import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database
import app as studio
from services.captions.client import rewrite_caption, CaptionError
from services.social.store import Store


class CaptionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = patch.object(database, 'DB_FILE', str(self.root / 'videos.json'))
        self.db.start()
        self.addCleanup(self.db.stop)
        self.video = database.add_video('Original #tag', 'url', 'one.mp4')
        self.client = studio.app.test_client()
        self.store = Store(self.root / 'social.db')
        self.config = patch.dict(studio.app.config, SOCIAL_STORE=self.store)
        self.config.start()
        self.addCleanup(self.config.stop)

    def test_rewrite_uses_requested_model_and_returns_only_caption(self):
        def opener(request, timeout):
            body = json.loads(request.data)
            self.assertEqual(body['model'], 'gemini-3.8-flash')
            self.assertIn('Original #tag', body['messages'][-1]['content'])
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
            return io.BytesIO(json.dumps({'choices':[{'message':{'content':'New caption #tag'}}]}).encode())
        self.assertEqual(rewrite_caption('Original #tag','Keep meaning',api_key='test-key',opener=opener),'New caption')

    def test_empty_ai_response_is_an_error(self):
        with self.assertRaises(CaptionError):
            rewrite_caption('original','',api_key='test-key',opener=lambda *args,**kwargs:io.BytesIO(b'{"choices":[]}'))

    def test_malformed_choice_is_a_sanitized_error(self):
        with self.assertRaises(CaptionError):
            rewrite_caption('original','',api_key='test-key',opener=lambda *args,**kwargs:io.BytesIO(b'{"choices":[null]}'))

    def test_truncated_response_is_not_presented_as_complete_caption(self):
        response={'choices':[{'finish_reason':'length','message':{'content':'unfinished'}}]}
        with self.assertRaises(CaptionError):
            rewrite_caption('original','',api_key='test-key',opener=lambda *args,**kwargs:io.BytesIO(json.dumps(response).encode()))

    def test_rewrite_saves_immediately_and_preserves_original_title(self):
        with patch('services.captions.routes.rewrite_captions',side_effect=lambda items,instruction,**kwargs:{item['video_id']:{'caption':'AI result'} for item in items}):
            response = self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']],'instruction':'Shorter'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['results'][0]['caption'],'AI result')
        self.assertEqual(database.get_video(self.video['id'])['caption'],'AI result')
        self.assertEqual(database.get_video(self.video['id'])['title'],'Original #tag')

    def test_save_caption_preserves_original_title_and_rejects_stale_edits(self):
        item = {'video_id':self.video['id'],'caption':'Approved caption','expected_caption':'Original #tag'}
        response = self.client.post('/api/captions/save',json={'items':[item]})
        self.assertEqual(response.status_code,200)
        video = database.get_video(self.video['id'])
        self.assertEqual(video['caption'],'Approved caption')
        self.assertEqual(video['title'],'Original #tag')
        stale = self.client.post('/api/captions/save',json={'items':[{**item,'caption':'Overwrite'}]})
        self.assertEqual(stale.json['results'][0]['status'],'conflict')
        self.assertEqual(database.get_video(self.video['id'])['caption'],'Approved caption')

    def test_direct_rewrite_changes_library_but_preserves_existing_schedule_snapshot(self):
        media=self.root/'ready.mp4'; media.write_bytes(b'fixture')
        batch=self.store.create_batch(self.video['id'],str(media),'Scheduled old caption',1000,False,'caption-snapshot')
        with patch('services.captions.routes.rewrite_captions',return_value={self.video['id']:{'caption':'New caption'}}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':[self.video['id']]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(database.get_video(self.video['id'])['caption'],'New caption')
        self.assertEqual(self.store.get_batch(batch['id'])['caption'],'Scheduled old caption')

    def test_malformed_input_and_cross_origin_are_rejected(self):
        for body in [{}, {'video_ids':'one'}, {'video_ids':[]}, {'video_ids':['one']*11}]:
            self.assertEqual(self.client.post('/api/captions/rewrite',json=body).status_code,400)
        self.assertEqual(self.client.post('/api/captions/rewrite',json={'video_ids':['one']},headers={'Origin':'https://evil.test'}).status_code,403)

    def test_publication_summary_preserves_success_and_shows_other_platform_failures(self):
        media = self.root / 'video.mp4'
        media.write_bytes(b'fixture')
        batch = self.store.create_batch(self.video['id'],str(media),'Original #tag',1000,False,'publication-test')
        owner=self.store.begin_login('facebook',now=1)
        self.store.complete_login('facebook',owner,'42',now=2)
        task=self.store.claim_next('worker',now=1000)
        self.store.mark_submitting(task['id'],'worker')
        self.store.finish(task['id'],'worker','published','OK','https://www.facebook.com/reel/12345')
        self.store.claim_next('worker',now=1001)
        summary=self.store.publication_summary([self.video['id']])[self.video['id']]
        self.assertEqual(summary['facebook']['state'],'published')
        self.assertEqual(summary['facebook']['url'],'https://www.facebook.com/reel/12345')
        self.assertEqual(summary['instagram']['state'],'needs_login')
        self.assertEqual(self.store.publication_summary(['never'])['never'],{})
        later=self.store.create_batch(self.video['id'],str(media),'later caption',2000,False,'later-attempt')
        with self.store.transaction() as db:
            db.execute("UPDATE tasks SET state='failed' WHERE batch_id=? AND platform='facebook'",(later['id'],))
        self.assertEqual(self.store.publication_summary([self.video['id']])[self.video['id']]['facebook']['state'],'published')


if __name__ == '__main__':
    unittest.main()
