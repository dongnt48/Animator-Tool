import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services.social.store import Store
from services.captions.client import rewrite_captions


class CaptionProviderTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        settings=patch.dict(studio.app.config,SOCIAL_STORE=Store(self.root/'social.db'))
        settings.start(); self.addCleanup(settings.stop)
        db=patch.object(database,'DB_FILE',str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        fallback=patch('services.captions.provider.configured_key',return_value='fallback-key')
        fallback.start(); self.addCleanup(fallback.stop)
        network=patch('urllib.request.urlopen',side_effect=AssertionError('Mock provider required'))
        network.start(); self.addCleanup(network.stop)
        self.client=studio.app.test_client()
        database._save_data([{'id':'one','title':'Original'}])

    def test_saved_key_is_never_returned_and_blank_preserves_it(self):
        response=self.client.post('/api/captions/provider',json={'model':'custom-model','api_key':'fake-secret-123'})
        self.assertEqual(response.status_code,200)
        self.assertNotIn('fake-secret-123',response.get_data(as_text=True))
        self.assertTrue(response.json['configured'])
        response=self.client.post('/api/captions/provider',json={'model':'next-model','api_key':''})
        self.assertEqual(response.json['model'],'next-model')
        for path in ['/api/captions/provider','/api/captions/videos','/api/social/videos/one']:
            self.assertNotIn('fake-secret-123',self.client.get(path).get_data(as_text=True))
        self.assertEqual(Store(self.root/'social.db').get_caption_provider()['api_key'],'fake-secret-123')

    def test_invalid_save_does_not_replace_existing_provider(self):
        self.client.post('/api/captions/provider',json={'model':'good-model','api_key':'safe-key'})
        for body in [{'model':''},{'model':'bad model'},{'api_key':'bad\r\nkey'},{'api_key':None},{'api_key':'x'*513}]:
            self.assertEqual(self.client.post('/api/captions/provider',json=body).status_code,400)
        self.assertEqual(self.client.get('/api/captions/provider').json['model'],'good-model')

    def test_rewrite_passes_saved_provider_to_completion_client(self):
        self.client.post('/api/captions/provider',json={'model':'custom-model','api_key':'fake-key'})
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'New'}}) as ai:
            response=self.client.post('/api/captions/rewrite',json={'video_ids':['one']})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ai.call_args.kwargs,{'model':'custom-model','api_key':'fake-key'})

    def test_model_is_sent_in_request_and_key_only_in_header(self):
        def opener(request,timeout):
            payload=json.loads(request.data)
            self.assertEqual(payload['model'],'custom-model')
            self.assertNotIn('fake-key',request.data.decode())
            self.assertEqual(request.get_header('Authorization'),'Bearer fake-key')
            return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps({'results':[{'video_id':'one','caption':'New'}]})}}]}).encode())
        self.assertEqual(rewrite_captions([{'video_id':'one','original':'Old','transcript':''}],model='custom-model',api_key='fake-key',opener=opener)['one']['caption'],'New')

    def test_existing_environment_fallback_and_default_model_still_work(self):
        response=self.client.get('/api/captions/provider')
        self.assertEqual(response.json['model'],'gemini-3.8-flash')
        self.assertTrue(response.json['configured'])
        self.assertFalse(response.json['has_saved_key'])
        self.assertNotIn('fallback-key',response.get_data(as_text=True))
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'New'}}) as ai:
            self.client.post('/api/captions/rewrite',json={'video_ids':['one']})
        self.assertEqual(ai.call_args.kwargs['api_key'],'fallback-key')

    def test_cross_origin_cannot_change_key(self):
        response=self.client.post('/api/captions/provider',json={'api_key':'malicious'},headers={'Origin':'https://evil.test'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(Store(self.root/'social.db').get_caption_provider(),{})
