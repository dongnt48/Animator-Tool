import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services.social.store import Store


class VideoDetailTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        db=patch.object(database,'DB_FILE',str(root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        self.store=Store(root/'social.sqlite3')
        config=patch.dict(studio.app.config,SOCIAL_STORE=self.store)
        config.start(); self.addCleanup(config.stop)
        database._save_data([{'id':'one','stt':1,'title':'Original <caption>','status':'completed','transcript':'Full dialogue',
                             'video_filename':'../secret.mp4','output_filename':'ready.mp4'}])
        database.apply_caption_results([{'video_id':'one','original':'Original <caption>','caption':'AI caption #tag','transcript':'Full dialogue','transcript_chars':13,'transcript_used':True}])
        self.client=studio.app.test_client()

    def test_detail_has_draft_dialogue_and_publication_without_external_calls(self):
        with patch('services.captions.routes.dialogue_for_video',side_effect=AssertionError('GET must not transcribe')), patch('services.captions.routes.rewrite_captions',side_effect=AssertionError('GET must not call AI')):
            response=self.client.get('/api/social/videos/one')
        self.assertEqual(response.status_code,200)
        data=response.json
        self.assertEqual(data['video']['caption'],'AI caption #tag')
        self.assertEqual(data['video']['transcript'],'Full dialogue')
        self.assertIn('publication',data)
        self.assertIsNone(data['media']['original'])
        self.assertEqual(self.client.get('/videos/one').status_code,200)

    def test_deleted_record_returns_404(self):
        self.assertEqual(self.client.get('/api/social/videos/missing').status_code,404)
        self.assertEqual(self.client.get('/videos/missing').status_code,404)

    def test_library_has_no_inline_result_editor(self):
        page=self.client.get('/').get_data(as_text=True)
        self.assertNotIn('id="captionResults"',page)
        self.assertNotIn('id="captionDrafts"',page)
        self.assertIn('id="captionTools"',page)
        self.assertNotIn('id="inputUrl"',page)
        creation=self.client.get('/create')
        self.assertEqual(creation.status_code,200)
        html=creation.get_data(as_text=True)
        self.assertIn('id="inputUrl"',html)
        self.assertNotIn('id="captionTools"',html)
        self.assertNotIn('id="videoTableBody"',html)
