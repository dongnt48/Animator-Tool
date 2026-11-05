import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services.captions import client
from services.social.store import Store


class CaptionBatchTests(unittest.TestCase):
    def setUp(self):
        network=patch('urllib.request.urlopen',side_effect=AssertionError('Tests must use mocked providers'))
        network.start(); self.addCleanup(network.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        db = patch.object(database, 'DB_FILE', str(Path(temporary.name)/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        settings=patch.dict(studio.app.config,SOCIAL_STORE=Store(Path(temporary.name)/'social.db'))
        settings.start(); self.addCleanup(settings.stop)
        self.items = [{'id':str(i),'title':'Original '+str(i),'stt':i} for i in range(205)]
        database._save_data(self.items)
        self.http = studio.app.test_client()

    def test_hundred_items_use_one_completion_and_map_by_id(self):
        calls = []
        def opener(request, timeout):
            payload = json.loads(request.data)
            self.assertIn('Không thêm hashtag',payload['messages'][0]['content'])
            sent = json.loads(payload['messages'][-1]['content'])['videos']
            calls.append(sent)
            results = [{'video_id':item['video_id'],'caption':'New '+item['video_id']} for item in reversed(sent)]
            return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps({'results':results})}}]}).encode())
        items = [{'video_id':str(i),'original':'Old','transcript':'Dialogue'} for i in range(100)]
        results = client.rewrite_captions(items, api_key='test', opener=opener)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]),100)
        self.assertEqual(results['0']['caption'],'New 0')

    def test_batch_route_persists_preview_without_replacing_caption(self):
        def provider(items, instruction, **kwargs):
            self.assertEqual(len(items),100)
            return {item['video_id']:{'caption':'New '+item['video_id']} for item in items}
        with patch('services.captions.routes.rewrite_captions', side_effect=provider) as ai:
            response = self.http.post('/api/captions/rewrite',json={'video_ids':[str(i) for i in range(100)]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ai.call_count,1)
        stored = database.get_video('0')
        self.assertEqual(stored['caption'],'New 0')
        self.assertNotIn('caption_ai',stored)
        videos = self.http.get('/api/captions/videos').json['videos']
        self.assertTrue(videos[0]['caption_rewritten'])
        self.assertNotIn('caption_draft',videos[0])

    def test_batch_limit_is_hundred_and_save_accepts_hundred(self):
        response = self.http.post('/api/captions/rewrite',json={'video_ids':[str(i) for i in range(101)]})
        self.assertEqual(response.status_code,400)
        response = self.http.post('/api/captions/save',json={'items':[
            {'video_id':str(i),'caption':'New','expected_caption':'Original '+str(i)} for i in range(100)]})
        self.assertEqual(response.status_code,200)
        self.assertTrue(all(item['status']=='saved' for item in response.json['results']))

    def test_missing_duplicate_and_unknown_ids_do_not_cross_assign(self):
        def opener(*args,**kwargs):
            data = {'results':[{'video_id':'a','caption':'First'},{'video_id':'a','caption':'Duplicate'},
                               {'video_id':'unknown','caption':'Wrong'}]}
            return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(data)}}]}).encode())
        result = client.rewrite_captions([{'video_id':i,'original':'Old','transcript':''} for i in ['a','b']],api_key='test',opener=opener)
        self.assertIn('error',result['a'])
        self.assertIn('error',result['b'])

    def test_saved_caption_has_persistent_rewrite_mark(self):
        self.http.post('/api/captions/save',json={'items':[{'video_id':'0','caption':'New','expected_caption':'Original 0'}]})
        video = self.http.get('/api/captions/videos').json['videos'][0]
        self.assertTrue(video['caption_rewritten'])
        self.assertEqual(video['caption_rewrite_state'],'saved')

    def test_provider_error_is_reported_for_whole_batch_without_saving(self):
        with patch('services.captions.routes.rewrite_captions',side_effect=client.CaptionError('Provider failed')):
            response = self.http.post('/api/captions/rewrite',json={'video_ids':['0','1']})
        self.assertEqual(response.status_code,200)
        self.assertTrue(all('error' in item for item in response.json['results']))
        self.assertNotIn('caption_ai',database.get_video('0'))

    def test_dialogue_is_shortened_to_300_and_full_cache_is_preserved(self):
        def provider(items, instruction, **kwargs):
            self.assertEqual(items[0]['transcript'],'x'*300)
            return {'0':{'caption':'New'}}
        with patch('services.captions.routes.dialogue_for_video',return_value='x'*500), patch('services.captions.routes.rewrite_captions',side_effect=provider):
            response=self.http.post('/api/captions/rewrite',json={'video_ids':['0'],'include_transcript':True})
        result=response.json['results'][0]
        self.assertEqual(result['transcript_chars'],300)
        self.assertEqual(result['transcript_total_chars'],500)
        self.assertTrue(result['transcript_shortened'])

    def test_stale_preview_cannot_overwrite_saved_caption(self):
        def provider(items, instruction, **kwargs):
            database.update_video_caption('0','Changed','Original 0')
            return {'0':{'caption':'Late AI'}}
        with patch('services.captions.routes.rewrite_captions',side_effect=provider):
            response=self.http.post('/api/captions/rewrite',json={'video_ids':['0']})
        self.assertIn('error',response.json['results'][0])
        self.assertNotIn('caption_ai',database.get_video('0'))

    def test_unwritten_mode_skips_draft_saved_and_legacy_before_ai_or_dialogue(self):
        data=database.get_all_videos()
        data[0]['caption_ai']={'original':'Original 0','caption':'Draft'}
        data[1]['caption_ai_saved_at']='2026-11-04'
        data[2]['caption']='Legacy saved'
        database._save_data(data)
        def provider(items,instruction,**kwargs):
            self.assertEqual([item['video_id'] for item in items],['3'])
            return {'3':{'caption':'Fresh'}}
        with patch('services.captions.routes.rewrite_captions',side_effect=provider) as ai, patch('services.captions.routes.dialogue_for_video',return_value='Speech') as speech:
            response=self.http.post('/api/captions/rewrite',json={'video_ids':['0','1','2','3'],'rewrite_mode':'unwritten','include_transcript':True})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ai.call_count,1)
        speech.assert_called_once_with('3')
        self.assertEqual([item['video_id'] for item in response.json['results'] if item.get('skipped')],['0','1','2'])
        self.assertEqual(database.get_video('0')['caption_ai']['caption'],'Draft')

    def test_all_mode_can_rewrite_existing_caption_and_invalid_mode_is_rejected(self):
        database.update_video_caption('0','Saved','Original 0')
        with patch('services.captions.routes.rewrite_captions',return_value={'0':{'caption':'Again'}}) as ai:
            response=self.http.post('/api/captions/rewrite',json={'video_ids':['0'],'rewrite_mode':'all'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ai.call_count,1)
        self.assertEqual(database.get_video('0')['caption'],'Again')
        with patch('services.captions.routes.rewrite_captions',return_value={'0':{'caption':'Unexpected'}}):
            self.assertEqual(self.http.post('/api/captions/rewrite',json={'video_ids':['0'],'rewrite_mode':'invalid'}).status_code,400)

    def test_all_already_written_makes_no_provider_call(self):
        database.update_video_caption('0','Saved','Original 0')
        with patch('services.captions.routes.rewrite_captions',side_effect=AssertionError('Must skip')), patch('services.captions.routes.dialogue_for_video',side_effect=AssertionError('Must skip')):
            response=self.http.post('/api/captions/rewrite',json={'video_ids':['0'],'rewrite_mode':'unwritten','include_transcript':True})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['results'][0]['skipped'])
