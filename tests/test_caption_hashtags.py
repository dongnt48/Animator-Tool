import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services.social.store import Store


class CaptionHashtagTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        db=patch.object(database,'DB_FILE',str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        settings=patch.dict(studio.app.config,SOCIAL_STORE=Store(self.root/'social.db'))
        settings.start(); self.addCleanup(settings.stop)
        network=patch('urllib.request.urlopen',side_effect=AssertionError('No real provider'))
        network.start(); self.addCleanup(network.stop)
        database._save_data([{'id':'one','title':'Old #legacy'}])
        self.client=studio.app.test_client()

    def test_empty_default_and_settings_persist_across_store_reopen(self):
        response=self.client.get('/api/captions/settings')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['hashtags'],'')
        response=self.client.post('/api/captions/settings',json={'hashtags':'dongluc, #SongTichCuc\n#dongluc'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['hashtags'],'#dongluc #SongTichCuc')
        self.assertEqual(Store(self.root/'social.db').get_caption_hashtags(),'#dongluc #SongTichCuc')

    def test_invalid_settings_leave_saved_value_unchanged(self):
        self.client.post('/api/captions/settings',json={'hashtags':'#saved'})
        for value in [None,{},'x'*1001,'#bad-tag','<script>','#']:
            self.assertEqual(self.client.post('/api/captions/settings',json={'hashtags':value}).status_code,400)
        self.assertEqual(self.client.get('/api/captions/settings').json['hashtags'],'#saved')

    def test_generated_hashtags_removed_and_only_user_tags_are_appended(self):
        self.client.post('/api/captions/settings',json={'hashtags':'#MyTag #MyBrand'})
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'New message. #AIinvented #legacy'}}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':['one']})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['results'][0]['caption'],'New message.\n\n#MyTag #MyBrand')
        self.assertEqual(database.get_video('one')['caption'],'New message.\n\n#MyTag #MyBrand')

    def test_empty_settings_make_new_caption_tag_free_and_explicit_save_preserves_manual_tags(self):
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'Message #unwanted'}}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':['one']})
        self.assertEqual(response.json['results'][0]['caption'],'Message')
        self.client.post('/api/captions/save',json={'items':[{'video_id':'one','caption':'Edited #manual','expected_caption':'Message'}]})
        self.assertEqual(database.get_video('one')['caption'],'Edited #manual')

    def test_request_snapshot_overrides_later_saved_settings_without_changing_settings(self):
        self.client.post('/api/captions/settings',json={'hashtags':'#NewSettings'})
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'Message'}}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':['one'],'hashtags':'#RunSnapshot'})
        self.assertEqual(response.json['results'][0]['caption'],'Message\n\n#RunSnapshot')
        self.assertEqual(self.client.get('/api/captions/settings').json['hashtags'],'#NewSettings')

    def test_hashtag_only_result_fails_without_hiding_other_results(self):
        database._save_data([{'id':'one','title':'First'},{'id':'two','title':'Second'}])
        with patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'#onlytag'},'two':{'caption':'Actual content #unwanted'}}):
            response=self.client.post('/api/captions/rewrite',json={'video_ids':['one','two']})
        self.assertIn('error',response.json['results'][0])
        self.assertEqual(response.json['results'][1]['caption'],'Actual content')

    def test_unicode_tags_are_normalized_and_csharp_text_is_preserved(self):
        from services.captions.hashtags import normalize_hashtags,finish_caption
        self.assertEqual(normalize_hashtags('#động_lực #ĐỘNG_LỰC'),'#động_lực')
        self.assertEqual(finish_caption('Học C# mỗi ngày #hashtag',''),'Học C# mỗi ngày')
