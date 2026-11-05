import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database


class DirectCaptionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        db=patch.object(database,'DB_FILE',str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)

    def test_results_apply_only_successful_unchanged_records(self):
        database._save_data([{'id':'one','title':'Old'},{'id':'two','title':'Other','caption':'Manual'}])
        results=[{'video_id':'one','original':'Old','caption':'AI'},
                 {'video_id':'two','original':'Other','caption':'Stale'},
                 {'video_id':'missing','original':'None','caption':'AI'}]
        database.apply_caption_results(results)
        self.assertEqual(database.get_video('one')['caption'],'AI')
        self.assertNotIn('caption_ai',database.get_video('one'))
        self.assertEqual(database.get_video('two')['caption'],'Manual')
        self.assertIn('error',results[1]); self.assertIn('error',results[2])

    def test_migration_applies_valid_draft_and_preserves_stale_current_caption(self):
        database._save_data([
            {'id':'one','title':'Old','caption_ai':{'original':'Old','caption':'Pending'}},
            {'id':'two','title':'Other','caption':'Manual','caption_ai':{'original':'Other','caption':'Stale'}},
        ])
        database.migrate_caption_drafts()
        self.assertEqual(database.get_video('one')['caption'],'Pending')
        self.assertEqual(database.get_video('two')['caption'],'Manual')
        self.assertTrue((self.root/'social'/'videos-before-direct-captions.json').is_file())
        self.assertTrue(all('caption_ai' not in item for item in database.get_all_videos()))
        before=(self.root/'videos.json').read_bytes()
        database.migrate_caption_drafts()
        self.assertEqual((self.root/'videos.json').read_bytes(),before)
