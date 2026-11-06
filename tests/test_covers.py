import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import database
from services.covers import images
from services.social.store import Store, media_hash, Conflict


class CoverTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        db = patch.object(database, 'DB_FILE', str(self.root/'videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id': 'one', 'stt': 1, 'title': 'Một câu chuyện về lòng tử tế #hashtag', 'status': 'completed'}])

    def image_bytes(self):
        stream = io.BytesIO(); Image.new('RGB', (600, 900), '#81B29A').save(stream, 'PNG')
        return stream.getvalue()

    def test_image_render_creates_two_valid_jpegs_and_keeps_unicode_title(self):
        cover = images.save_cover('one', self.image_bytes(), 'Sống tử tế mỗi ngày', self.root/'covers', mode='upload')
        self.assertEqual(database.get_video('one')['cover']['title'], 'Sống tử tế mỗi ngày')
        for shape, size in [('portrait', (1080, 1920)), ('landscape', (1280, 720))]:
            path = images.cover_path(cover, shape, self.root/'covers')
            with Image.open(path) as picture:
                self.assertEqual(picture.size, size)
                self.assertEqual(picture.format, 'JPEG')

    def test_invalid_images_titles_and_paths_rejected(self):
        for payload in (b'<svg onload=alert(1)>', b'not an image', b'x'*(images.MAX_BYTES+1)):
            with self.assertRaises(ValueError):
                images.save_cover('one', payload, 'Title', self.root/'covers', mode='upload')
        with self.assertRaises(ValueError):
            images.save_cover('one', self.image_bytes(), 'x'*101, self.root/'covers', mode='upload')
        self.assertIsNone(images.cover_path({'portrait_filename': '../outside.jpg'}, 'portrait', self.root))
        with self.assertRaises(ValueError):
            images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload', focus=[float('nan'), .5])

    def test_frame_selection_and_worker_generation_never_write_library(self):
        import cv2
        import numpy as np
        path = self.root/'source.mp4'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 96))
        self.assertTrue(writer.isOpened())
        for index in range(20):
            writer.write(np.full((96,64,3), index*10, dtype=np.uint8))
        writer.release()
        before = Path(database.DB_FILE).read_bytes()
        with patch.object(database, 'save_video_cover', side_effect=AssertionError('Worker must not write JSON')):
            with images.scheduled_cover('one', path, self.root/'covers') as cover:
                self.assertEqual(cover['mode'], 'frame')
                self.assertTrue(Path(cover['portrait_path']).is_file())
                generated = Path(cover['portrait_path'])
        self.assertFalse(generated.exists())
        self.assertEqual(Path(database.DB_FILE).read_bytes(), before)
        with self.assertRaises(ValueError):
            images.frame_cover('one', path, 'Title', self.root/'covers', timestamp=9)
        saved = images.frame_cover('one', path, 'Title', self.root/'covers', timestamp=.6)
        self.assertEqual(saved['timestamp'], .6)
        self.assertEqual(database.get_video('one')['cover']['mode'], 'frame')

    def test_cover_save_preserves_transcript_persistence(self):
        self.assertTrue(database.update_video_transcript('one', 'Lời thoại nguyên bản', 'fingerprint'))
        images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload')
        self.assertEqual(database.get_video('one')['transcript'], 'Lời thoại nguyên bản')

    def test_crop_focus_selects_different_region(self):
        source = Image.new('RGB', (200,100), 'red')
        source.paste('blue', (100,0,200,100))
        self.assertEqual(images.compose(source, '', (100,100), (0,.5)).getpixel((50,50)), (255,0,0))
        self.assertEqual(images.compose(source, '', (100,100), (1,.5)).getpixel((50,50)), (0,0,255))

    def test_existing_cover_uses_current_video_ratio_without_discarding_image(self):
        cover = images.save_cover('one', self.image_bytes(), 'User title', self.root/'covers', mode='upload')
        database.update_video_aspect_ratio('one', '16:9')
        payload = images.ensure_cover('one', self.root/'unused.mp4', self.root/'covers')
        self.assertEqual(payload['aspect_ratio'], '16:9')
        self.assertEqual(database.get_video('one')['cover']['revision'], cover['revision'])
        with images.scheduled_cover('one', self.root/'unused.mp4', self.root/'covers') as scheduled:
            self.assertEqual(scheduled['aspect_ratio'], '16:9')
            self.assertEqual(scheduled['title'], 'User title')

    def test_old_schedule_schema_migrates_without_cover(self):
        import sqlite3
        path = self.root/'social.sqlite3'
        store = Store(path); media = self.root/'video.mp4'; media.write_bytes(b'video')
        batch = store.create_batch('one', media, 'caption', 100, False, 'old-schema-key')
        from contextlib import closing
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute('ALTER TABLE batches DROP COLUMN cover_json')
            connection.execute('ALTER TABLE tasks DROP COLUMN cover_state')
            connection.execute('ALTER TABLE tasks DROP COLUMN cover_message')
        restored = Store(path).get_batch(batch['id'])
        self.assertEqual(json.loads(restored['cover_json']), {})
        self.assertEqual({task['cover_state'] for task in restored['tasks']}, {'none'})

    def test_deleted_record_does_not_receive_cover(self):
        database.delete_video('one')
        with self.assertRaises(ValueError):
            images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload')
        self.assertFalse(list((self.root/'covers').glob('*.jpg')))

    def test_schedule_freezes_cover_and_worker_claim_contains_snapshot(self):
        cover = images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload')
        payload = images.cover_payload(cover, self.root/'covers')
        store = Store(self.root/'social.sqlite3')
        video = self.root/'video.mp4'; video.write_bytes(b'video')
        batch = store.create_batch('one', video, 'caption', 100, False, 'cover-test-one', cover=payload)
        snapshot = json.loads(batch['cover_json'])
        original = Path(payload['portrait_path']); original.write_bytes(b'changed after scheduling')
        self.assertEqual(media_hash(snapshot['portrait_path']), snapshot['portrait_hash'])
        self.assertNotEqual(snapshot['portrait_path'], str(original))
        owner = store.begin_login('facebook', now=1); store.complete_login('facebook', owner, 'id', now=2)
        task = store.claim_next('worker', now=100)
        self.assertEqual(task['cover']['portrait_hash'], snapshot['portrait_hash'])
        self.assertEqual(task['cover_state'], 'pending')

    def test_idempotency_rejects_a_different_cover_for_same_request(self):
        store = Store(self.root/'social.sqlite3'); video = self.root/'video.mp4'; video.write_bytes(b'video')
        one = images.save_cover('one', self.image_bytes(), 'One', self.root/'covers', mode='upload')
        store.create_batch('one', video, 'caption', 100, False, 'same-cover-key', cover=images.cover_payload(one, self.root/'covers'))
        two = images.save_cover('one', self.image_bytes(), 'Two', self.root/'covers', mode='upload')
        with self.assertRaises(Conflict):
            store.create_batch('one', video, 'caption', 100, False, 'same-cover-key', cover=images.cover_payload(two, self.root/'covers'))

    def test_modified_scheduled_cover_fails_before_browser_publisher(self):
        from services.social.worker import Worker
        cover = images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload')
        store = Store(self.root/'social.sqlite3'); video = self.root/'video.mp4'; video.write_bytes(b'video')
        batch = store.create_batch('one', video, 'caption', 100, False, 'hash-check-key', cover=images.cover_payload(cover, self.root/'covers'))
        frozen = json.loads(batch['cover_json']); Path(frozen['portrait_path']).write_bytes(b'tampered')
        owner = store.begin_login('facebook', now=1); store.complete_login('facebook', owner, 'id', now=2)
        with patch('services.social.browser.BrowserPublisher.__call__', side_effect=AssertionError('Do not post a changed cover')):
            Worker(store).run_once(now=100)
        task = next(t for t in store.get_batch(batch['id'])['tasks'] if t['platform']=='facebook')
        self.assertEqual(task['state'], 'failed')
        self.assertIn('Ảnh bìa', task['message'])

    def test_api_upload_retitle_and_deleted_record_do_not_expose_paths(self):
        import app as studio
        with patch.dict(studio.app.config, TESTING=True, SOCIAL_STORE=Store(self.root/'social.sqlite3'),
                        COVERS_DIR=str(self.root/'covers')):
            client = studio.app.test_client()
            self.assertFalse(client.get('/api/covers/videos/one').json['cover']['ready'])
            response = client.post('/api/covers/videos/one', data={
                'title': 'Sống tử tế', 'image': (io.BytesIO(self.image_bytes()), 'cover.png')})
            self.assertEqual(response.status_code, 200)
            cover = response.json['cover']
            self.assertTrue(cover['ready'])
            self.assertNotIn(str(self.root), response.get_data(as_text=True))
            picture = client.get(cover['images']['portrait'])
            self.assertEqual(picture.status_code, 200)
            self.assertEqual(picture.mimetype, 'image/jpeg')
            picture.close()
            changed = client.post('/api/covers/videos/one', json={'mode':'title', 'title':'Bình yên mỗi ngày'})
            self.assertEqual(changed.status_code, 200)
            self.assertNotEqual(changed.json['cover']['revision'], cover['revision'])
            self.assertEqual(changed.json['cover']['title'], 'Bình yên mỗi ngày')
            bad = client.post('/api/covers/videos/one', data={'image': (io.BytesIO(b'<svg>bad</svg>'), 'x.jpg')})
            self.assertEqual(bad.status_code, 400)
            database.delete_video('one')
            self.assertEqual(client.get(cover['images']['portrait']).status_code, 404)
            self.assertEqual(client.post('/api/covers/videos/one', json={'mode':'title','title':'X'}).status_code, 404)

    def test_deleting_library_cover_keeps_frozen_schedule_images(self):
        from services.video_deletion import delete_media
        cover = images.save_cover('one', self.image_bytes(), 'Title', self.root/'covers', mode='upload')
        store = Store(self.root/'social.sqlite3'); video = self.root/'video.mp4'; video.write_bytes(b'video')
        batch = store.create_batch('one', video, 'caption', 100, False, 'delete-cover-key',
                                   cover=images.cover_payload(cover, self.root/'covers'))
        frozen = json.loads(batch['cover_json'])
        record = database.get_video('one'); database.delete_video('one')
        errors, _ = delete_media(record, self.root/'downloads', self.root/'outputs', self.root/'static', self.root/'covers')
        self.assertEqual(errors, [])
        self.assertFalse(list((self.root/'covers').glob('*.jpg')))
        self.assertTrue(Path(frozen['portrait_path']).is_file())
        self.assertTrue(Path(frozen['landscape_path']).is_file())


if __name__ == '__main__':
    unittest.main()
