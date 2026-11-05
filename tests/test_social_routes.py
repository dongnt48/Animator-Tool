import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import app as studio
from services.social.store import Store


class RoutesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.output = root / 'outputs'
        self.output.mkdir()
        (self.output / 'ready.mp4').write_bytes(b'rendered video')
        self.store = Store(root / 'social.sqlite3')
        self.video = {'id': 'one', 'status': 'completed', 'title': "Caption O'Brien #tag", 'output_filename': 'ready.mp4'}
        self.client = studio.app.test_client()
        self.settings = patch.dict(studio.app.config, SOCIAL_STORE=self.store, SOCIAL_OUTPUTS_DIR=str(self.output), TESTING=True)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.lookup = patch('database.get_video', return_value=self.video)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)

    def payload(self, **changes):
        payload = {'video_id': 'one', 'scheduled_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                   'made_for_kids': False, 'confirm_all_platforms': True, 'request_key': 'route-request-123'}
        payload.update(changes)
        return payload

    def test_creates_all_targets_and_uses_existing_caption(self):
        response = self.client.post('/api/social/batches', json=self.payload())
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        batch = response.json['batch']
        self.assertEqual(batch['caption'], "Caption O'Brien #tag")
        self.assertEqual(len(batch['tasks']), 5)
        self.assertNotIn('media_path', batch)

    def test_ignores_client_caption_and_uses_stored_caption(self):
        self.video['caption'] = 'Existing caption override'
        response = self.client.post('/api/social/batches', json=self.payload(caption='do not use'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['batch']['caption'], 'Existing caption override')

    def test_requires_timezone_and_explicit_youtube_audience(self):
        for changes in [{'scheduled_at': '2027-01-01T10:00'}, {'made_for_kids': 'false'},
                        {'made_for_kids': None}, {'confirm_all_platforms': False},
                        {'scheduled_at': 'garbage'}, {'scheduled_at': '2020-01-01T00:00:00Z'}]:
            with self.subTest(changes=changes):
                response = self.client.post('/api/social/batches', json=self.payload(**changes))
                self.assertEqual(response.status_code, 400)

    def test_path_traversal_in_video_record_is_rejected(self):
        self.video['output_filename'] = '../outside.mp4'
        response = self.client.post('/api/social/batches', json=self.payload())
        self.assertEqual(response.status_code, 400)

    def test_unrendered_video_is_not_schedulable(self):
        self.video['status'] = 'processing'
        self.assertEqual(self.client.post('/api/social/batches', json=self.payload()).status_code, 400)

    def test_cross_origin_requests_cannot_open_browser_or_create_schedule(self):
        response = self.client.post('/api/social/batches', json=self.payload(), headers={'Origin': 'https://evil.test'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post('/api/social/accounts/facebook/connect', json={}, headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status_code, 403)

    def test_localhost_host_header_is_required(self):
        response = self.client.get('/api/social/status', headers={'Host': 'evil.test'})
        self.assertEqual(response.status_code, 403)

    def test_bad_json_shape_does_not_raise_internal_error(self):
        for body in [[], None, 'string', 1]:
            response = self.client.post('/api/social/batches', json=body)
            self.assertIn(response.status_code, (400, 415))

    def test_page_and_status_are_available_without_starting_worker(self):
        self.assertEqual(self.client.get('/publishing').status_code, 200)
        with patch('database.get_all_videos', return_value=[self.video]):
            response = self.client.get('/api/social/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['videos'][0]['caption'], self.video['title'])
        self.assertFalse(response.json['worker_online'])

    def test_lost_schedule_response_can_be_recovered_after_due_time_and_source_deletion(self):
        body = self.payload()
        first = self.client.post('/api/social/batches', json=body)
        self.assertEqual(first.status_code, 201)
        (self.output / 'ready.mp4').unlink()
        self.video['status'] = 'processing'
        future = datetime.fromisoformat(body['scheduled_at']).timestamp() + 10
        with patch('services.social.routes.time.time', return_value=future):
            replay = self.client.post('/api/social/batches', json=body)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay.json['batch']['id'], first.json['batch']['id'])
        changed = self.client.post('/api/social/batches', json={**body, 'video_id':'different'})
        self.assertEqual(changed.status_code, 409)

    def test_renderer_rejects_shell_metacharacters_before_starting_tools(self):
        from services import renderer
        self.video['video_filename'] = 'ready.mp4'
        with patch.object(renderer.database, 'update_video_status'), patch.object(renderer.os.path, 'exists', return_value=True), patch.object(renderer.transcriber, 'extract_audio', side_effect=RuntimeError('must not reach tools')) as extract:
            result = renderer.render_video_pipeline('one', style='cozy&echo marker&')
        self.assertFalse(result)
        extract.assert_not_called()

    def test_daily_configuration_does_not_require_selecting_a_video(self):
        body = {'enabled':True,'times':['19:00','08:00'],'timezone':'Asia/Bangkok',
                'selection':'fifo','made_for_kids':False,'confirm_all_platforms':True}
        response = self.client.post('/api/social/daily', json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.get_daily()['times'], ['08:00','19:00'])
        self.assertEqual(self.store.list_batches(), [])

    def test_admin_pages_are_separate_and_legacy_video_link_redirects(self):
        for path, expected, absent in [('/publishing', 'metricReady', 'dailyForm'),
                                       ('/publishing/schedule', 'dailyForm', 'accounts"'),
                                       ('/publishing/accounts', 'accounts"', 'dailyForm'),
                                       ('/publishing/results', 'batches"', 'scheduleForm'),
                                       ('/publishing/new', 'scheduleForm', 'dailyForm')]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(expected, html)
                self.assertNotIn(f'id="{absent}', html)
        response = self.client.get('/publishing?video=one')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/publishing/new?video=one', response.location)

    def test_video_creation_page_uses_same_admin_shell(self):
        response = self.client.get('/create')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('admin-sidebar', html)
        self.assertIn('id="inputUrl"', html)
        self.assertIn('id="btnDownloadAndRender"', html)
        self.assertIn('/static/admin/js/library.js', html)

    def test_daily_enable_requires_confirmation_but_pause_does_not(self):
        body = {'enabled':True,'times':['08:00'],'timezone':'Asia/Bangkok','selection':'fifo','made_for_kids':False}
        self.assertEqual(self.client.post('/api/social/daily', json=body).status_code, 400)
        self.assertEqual(self.client.post('/api/social/daily', json={**body,'enabled':False}).status_code, 200)

    def test_daily_status_counts_only_unused_completed_content(self):
        self.store.create_batch('one', str(self.output / 'ready.mp4'), 'existing', 1, False, 'already-used')
        with patch('database.get_all_videos', return_value=[self.video]):
            response = self.client.get('/api/social/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['daily']['available_count'], 0)
        self.assertFalse(response.json['daily']['config']['enabled'])


if __name__ == '__main__':
    unittest.main()
