"""Downloader subprocesses must use the app's Python even without a PATH alias."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import downloader
import database


class DownloaderRuntimeTests(unittest.TestCase):
    def test_browser_fallback_downloads_channel_urls_after_both_apis_fail(self):
        with patch.object(downloader.subprocess, 'check_output', side_effect=OSError('Extractor blocked')), \
                patch.object(downloader.urllib.request, 'urlopen', side_effect=OSError('API blocked')), \
                patch('services.channel_browser.scan_channel_urls', return_value=['https://www.tiktok.com/@example/video/12']), \
                patch.object(downloader, 'download_single_video', return_value={'video_filename': 'fixture.mp4'}):
            result = downloader.download_channel_videos('https://www.tiktok.com/@example', limit=1)
        self.assertEqual(result, [('https://www.tiktok.com/@example/video/12', {'video_filename': 'fixture.mp4'})])

    def test_browser_only_duplicates_are_counted_and_not_downloaded_again(self):
        with patch.object(downloader.subprocess, 'check_output', side_effect=OSError('Extractor blocked')), \
                patch.object(downloader.urllib.request, 'urlopen', side_effect=OSError('API blocked')), \
                patch('services.channel_browser.scan_channel_urls', return_value=['https://www.tiktok.com/@example/video/12']), \
                patch.object(downloader, 'download_single_video', side_effect=database.DuplicateVideo({'id': 'existing'})):
            result = downloader.download_channel_videos('https://www.tiktok.com/@example', limit=1)
        self.assertEqual(result, [])
        self.assertEqual(result.skipped_duplicates, 1)

    def test_manual_verification_progress_reaches_download_and_render_record(self):
        import app as studio
        for process in (studio.process_download_task, studio.process_download_and_render_task):
            with self.subTest(process=process.__name__), tempfile.TemporaryDirectory() as directory:
                seen = []
                def scan(url, limit, *, progress):
                    progress('Hoàn thành CAPTCHA thủ công trong Chrome')
                    seen.append(database.get_all_videos()[0]['log'])
                    result = downloader.DownloadResults()
                    result.skipped_duplicates = 1
                    return result
                with patch.object(database, 'DB_FILE', str(Path(directory)/'videos.json')), \
                        patch.object(downloader, 'download_channel_videos', side_effect=scan):
                    process('https://www.tiktok.com/@example')
                self.assertEqual(seen, ['Hoàn thành CAPTCHA thủ công trong Chrome'])

    def test_channel_scan_runs_inside_current_python_without_python_on_path(self):
        with tempfile.TemporaryDirectory() as directory:
            # A local extractor fixture exercises the real subprocess boundary.
            Path(directory, 'yt_dlp.py').write_text('print("12345")\n')
            with patch.dict(os.environ, {'PATH': directory, 'PYTHONPATH': directory}), \
                    patch.object(downloader, 'download_single_video', return_value={'video_filename': 'fixture.mp4'}), \
                    patch.object(downloader.urllib.request, 'urlopen', side_effect=OSError('No fallback network in test')):
                result = downloader.download_channel_videos('https://www.tiktok.com/@example', limit=1)
            self.assertEqual(result, [('https://www.tiktok.com/@example/video/12345', {'video_filename': 'fixture.mp4'})])
