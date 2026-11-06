import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from services.animation import planner, settings, timing


WORDS = [
    {'text': 'Hãy', 'start': 1.2, 'end': 1.5},
    {'text': 'bước', 'start': 1.6, 'end': 1.9},
    {'text': 'tiếp.', 'start': 2.0, 'end': 2.4},
    {'text': 'Bình', 'start': 4.0, 'end': 4.2},
    {'text': 'yên.', 'start': 4.3, 'end': 4.7},
]


def storyboard():
    return {'scenes': [
        {'segment_id': 0, 'mood': 'proud', 'action': 'walk', 'visual': 'journey', 'cue_word': 1,
         'badge': 'Bước tiếp', 'key_phrase': 'BƯỚC TIẾP', 'note': 'Tiếp tục hành trình', 'icon': '🌿'},
        {'segment_id': 1, 'mood': 'peace', 'action': 'breathe', 'visual': 'peace', 'cue_word': 0,
         'badge': 'Bình yên', 'key_phrase': 'BÌNH YÊN', 'note': 'Tìm lại bình yên', 'icon': '✨'},
    ]}


class AnimationTests(unittest.TestCase):
    def test_grouping_preserves_real_word_times_and_pauses(self):
        segments = timing.group_words(WORDS, 6)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]['start'], 1.2)
        self.assertEqual(segments[0]['end'], 2.4)
        self.assertEqual(segments[1]['start'], 4.0)
        self.assertEqual(segments[0]['words'], WORDS[:3])
        for bad in ([], ['invalid'], [{'text': 5, 'start': 0, 'end': 1}], [{'text': 'x', 'start': float('nan'), 'end': 2}],
                    [{'text': 'x', 'start': 2, 'end': 1}]):
            with self.assertRaises(ValueError):
                timing.group_words(bad, 6)

    def test_ai_cannot_change_timing_and_cue_is_a_real_word(self):
        segments = timing.group_words(WORDS, 6)
        plan = planner.validate_storyboard(storyboard(), segments)
        result = planner.build_scenes(plan, segments, 6)
        first = result['scenes'][0]
        self.assertEqual(first['leadWords'][0], {'text': 'Hãy', 'start': 36, 'end': 45})
        self.assertEqual(first['actionStart'], 48)
        self.assertEqual(first['visual'], 'journey')
        self.assertEqual(result['durationInFrames'], 180)
        self.assertTrue(result['scenes'][-1]['endFrame'] <= 180)
        self.assertEqual(first['startFrame'], 36)

    def test_incomplete_duplicate_unknown_action_and_invalid_cues_rejected(self):
        segments = timing.group_words(WORDS, 6)
        invalid = [[], [storyboard()['scenes'][0]] * 2]
        for field, value in [('mood', 'invented'), ('action', 'shell'), ('visual', 'arbitrary_svg'), ('icon', 'wave'), ('cue_word', 99), ('cue_word', True)]:
            item = storyboard()
            item['scenes'][0][field] = value
            invalid.append(item['scenes'])
        for scenes in invalid:
            with self.assertRaises(ValueError):
                planner.validate_storyboard({'scenes': scenes}, segments)

    def test_cli_one_call_structured_output_no_shell_and_full_dialogue(self):
        segments = timing.group_words(WORDS, 6)
        done = SimpleNamespace(returncode=0, stdout=json.dumps({'status': 'SUCCESS', 'structured_output': storyboard()}))
        with patch.object(planner, 'find_cli', return_value='C:/agy.exe'), patch.object(planner.subprocess, 'run', return_value=done) as run:
            result = planner.request_storyboard(segments, {'model': 'test-model'})
        self.assertEqual(result, storyboard())
        self.assertEqual(run.call_count, 1)
        args, kwargs = run.call_args
        self.assertFalse(kwargs.get('shell', False))
        self.assertNotIn('--dangerously-skip-permissions', args[0])
        self.assertIn('test-model', args[0])
        self.assertIn('Bình', kwargs['input'])
        self.assertIn('--input-format', args[0])

    def test_cli_failure_is_sanitized_and_never_retried(self):
        segments = timing.group_words(WORDS, 6)
        for response in [SimpleNamespace(returncode=1, stdout='SECRET raw diagnostics'),
                         SimpleNamespace(returncode=0, stdout='not json'),
                         SimpleNamespace(returncode=0, stdout=json.dumps({'status': 'ERROR', 'error': 'SECRET'}))]:
            with patch.object(planner, 'find_cli', return_value='agy.exe'), patch.object(planner.subprocess, 'run', return_value=response) as run:
                with self.assertRaisesRegex(RuntimeError, 'Antigravity') as caught:
                    planner.request_storyboard(segments, {})
                self.assertNotIn('SECRET', str(caught.exception))
                self.assertEqual(run.call_count, 1)

    def test_cli_stream_result_and_timeout(self):
        segments = timing.group_words(WORDS, 6)
        output = '\n'.join(['[]', json.dumps({'event': 'init'}), json.dumps({'event': 'result', 'result': {
            'status': 'SUCCESS', 'response': json.dumps(storyboard())}})])
        with patch.object(planner, 'find_cli', return_value='agy.exe'), patch.object(planner.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=output)):
            self.assertEqual(planner.request_storyboard(segments, {}), storyboard())
        with patch.object(planner, 'find_cli', return_value='agy.exe'), patch.object(planner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('agy', 600)) as run:
            with self.assertRaisesRegex(RuntimeError, '10 phút'):
                planner.request_storyboard(segments, {})
            self.assertEqual(run.call_count, 1)

    def test_grouping_never_hides_words_beyond_subtitle_limit(self):
        words = [{'text': str(i), 'start': i*.2, 'end': i*.2+.1} for i in range(30)]
        segments = timing.group_words(words, 7)
        self.assertTrue(all(len(s['words']) <= 9 for s in segments))
        self.assertEqual(sum(len(s['words']) for s in segments), 30)

    def test_cache_reuses_ai_and_invalidates_on_media_or_model_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.mp4'; path.write_bytes(b'one')
            with patch.object(planner, 'CACHE_DIR', Path(tmp)/'cache'), \
                 patch.object(planner, 'recognize', return_value=(WORDS, 6)) as recognize, \
                 patch.object(planner, 'request_storyboard', return_value=storyboard()) as ai:
                one = planner.prepare_animation(path, {'model': 'a', 'speech_model': 'small'})
                two = planner.prepare_animation(path, {'model': 'a', 'speech_model': 'small'})
                self.assertEqual(one, two)
                self.assertEqual(ai.call_count, 1)
                self.assertEqual(recognize.call_count, 1)
                planner.prepare_animation(path, {'model': 'b', 'speech_model': 'small'})
                self.assertEqual(ai.call_count, 2)
                self.assertEqual(recognize.call_count, 1)
                path.write_bytes(b'different source')
                planner.prepare_animation(path, {'model': 'b', 'speech_model': 'small'})
                self.assertEqual(recognize.call_count, 2)

    def test_new_visual_planner_invalidates_old_story_without_repeating_recognition(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'source.mp4'; path.write_bytes(b'source')
            with patch.object(planner, 'CACHE_DIR', Path(tmp)/'cache'), \
                 patch.object(planner, 'recognize', return_value=(WORDS, 6)) as speech, \
                 patch.object(planner, 'request_storyboard', return_value=storyboard()) as ai:
                planner.prepare_animation(path, {'model': 'test', 'speech_model': 'small'})
                with patch.object(planner, 'STORY_VERSION', planner.STORY_VERSION + 1):
                    planner.prepare_animation(path, {'model': 'test', 'speech_model': 'small'})
                self.assertEqual(ai.call_count, 2)
                self.assertEqual(speech.call_count, 1)

    def test_settings_reject_unknown_modes_flags_and_models(self):
        for body in ({'mode': 'other'}, {'model': '--shell'}, {'model': 'a\nb'}, {'speech_model': 'huge'}, {'mode': True}):
            with self.assertRaises(ValueError):
                settings.validate_update(body)
        self.assertEqual(settings.validate_update({'mode': 'antigravity', 'model': '', 'speech_model': 'small'})['mode'], 'antigravity')


class AnimationRouteTests(unittest.TestCase):
    def test_ai_accepts_known_legacy_styles_and_rejects_unknown_before_queue(self):
        video = {'id': 'one', 'status': 'completed', 'style': 'semantic_dark', 'character': 'stickman', 'aspect_ratio': '9:16'}
        with patch('services.animation.routes.database.get_video', return_value=video), \
             patch('services.animation.routes.database.update_video_status') as update, \
             patch.object(self.studio.threading, 'Thread') as thread:
            self.assertEqual(self.client.post('/api/animation/render/one', json={}).status_code, 200)
            self.assertEqual(thread.call_args.kwargs['args'][2], 'midnight')
            video['style'] = 'ai_storyboard'
            self.assertEqual(self.client.post('/api/animation/render/one', json={}).status_code, 200)
            self.assertEqual(thread.call_args.kwargs['args'][2], 'cozy')
            thread.reset_mock(); update.reset_mock()
            video['style'] = 'unknown'
            self.assertEqual(self.client.post('/api/animation/render/one', json={}).status_code, 400)
            thread.assert_not_called(); update.assert_not_called()

    def setUp(self):
        import app as studio
        from services.social.store import Store
        self.studio = studio
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name)/'settings.sqlite3')
        config = patch.dict(studio.app.config, SOCIAL_STORE=self.store)
        config.start(); self.addCleanup(config.stop)
        check = patch('services.animation.routes.readiness', return_value={'cli_installed': True, 'speech_installed': True})
        check.start(); self.addCleanup(check.stop)
        self.client = studio.app.test_client()

    def test_settings_round_trip_bad_body_and_no_ai_calls(self):
        with patch.object(planner, 'request_storyboard', side_effect=AssertionError('No generation on settings')):
            self.assertEqual(self.client.get('/api/animation/settings').json['settings']['mode'], 'antigravity')
            response = self.client.post('/api/animation/settings', json={'mode': 'legacy', 'model': 'custom-model'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get('/api/animation/settings').json['settings']['model'], 'custom-model')
            for body in ([], None, {'api_key': 'do-not-store'}, {'mode': 'invalid'}):
                self.assertEqual(self.client.post('/api/animation/settings', json=body).status_code, 400)
            self.assertEqual(self.client.get('/api/animation/settings').json['settings']['mode'], 'legacy')

    def test_render_snapshots_saved_settings_and_missing_dependencies_do_not_queue(self):
        video = {'id': 'one', 'stt': 1, 'status': 'completed'}
        with patch.object(self.studio, 'get_video', return_value=video), \
             patch('services.animation.routes.database.get_video', return_value=video), \
             patch('services.animation.routes.database.update_video_status'), \
             patch.object(self.studio, 'update_video_status') as update, \
             patch.object(self.studio.threading, 'Thread') as thread:
            settings.save_settings(self.store, {'mode': 'antigravity'})
            response = self.client.post('/api/render/one', json={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(thread.call_args.kwargs['args'][-1]['mode'], 'legacy')
            thread.reset_mock(); update.reset_mock()
            settings.save_settings(self.store, {'mode': 'antigravity'})
            with patch('services.animation.routes.readiness', return_value={'cli_installed': False, 'speech_installed': True}):
                response = self.client.post('/api/animation/render/one', json={})
            self.assertEqual(response.status_code, 400)
            thread.assert_not_called(); update.assert_not_called()

    def test_ai_tab_is_separate_and_only_explicit_ai_endpoint_uses_quota(self):
        self.assertEqual(self.client.get('/animation').status_code, 200)
        for path in ('/', '/create'):
            text = self.client.get(path).get_data(as_text=True)
            self.assertNotIn('id="animationSettingsForm"', text)
        video = {'id': 'one', 'stt': 1, 'status': 'completed', 'video_filename': 'source.mp4'}
        with patch.object(self.studio, 'get_video', return_value=video), \
             patch('services.animation.routes.database.get_video', return_value=video), \
             patch('services.animation.routes.database.update_video_status'), \
             patch.object(self.studio, 'update_video_status'), \
             patch.object(self.studio.threading, 'Thread') as thread:
            response = self.client.post('/api/animation/render/one', json={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(thread.call_args.kwargs['kwargs']['animation_settings']['mode'], 'antigravity')

    def test_old_download_and_batch_render_ignore_ai_settings(self):
        settings.save_settings(self.store, {'mode': 'antigravity'})
        with patch.object(self.studio, 'get_all_videos', return_value=[{'id': 'one', 'status': 'new'}]), \
             patch.object(self.studio, 'update_video_status'), \
             patch.object(self.studio.threading, 'Thread') as thread, \
             patch('services.animation.routes.readiness', side_effect=AssertionError('Old flow must not probe AI')):
            for path, body in [('/api/render-all', {}), ('/api/download-and-render', {'url': 'https://www.tiktok.com/@test/video/1'})]:
                self.assertEqual(self.client.post(path, json=body).status_code, 200)
                self.assertEqual(thread.call_args.kwargs['args'][-1]['mode'], 'legacy')


class AnimationPipelineTests(unittest.TestCase):
    def test_duplicate_render_does_not_start_another_pipeline(self):
        from services import renderer
        import threading
        running = threading.Event()
        release = threading.Event()
        def pipeline(*args, **kwargs):
            running.set(); release.wait(5)
            return True
        with patch.object(renderer, '_render_video_pipeline', side_effect=pipeline) as mock:
            first = threading.Thread(target=renderer.render_video_pipeline, args=('concurrency-test',))
            first.start()
            try:
                self.assertTrue(running.wait(2))
                self.assertFalse(renderer.render_video_pipeline('concurrency-test'))
                self.assertEqual(mock.call_count, 1)
            finally:
                release.set(); first.join(5)

    def test_ai_failure_preserves_existing_output_and_does_not_run_remotion(self):
        from services import renderer
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source.mp4'; source.write_bytes(b'source')
            output = root/'completed.mp4'; output.write_bytes(b'old output')
            video = {'id': 'one', 'video_filename': source.name, 'output_filename': output.name}
            with patch.object(renderer.database, 'get_video', return_value=video), \
                 patch.object(renderer.database, 'update_video_status') as status, \
                 patch.object(renderer, 'DOWNLOADS_DIR', tmp), \
                 patch.object(renderer, 'OUTPUTS_DIR', tmp), \
                 patch.object(renderer.transcriber, 'extract_audio'), \
                 patch.object(planner, 'find_cli', return_value='agy.exe'), \
                 patch('services.animation.settings.find_cli', return_value='agy.exe'), \
                 patch.object(planner, 'prepare_animation', side_effect=RuntimeError('No quota')), \
                 patch.object(renderer.subprocess, 'run') as render:
                self.assertFalse(renderer.render_video_pipeline('one', animation_settings={'mode': 'antigravity'}))
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b'old output')
            self.assertEqual(status.call_args.args[1], 'error')

    def test_legacy_mode_does_not_call_antigravity(self):
        from services import renderer
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'source.mp4').write_bytes(b'source')
            video = {'id': 'one', 'video_filename': 'source.mp4'}
            def render(command, **kwargs):
                Path(command[5]).write_bytes(b'new output')
                return SimpleNamespace(returncode=0)
            with patch.object(renderer.database, 'get_video', return_value=video), \
                 patch.object(renderer.database, 'update_video_status', side_effect=lambda *args, **kwargs: events.append(args[1])), \
                 patch('services.covers.images.ensure_cover', side_effect=lambda *args: events.append('cover') or {'mode':'frame'}), \
                 patch.object(renderer, 'DOWNLOADS_DIR', tmp), \
                 patch.object(renderer, 'OUTPUTS_DIR', tmp), \
                 patch.object(renderer, 'REMOTION_DIR', tmp), \
                 patch.object(renderer, 'LEGACY_REMOTION_DIR', tmp), \
                 patch.object(renderer.transcriber, 'extract_audio'), \
                 patch.object(renderer.transcriber, 'transcribe_audio_segments', return_value=([{'start': 0, 'end': 1, 'text': 'hello'}], 1)), \
                 patch.object(planner, 'prepare_animation', side_effect=AssertionError('No AI')), \
                 patch.object(renderer.subprocess, 'run', side_effect=render):
                self.assertTrue(renderer.render_video_pipeline('one', animation_settings={'mode': 'legacy'}))
            self.assertTrue(any(p.name.startswith('cozy_') for p in root.glob('*.mp4')))
            self.assertLess(events.index('cover'), events.index('completed'))

    def test_ai_style_alias_does_not_overwrite_original_library_settings(self):
        from services import renderer
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'source.mp4').write_bytes(b'source')
            video = {'id': 'one', 'video_filename': 'source.mp4', 'style': 'semantic_dark'}
            def render(command, **kwargs):
                Path(command[5]).write_bytes(b'new output')
                return SimpleNamespace(returncode=0)
            with patch.object(renderer.database, 'get_video', return_value=video), \
                 patch.object(renderer.database, 'update_video_status') as status, \
                 patch.object(renderer, 'DOWNLOADS_DIR', tmp), \
                 patch.object(renderer, 'OUTPUTS_DIR', tmp), \
                 patch.object(renderer, 'REMOTION_DIR', tmp), \
                 patch.object(renderer.transcriber, 'extract_audio'), \
                 patch('services.captions.transcripts.save_recognized_transcript'), \
                 patch('services.animation.settings.find_cli', return_value='agy.exe'), \
                 patch.object(planner, 'prepare_animation', return_value={'scenes': [], 'durationInFrames': 30, 'transcript': 'Hello', 'timedDialogue': True}), \
                 patch.object(renderer.subprocess, 'run', side_effect=render):
                self.assertTrue(renderer.render_video_pipeline('one', style='midnight', animation_settings={'mode': 'antigravity'}))
            for call in status.call_args_list:
                self.assertNotIn('style', call.kwargs)
                self.assertNotIn('aspect_ratio', call.kwargs)
                self.assertNotIn('character', call.kwargs)
            self.assertTrue(status.call_args.kwargs['output_filename'].startswith('antigravity_midnight_'))


if __name__ == '__main__':
    unittest.main()
