import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
import database
from services import downloader


class VideoDeletionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ('downloads', 'outputs', 'static/thumbnails'):
            (self.root/name).mkdir(parents=True)
        db = patch.object(database, 'DB_FILE', str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        for owner, name, value in [(studio, 'DOWNLOADS_DIR', str(self.root/'downloads')),
                                    (studio, 'OUTPUTS_DIR', str(self.root/'outputs')),
                                    (studio, 'STATIC_DIR', str(self.root/'static'))]:
            mock = patch.object(owner, name, value); mock.start(); self.addCleanup(mock.stop)
        self.client = studio.app.test_client()
        database._save_data([{'id': 'vid_one', 'stt': 1, 'title': 'Keep title', 'caption': 'Keep caption',
                              'status': 'completed', 'tiktok_url': 'https://www.tiktok.com/@old/video/12345',
                              'video_filename': 'tiktok_12345.mp4', 'output_filename': 'cozy_stickman_vid_one_9_16.mp4',
                              'thumbnail': '/static/thumbnails/one.jpg'}])
        (self.root/'downloads/tiktok_12345.mp4').write_bytes(b'original bytes')
        (self.root/'outputs/cozy_stickman_vid_one_9_16.mp4').write_bytes(b'output')
        (self.root/'outputs/antigravity_midnight_stickman_vid_one_9_16.mp4').write_bytes(b'AI output')
        (self.root/'static/thumbnails/one.jpg').write_bytes(b'JPEG')

    def test_delete_retains_record_and_identity_but_removes_media(self):
        response = self.client.delete('/api/video/vid_one')
        self.assertEqual(response.status_code, 200)
        record = database.get_video('vid_one', include_deleted=True)
        self.assertTrue(record['deleted_at'])
        self.assertEqual(record['status'], 'deleted')
        self.assertEqual(record['status_before_delete'], 'completed')
        self.assertEqual(record['title'], 'Keep title')
        self.assertEqual(record['caption'], 'Keep caption')
        self.assertEqual(record['source_hash'], hashlib.sha256(b'original bytes').hexdigest())
        self.assertIsNone(database.get_video('vid_one'))
        self.assertEqual(database.get_all_videos(), [])
        self.assertFalse(list((self.root/'downloads').glob('*.mp4')))
        self.assertFalse(list((self.root/'outputs').glob('*.mp4')))
        self.assertFalse((self.root/'static/thumbnails/one.jpg').exists())
        self.assertEqual(self.client.delete('/api/video/vid_one').status_code, 200)

    def test_deleted_records_block_same_source_with_different_author_or_tracking_url(self):
        self.client.delete('/api/video/vid_one')
        with patch.object(studio.threading, 'Thread') as thread:
            for endpoint in ('/api/download', '/api/download-and-render'):
                response = self.client.post(endpoint, json={'url': 'https://m.tiktok.com/@new/video/12345?share=changed'})
                self.assertEqual(response.status_code, 409)
                self.assertIn('đã xóa', response.json['message'])
            thread.assert_not_called()

    def test_deleted_record_cannot_receive_late_caption_or_render_updates(self):
        self.client.delete('/api/video/vid_one')
        database.update_video_status('vid_one', 'completed', log_msg='late')
        result = [{'video_id': 'vid_one', 'original': 'Keep caption', 'caption': 'Late AI'}]
        database.apply_caption_results(result)
        self.assertIn('error', result[0])
        self.assertEqual(database.update_video_caption('vid_one', 'Late', 'Keep caption'), 'missing')
        self.assertEqual(database.get_video('vid_one', include_deleted=True)['caption'], 'Keep caption')
        self.assertIsNone(database.get_video('vid_one'))

    def test_processing_video_is_not_deleted(self):
        database.update_video_status('vid_one', 'processing')
        self.assertEqual(self.client.delete('/api/video/vid_one').status_code, 409)
        self.assertTrue((self.root/'downloads/tiktok_12345.mp4').exists())
        self.assertIsNotNone(database.get_video('vid_one'))

    def test_path_traversal_and_other_records_render_are_not_deleted(self):
        outside = self.root/'outside.mp4'; outside.write_bytes(b'keep')
        data = database._load_data(); data[0]['video_filename'] = '../outside.mp4'; database._save_data(data)
        other = self.root/'outputs/cozy_stickman_vid_one_extra_9_16.mp4'; other.write_bytes(b'keep other')
        # Different record IDs must not be interpreted as variants of this record.
        data.append({'id': 'vid_one_extra', 'stt': 2, 'status': 'completed', 'output_filename': other.name})
        database._save_data(data)
        self.client.delete('/api/video/vid_one')
        self.assertEqual(outside.read_bytes(), b'keep')
        self.assertEqual(other.read_bytes(), b'keep other')

    def test_content_hash_detects_deleted_video_and_cleans_only_new_download(self):
        self.client.delete('/api/video/vid_one')
        new_file = self.root/'downloads/new_unique.mp4'; new_file.write_bytes(b'original bytes')
        result = {'title': 'Another caption', 'video_filename': new_file.name, 'thumbnail': '', 'duration_sec': 3}
        with patch.object(downloader, 'DOWNLOAD_DIR', str(self.root/'downloads')), \
             patch.object(downloader, '_download_single_video', return_value=result):
            with self.assertRaises(database.DuplicateVideo):
                downloader.download_single_video('https://vt.tiktok.com/new-link/')
        self.assertFalse(new_file.exists())

    def test_atomic_insert_checks_deleted_sources_and_stt_never_reuses_tombstone(self):
        database.delete_video('vid_one')
        with self.assertRaises(database.DuplicateVideo):
            database.add_video('Same', 'https://www.tiktok.com/@other/video/12345', 'other.mp4')
        second = database.add_video('Different', 'https://www.tiktok.com/@other/video/67890', 'new.mp4')
        self.assertEqual(second['stt'], 2)
        self.assertNotEqual(second['id'], 'vid_one')

    def test_duplicate_check_endpoint_and_channel_skip_deleted_sources_without_fetching_media(self):
        self.client.delete('/api/video/vid_one')
        response = self.client.get('/api/videos/check-duplicate', query_string={'url': 'https://www.tiktok.com/@new/video/12345?x=2'})
        self.assertEqual(response.json['video_id'], 'vid_one')
        self.assertTrue(response.json['deleted'])
        with patch.object(downloader.subprocess, 'check_output', return_value='12345\n12345\n'), \
             patch.object(downloader, '_download_single_video', side_effect=AssertionError('Do not fetch duplicate media')):
            results = downloader.download_channel_videos('https://www.tiktok.com/@old')
        self.assertEqual(results, [])
        self.assertEqual(results.skipped_duplicates, 1)

    def test_shared_media_remains_for_active_record(self):
        data = database._load_data()
        data.append({'id': 'vid_two', 'stt': 2, 'status': 'completed', 'video_filename': data[0]['video_filename']})
        database._save_data(data)
        response = self.client.delete('/api/video/vid_one')
        self.assertGreater(response.json['shared_files_retained'], 0)
        self.assertTrue((self.root/'downloads/tiktok_12345.mp4').exists())
        self.assertIsNotNone(database.get_video('vid_two'))
        from services.social.daily import ready_content
        tombstone = database.get_video('vid_one', include_deleted=True)
        tombstone['status'] = 'completed'  # Even accidentally reclassified history is not a candidate.
        self.assertEqual(ready_content([tombstone], self.root/'outputs'), [])

    def test_failed_file_removal_leaves_tombstone_and_can_be_retried(self):
        original = Path.unlink
        def unlink(path, *args, **kwargs):
            if path.name == 'tiktok_12345.mp4':
                raise PermissionError('Open video')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', unlink):
            response = self.client.delete('/api/video/vid_one')
        self.assertEqual(response.status_code, 503)
        self.assertTrue(database.get_video('vid_one', include_deleted=True)['deleted_at'])
        self.assertTrue((self.root/'downloads/tiktok_12345.mp4').exists())
        self.assertEqual(self.client.delete('/api/video/vid_one').status_code, 200)
        self.assertFalse((self.root/'downloads/tiktok_12345.mp4').exists())

    def test_channel_with_all_duplicates_does_not_report_tiktok_block_or_create_active_record(self):
        self.client.delete('/api/video/vid_one')
        results = downloader.DownloadResults(); results.skipped_duplicates = 1
        with patch.object(downloader, 'download_channel_videos', return_value=results):
            studio.process_download_task('https://www.tiktok.com/@old')
        self.assertEqual(database.get_all_videos(), [])
        self.assertEqual(len(database.get_all_videos(include_deleted=True)), 2)

    def test_duplicate_insert_and_download_attachment_are_atomic(self):
        placeholder = database.add_video('Waiting', 'https://vt.tiktok.com/new-link/', '')
        with self.assertRaises(database.DuplicateVideo):
            database.attach_download(placeholder['id'], {'video_filename': 'different.mp4', 'source_video_id': '12345'})
        self.assertEqual(database.get_video(placeholder['id'])['video_filename'], '')

    def test_failed_atomic_record_write_never_destroys_existing_history(self):
        before = Path(database.DB_FILE).read_bytes()
        with patch.object(database.os, 'replace', side_effect=OSError('Disk error')):
            with self.assertRaises(OSError):
                database.delete_video('vid_one')
        self.assertEqual(Path(database.DB_FILE).read_bytes(), before)
        self.assertIsNotNone(database.get_video('vid_one'))

    def test_corrupt_history_blocks_new_writes_instead_of_losing_tombstones(self):
        Path(database.DB_FILE).write_text('{broken JSON', encoding='utf-8')
        with self.assertRaises(RuntimeError):
            database.add_video('New', 'https://www.tiktok.com/@test/video/99999', 'new.mp4')
        self.assertEqual(Path(database.DB_FILE).read_text(encoding='utf-8'), '{broken JSON')

    def test_render_starting_during_delete_preflight_blocks_unlink_atomically(self):
        from services import video_deletion
        digest = video_deletion.hashlib.file_digest
        def begin_render(stream, algorithm):
            database.update_video_status('vid_one', 'processing')
            return digest(stream, algorithm)
        with patch.object(video_deletion.hashlib, 'file_digest', side_effect=begin_render):
            response = self.client.delete('/api/video/vid_one')
        self.assertEqual(response.status_code, 409)
        self.assertIsNotNone(database.get_video('vid_one'))
        self.assertTrue((self.root/'downloads/tiktok_12345.mp4').exists())


if __name__ == '__main__':
    unittest.main()
