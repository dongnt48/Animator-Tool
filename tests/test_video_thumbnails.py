import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
from services.social.thumbnails import video_thumbnail


class VideoThumbnailTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.media=self.root/'media'; self.media.mkdir()
        self.cache=self.root/'cache'
        (self.media/'source.mp4').write_bytes(b'video')
        self.video={'video_filename':'source.mp4','output_filename':'source.mp4'}

    def test_cache_reuses_frame_and_source_changes_invalidate_it(self):
        def convert(command,**kwargs):
            Path(command[-1]).write_bytes(b'jpeg fixture')
        with patch('services.social.thumbnails.subprocess.run',side_effect=convert) as run:
            first=video_thumbnail(self.video,'original',self.media,self.media,self.cache)
            self.assertEqual(video_thumbnail(self.video,'original',self.media,self.media,self.cache),first)
            self.assertEqual(run.call_count,1)
            (self.media/'source.mp4').write_bytes(b'rendered differently')
            second=video_thumbnail(self.video,'original',self.media,self.media,self.cache)
            self.assertNotEqual(first,second)
            self.assertEqual(run.call_count,2)

    def test_unsafe_missing_and_unknown_media_do_not_run_ffmpeg(self):
        with patch('services.social.thumbnails.subprocess.run',side_effect=AssertionError('Must not run')):
            for video,kind in [({'video_filename':'../secret.mp4'},'original'),({'video_filename':'missing.mp4'},'original'),(self.video,'invalid')]:
                with self.assertRaises(FileNotFoundError):
                    video_thumbnail(video,kind,self.media,self.media,self.cache)

    def test_failed_conversion_cleans_temporary_image(self):
        with patch('services.social.thumbnails.subprocess.run',side_effect=subprocess.TimeoutExpired('ffmpeg',15)):
            with self.assertRaises(subprocess.TimeoutExpired):
                video_thumbnail(self.video,'original',self.media,self.media,self.cache)
        self.assertEqual(list(self.cache.iterdir()),[])
