import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services.captions.client import rewrite_caption, CaptionError
from services.captions.transcripts import dialogue_for_video
from services import transcriber
from services.social.store import Store


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.downloads=self.root/'downloads'; self.downloads.mkdir()
        self.outputs=self.root/'outputs'; self.outputs.mkdir()
        self.media=self.downloads/'one.mp4'; self.media.write_bytes(b'video fixture')
        db=patch.object(database,'DB_FILE',str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        settings=patch.dict(studio.app.config,SOCIAL_STORE=Store(self.root/'social.db'))
        settings.start(); self.addCleanup(settings.stop)
        self.video=database.add_video('Caption old','url','one.mp4')
        self.client=studio.app.test_client()
        dirs=patch.multiple('services.captions.transcripts',DOWNLOADS_DIR=self.downloads,OUTPUTS_DIR=self.outputs)
        dirs.start(); self.addCleanup(dirs.stop)

    def test_real_dialogue_is_cached_and_reused_without_second_recognition(self):
        with patch('services.captions.transcripts.transcribe_audio_text',return_value=('Nội dung lời nói.',12)) as recognize:
            text=dialogue_for_video(self.video['id'])
        self.assertEqual(text,'Nội dung lời nói.')
        self.assertEqual(database.get_video(self.video['id'])['transcript'],text)
        with patch('services.captions.transcripts.transcribe_audio_text',side_effect=AssertionError('must use cache')):
            self.assertEqual(dialogue_for_video(self.video['id']),text)

    def test_changed_source_invalidates_old_dialogue(self):
        with patch('services.captions.transcripts.transcribe_audio_text',return_value=('Old speech',1)):
            dialogue_for_video(self.video['id'])
        self.media.write_bytes(b'different source video')
        with patch('services.captions.transcripts.transcribe_audio_text',return_value=('New speech',1)):
            self.assertEqual(dialogue_for_video(self.video['id']),'New speech')

    def test_missing_media_and_unsafe_path_do_not_reach_recognizer(self):
        self.media.unlink()
        with patch('services.captions.transcripts.transcribe_audio_text',side_effect=AssertionError('must not transcribe')):
            with self.assertRaises(CaptionError):
                dialogue_for_video(self.video['id'])
        with database.LOCK:
            data=database._load_data(); data[0]['video_filename']='../secret.mp4'; database._save_data(data)
        (self.root/'secret.mp4').write_bytes(b'secret')
        with self.assertRaises(CaptionError):
            dialogue_for_video(self.video['id'])

    def test_cached_dialogue_remains_usable_after_source_deletion(self):
        with patch('services.captions.transcripts.transcribe_audio_text',return_value=('Cached speech',1)):
            dialogue_for_video(self.video['id'])
        self.media.unlink()
        self.assertEqual(dialogue_for_video(self.video['id']),'Cached speech')

    def test_media_disappearing_before_stat_is_a_per_video_error(self):
        with patch('services.captions.transcripts.fingerprint',side_effect=FileNotFoundError()):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']],'include_transcript':True})
        self.assertEqual(response.status_code,200)
        self.assertIn('error',response.json['results'][0])

    def test_provider_receives_dialogue_separately_from_original_caption(self):
        def opener(request,timeout):
            data=json.loads(request.data)
            content=json.loads(data['messages'][-1]['content'])
            self.assertEqual(content['lời_thoại_video'],'Đây là lời thoại thực tế.')
            self.assertEqual(content['caption_gốc'],'Old caption')
            return io.BytesIO(b'{"choices":[{"message":{"content":"New caption"}}]}')
        self.assertEqual(rewrite_caption('Old caption','',transcript='Đây là lời thoại thực tế.',api_key='test',opener=opener),'New caption')

    def test_dialogue_sent_to_provider_is_limited_to_300_characters(self):
        def opener(request,timeout):
            content=json.loads(json.loads(request.data)['messages'][-1]['content'])
            self.assertEqual(len(content['lời_thoại_video']),300)
            return io.BytesIO(b'{"choices":[{"message":{"content":"New"}}]}')
        rewrite_caption('Old','',transcript='x'*12001,api_key='test',opener=opener)

    def test_rewrite_with_dialogue_reports_text_used_but_does_not_save_caption(self):
        with patch('services.captions.routes.dialogue_for_video',return_value='Lời thoại thật.'), patch('services.captions.routes.rewrite_captions',side_effect=lambda items,instruction,**kwargs:{item['video_id']:{'caption':'AI caption'} for item in items}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']],'include_transcript':True})
        self.assertEqual(response.status_code,200)
        result=response.json['results'][0]
        self.assertEqual(result['transcript'],'Lời thoại thật.')
        self.assertEqual(result['transcript_chars'],15)
        self.assertTrue(result['transcript_used'])
        self.assertEqual(database.get_video(self.video['id'])['caption'],'AI caption')

    def test_recognition_failure_does_not_call_caption_ai(self):
        with patch('services.captions.routes.dialogue_for_video',side_effect=CaptionError('Không nhận diện được lời thoại.')), patch('services.captions.routes.rewrite_captions',side_effect=AssertionError('No AI without dialogue')):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']],'include_transcript':True})
        self.assertIn('error',response.json['results'][0])

    def test_invalid_dialogue_toggle_is_rejected(self):
        response=self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']],'include_transcript':'true'})
        self.assertEqual(response.status_code,400)

    def test_strict_recognition_never_invents_fallback_and_cleans_wav(self):
        def convert(command,**kwargs):
            with wave.open(str(command[-1]),'wb') as output:
                output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
                output.writeframes(b'\0\0'*160)
        temp=self.root/'recognition'; temp.mkdir()
        with patch.object(transcriber.subprocess,'run',side_effect=convert), patch.object(transcriber.sr.Recognizer,'recognize_google',side_effect=RuntimeError('network failed')):
            with self.assertRaises(transcriber.TranscriptionError):
                transcriber.transcribe_audio_text(str(self.media),str(temp),strict=True)
        self.assertFalse((temp/'temp_voice.wav').exists())


if __name__=='__main__':
    unittest.main()
