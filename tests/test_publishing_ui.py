import importlib.util
import logging
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
from services.social.store import Store


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install Playwright for UI integration tests')
class PublishingUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.mp4'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'lavfi', '-i',
                            'color=c=0xe5dcc5:s=144x256:r=5', '-t', '0.4', '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', str(path)], check=True, capture_output=True)
            cls.video_bytes = path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        from werkzeug.serving import make_server
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        outputs = root / 'outputs'
        outputs.mkdir()
        (outputs / 'ready.mp4').write_bytes(self.video_bytes)
        self.media_route = patch.object(studio, 'OUTPUTS_DIR', str(outputs))
        self.media_route.start()
        self.addCleanup(self.media_route.stop)
        self.store = Store(root / 'social.sqlite3')
        self.caption = "Caption O'Brien <img src=x onerror=window.unwantedScript=1> #hashtag"
        video = {'id': 'one', 'status': 'completed', 'title': self.caption, 'output_filename': 'ready.mp4'}
        self.settings = patch.dict(studio.app.config, SOCIAL_STORE=self.store, SOCIAL_OUTPUTS_DIR=str(outputs), TESTING=True)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.lookup = patch('database.get_all_videos', return_value=[video])
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        self.single = patch('database.get_video', return_value=video)
        self.single.start()
        self.addCleanup(self.single.stop)
        self.server = make_server('127.0.0.1', 0, studio.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.page = self.browser.new_page(viewport={'width':1440,'height':1000}, timezone_id='Asia/Bangkok')
        self.addCleanup(self.page.close)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing?video=one')
        self.page.locator('#videoSelect option[value=one]').wait_for(state='attached')

    def close_server(self):
        self.server.shutdown()
        self.thread.join(timeout=3)
        self.server.server_close()

    def test_schedule_real_ui_reuses_caption_and_creates_all_targets(self):
        from playwright.sync_api import expect
        self.assertEqual(self.page.locator('#captionPreview').inner_text(), self.caption)
        self.assertIsNone(self.page.evaluate('window.unwantedScript'))
        self.page.locator('#youtubeAudience').select_option('no')
        self.page.locator('#confirmPublish').check()
        self.page.get_by_role('button', name='Lên lịch cho cả 5 nền tảng').click()
        expect(self.page.locator('#notice')).to_contain_text('Đã lưu lịch cho cả 5 nền tảng')
        self.page.get_by_role('navigation', name='Điều hướng quản trị').get_by_role('link', name='Kết quả đăng').click()
        expect(self.page.locator('.task')).to_have_count(5)
        batches = self.store.list_batches()
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]['caption'], self.caption)
        self.assertEqual({task['state'] for task in batches[0]['tasks']}, {'queued'})
        self.assertEqual(self.errors, [])

    def test_mobile_and_desktop_have_no_horizontal_overflow(self):
        screenshots = Path('.superpowers/sdd/2026-11-04-social-publishing')
        screenshots.mkdir(parents=True, exist_ok=True)
        for route in ['', '/schedule', '/accounts', '/results', '/new', '/captions']:
            self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing{route}')
            self.page.wait_for_function("document.getElementById('workerStatus').textContent !== 'Đang kiểm tra…'")
            for width, label in [(1920, 'wide'), (1440, 'desktop'), (390, 'mobile')]:
                self.page.set_viewport_size({'width':width,'height':1000})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width, route)
                self.assertEqual(self.page.evaluate('getComputedStyle(document.body).backgroundColor'), 'rgb(250, 246, 238)')
                if width == 1920:
                    self.assertEqual(self.page.locator('main').bounding_box()['x'], 232)
                    box = self.page.locator('main').bounding_box()
                    self.assertEqual(box['x'] + box['width'], 1920)
                self.page.screenshot(path=str(screenshots / f'{route.strip("/") or "overview"}-{label}.png'), full_page=True)
        self.assertEqual(self.errors, [])

    def test_failed_destinations_remain_visible_in_compact_history(self):
        from playwright.sync_api import expect
        import time
        self.store.create_batch('one', str(Path(studio.OUTPUTS_DIR) / 'ready.mp4'), self.caption,
                                time.time(), False, 'compact-error-test')
        self.store.claim_next('no-connected-accounts')
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing/results')
        expect(self.page.locator('.batch')).to_have_attribute('open', '')
        expect(self.page.locator('.batch summary')).to_contain_text('5 cần xử lý')
        expect(self.page.get_by_role('button', name='Thử lại nền tảng này')).to_have_count(5)
        self.page.get_by_role('navigation', name='Điều hướng quản trị').get_by_role('link', name='Tổng quan').click()
        expect(self.page.locator('#metricAttention')).to_have_text('5')

    def test_admin_navigation_opens_account_settings_and_shows_real_metrics(self):
        from playwright.sync_api import expect
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing')
        expect(self.page.locator('#metricReady')).to_have_text('1')
        expect(self.page.locator('#metricAccounts')).to_have_text('0/5')
        expect(self.page.locator('#metricPublished')).to_have_text('0')
        self.page.get_by_role('navigation', name='Điều hướng quản trị').get_by_role('link', name='Tài khoản').click()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/publishing/accounts')
        expect(self.page.locator('#accounts .account')).to_have_count(5)
        expect(self.page.locator('.admin-nav a[href="/publishing/accounts"]')).to_have_attribute('aria-current','page')
        expect(self.page.locator('#dailyForm')).to_have_count(0)
        self.assertEqual(self.errors, [])

    def test_ui_retries_same_schedule_after_lost_response_even_when_time_passes(self):
        from playwright.sync_api import expect
        self.page.locator('#youtubeAudience').select_option('no')
        self.page.locator('#confirmPublish').check()
        def lose_response(route):
            route.fetch()
            route.abort('failed')
        self.page.route('**/api/social/batches', lose_response)
        self.page.get_by_role('button', name='Lên lịch cho cả 5 nền tảng').click()
        expect(self.page.locator('#notice')).to_have_attribute('data-error', 'true')
        self.assertEqual(len(self.store.list_batches()), 1)
        self.page.unroute('**/api/social/batches', lose_response)
        self.page.evaluate('Date.now = () => new Date(document.getElementById("scheduleAt").value).getTime() + 10000')
        self.page.get_by_role('button', name='Lên lịch cho cả 5 nền tảng').click()
        expect(self.page.locator('#notice')).to_contain_text('Đã lưu lịch cho cả 5 nền tảng', timeout=2000)
        self.assertEqual(len(self.store.list_batches()), 1)

    def test_daily_hours_are_saved_without_a_video_selection_and_dirty_hours_survive_refresh(self):
        from playwright.sync_api import expect
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing/schedule')
        self.page.wait_for_function("document.getElementById('dailySelection').value === 'random'")
        self.page.locator('#dailyTime').fill('08:00')
        self.page.get_by_role('button', name='Thêm giờ', exact=True).click()
        self.page.locator('#refreshStatus').click()
        expect(self.page.locator('#dailyTimes')).to_contain_text('08:00')
        self.page.locator('#dailyTime').fill('19:00')
        self.page.get_by_role('button', name='Thêm giờ', exact=True).click()
        self.page.locator('#dailyAudience').select_option('no')
        self.page.locator('#dailyEnabled').check()
        self.page.locator('#dailyConfirm').check()
        self.page.get_by_role('button', name='Lưu lịch hằng ngày', exact=True).click()
        expect(self.page.locator('#notice')).to_contain_text('Đã lưu lịch hằng ngày')
        self.assertEqual(self.store.get_daily()['times'], ['08:00','19:00'])
        self.assertTrue(self.store.get_daily()['enabled'])
        self.assertEqual(self.store.get_daily()['selection'], 'random')
        self.assertEqual(self.store.list_batches(), [])

    def test_separate_creation_page_preserves_download_controls_and_library_navigation(self):
        from playwright.sync_api import expect
        import json
        library = patch.object(studio, 'get_all_videos', return_value=[])
        library_mock=library.start()
        self.addCleanup(library.stop)
        self.page.route('https://cdnjs.cloudflare.com/**', lambda route: route.fulfill(status=200,body='',content_type='text/css'))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/create')
        expect(self.page.locator('.admin-sidebar')).to_be_visible()
        expect(self.page.locator('.admin-nav a[href="/create"]')).to_have_attribute('aria-current','page')
        expect(self.page.locator('#captionTools')).to_have_count(0)
        expect(self.page.locator('#videoTableBody')).to_have_count(0)
        expect(self.page.locator('#btnDownloadAndRender')).to_be_visible()
        expect(self.page.locator('#btnDownloadAndRender')).to_be_enabled()
        self.assertIn('linear-gradient',self.page.locator('#btnDownloadAndRender').evaluate('button => getComputedStyle(button).backgroundImage'))
        render_requests=[]
        def queue_fixture(route):
            render_requests.append(route.request.post_data_json)
            route.fulfill(status=200,content_type='application/json',body='{"status":"success","message":"Queued fixture only"}')
        self.page.route('**/api/download-and-render',queue_fixture)
        self.page.locator('#inputUrl').fill('https://www.tiktok.com/@test/video/12345')
        self.page.locator('#btnDownloadAndRender').click()
        expect(self.page.locator('#inputUrl')).to_have_value('')
        expect(self.page.locator('#btnDownloadAndRender')).to_be_enabled()
        self.assertEqual(len(render_requests),1)
        self.assertEqual(render_requests[0]['aspect_ratio'],'9:16')
        self.assertEqual(render_requests[0]['style'],'cozy')
        library_mock.return_value=[{'id':'queued','stt':1,'title':'Queued fixture','status':'processing','log':'Rendering fixture'}]
        self.page.evaluate('fetchVideos()')
        expect(self.page.locator('#creationActivity')).to_contain_text('Rendering fixture')
        library_mock.return_value=[{'id':'queued','stt':1,'title':'Queued fixture','status':'completed'}]
        self.page.evaluate('fetchVideos()')
        expect(self.page.locator('#statCompleted')).to_have_text('1')
        expect(self.page.locator('#creationActivity')).to_contain_text('Không có video đang xử lý')
        self.page.route('**/api/download', lambda route: route.fulfill(status=200, content_type='application/json',
                          body=json.dumps({'status':'success','message':'Queued fixture only'})))
        self.page.locator('#inputUrl').fill('https://www.tiktok.com/@test/video/12345')
        self.page.locator('#btnDownload').click()
        expect(self.page.locator('#inputUrl')).to_have_value('')
        for width in (1440, 390):
            self.page.set_viewport_size({'width':width,'height':1000})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
        self.page.screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/library-mobile.png',full_page=True)
        self.page.set_viewport_size({'width':1440,'height':1000})
        self.page.screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/library-desktop.png',full_page=True)
        self.page.get_by_role('navigation').get_by_role('link',name='Thư viện',exact=True).click()
        expect(self.page.locator('#videoTableBody')).to_be_visible()
        expect(self.page.locator('#captionTools')).to_be_visible()
        expect(self.page.locator('#inputUrl')).to_have_count(0)
        library_mock.return_value=[]
        self.page.wait_for_function('typeof window.fetchVideos === "function"')
        self.page.evaluate('fetchVideos()')
        expect(self.page.locator('#videoTableBody a[href="/create"]')).to_be_visible()
        self.page.get_by_role('navigation',name='Điều hướng quản trị').get_by_role('link',name='Lịch tự động').click()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/publishing/schedule')
        expect(self.page.locator('#dailyForm')).to_be_visible()
        self.assertEqual(self.errors,[])

    def test_ai_caption_preview_requires_explicit_save_and_keeps_original_title(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop()
        self.single.stop()
        db = patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'caption-videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':'one','stt':1,'title':'Original caption #tag','status':'completed','output_filename':'ready.mp4'}])
        provider=patch('services.captions.routes.rewrite_captions',side_effect=lambda items,instruction,**kwargs:{item['video_id']:{'caption':'AI caption #tag'} for item in items})
        provider.start(); self.addCleanup(provider.stop)
        dialogue=patch('services.captions.routes.dialogue_for_video',return_value='Fixture dialogue')
        dialogue.start(); self.addCleanup(dialogue.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing/captions?video=one')
        expect(self.page.locator('#captionSelectedCount')).to_have_text('1 đã chọn')
        expect(self.page.locator('#captionUseTranscript')).to_be_checked()
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionResults textarea')).to_have_value('AI caption')
        expect(self.page.locator('#captionResults')).to_contain_text('Lời thoại đã gửi (16 ký tự)')
        self.assertEqual(database.get_video('one')['caption'],'AI caption')
        self.page.locator('#captionResults textarea').fill('Approved edit #tag')
        self.page.get_by_role('button',name='Lưu caption này',exact=True).click()
        expect(self.page.locator('#notice')).to_contain_text('Đã lưu 1/1')
        self.assertEqual(database.get_video('one')['caption'],'Approved edit #tag')
        self.assertEqual(database.get_video('one')['title'],'Original caption #tag')
        self.assertEqual(self.errors,[])

    def test_caption_select_all_205_videos_sends_three_batches_and_restores_marks(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'bulk-captions.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':str(i),'stt':i,'title':'Original '+str(i)} for i in range(205)])
        sizes=[]
        def provider(items,instruction,**kwargs):
            sizes.append(len(items))
            return {item['video_id']:{'caption':'AI '+item['video_id']} for item in items}
        mock=patch('services.captions.routes.rewrite_captions',side_effect=provider)
        mock.start(); self.addCleanup(mock.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing/captions')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        expect(self.page.locator('#captionSelectedCount')).to_have_text('205 đã chọn')
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionResults textarea')).to_have_count(205,timeout=30000)
        expect(self.page.locator('#rewriteCaptions')).to_be_disabled()
        self.assertEqual(sizes,[100,100,5])
        expect(self.page.locator('#captionVideos .badge')).to_have_count(205)
        self.page.reload()
        expect(self.page.locator('#captionResults textarea')).to_have_count(0)
        expect(self.page.locator('#captionVideos .badge')).to_have_count(205)
        self.assertEqual(database.get_video('204')['caption'],'AI 204')
        self.assertEqual(self.errors,[])

    def test_library_shows_published_platform_and_its_receipt_link(self):
        from playwright.sync_api import expect
        import time
        video={'id':'one','stt':1,'title':'Caption #tag','status':'completed','output_filename':'ready.mp4',
               'video_filename':'original.mp4','tiktok_url':'https://www.tiktok.com/@test/video/12345'}
        library=patch.object(studio,'get_all_videos',return_value=[video])
        library.start(); self.addCleanup(library.stop)
        now=time.time()
        self.store.create_batch('one',str(Path(studio.OUTPUTS_DIR)/'ready.mp4'),'Caption #tag',now,False,'library-status-test')
        owner=self.store.begin_login('facebook')
        self.store.complete_login('facebook',owner,'42')
        task=self.store.claim_next('worker',now=now)
        self.store.mark_submitting(task['id'],'worker')
        self.store.finish(task['id'],'worker','published','OK','https://www.facebook.com/reel/12345')
        self.page.route('https://cdnjs.cloudflare.com/**',lambda route:route.fulfill(status=200,body='',content_type='text/css'))
        self.page.route('https://images.unsplash.com/**',lambda route:route.abort())
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        link=self.page.locator('.publication-chips a[data-state="published"]')
        expect(link).to_contain_text('Facebook · Đã đăng')
        expect(link).to_have_attribute('href','https://www.facebook.com/reel/12345')
        expect(self.page.get_by_role('columnheader',name='Đã Đăng Ở Đâu')).to_be_visible()
        self.assertEqual(self.errors,[])

    def test_caption_later_batch_network_error_keeps_earlier_drafts(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'partial-captions.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':str(i),'stt':i,'title':'Original '+str(i)} for i in range(101)])
        mock=patch('services.captions.routes.rewrite_captions',side_effect=lambda items,instruction,**kwargs:{item['video_id']:{'caption':'New'} for item in items})
        ai=mock.start(); self.addCleanup(mock.stop)
        requests=[]
        def intercept(route):
            requests.append(route.request.post_data_json['video_ids'])
            if len(requests)==2:
                route.fulfill(status=503,content_type='application/json',body='{"message":"Batch failed"}')
            else:
                route.continue_()
        self.page.route('**/api/captions/rewrite',intercept)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/publishing/captions')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#notice')).to_contain_text('Batch failed',timeout=30000)
        expect(self.page.locator('#captionResults textarea')).to_have_count(100)
        expect(self.page.locator('#saveAllCaptions')).to_be_disabled()
        self.assertEqual(ai.call_count,1)
        self.assertEqual(database.get_video('99')['caption'],'New')
        self.assertNotIn('caption_ai',database.get_video('100'))

    def test_library_rewrite_opens_individual_detail_for_review_and_save(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'inline-captions.json'))
        db.start(); self.addCleanup(db.stop)
        fixture=[{'id':str(i),'stt':i+1,'title':'Original '+str(i),'status':'new','video_filename':'original.mp4'} for i in range(2)]
        database._save_data(fixture)
        library=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        library.start(); self.addCleanup(library.stop)
        provider=patch('services.captions.routes.rewrite_captions',side_effect=lambda items,instruction,**kwargs:{item['video_id']:{'caption':'New #songtichcuc #dongluc #cuocsong'} for item in items})
        ai=provider.start(); self.addCleanup(provider.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        expect(self.page.locator('#captionSelectedCount')).to_have_text('2 đã chọn')
        # A periodic table replacement must preserve checkbox state.
        self.page.evaluate('fetchVideos()')
        expect(self.page.locator('#videoTableBody input[data-caption-video]:checked')).to_have_count(2)
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionBatchFeedback')).to_contain_text('Đã viết lại 2/2')
        expect(self.page.locator('#captionResults')).to_have_count(0)
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/')
        self.assertEqual(ai.call_count,1)
        self.page.locator('#videoTableBody .library-title-link').first.click()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/videos/0')
        expect(self.page.locator('#detailCaption')).to_have_value('New')
        expect(self.page.locator('#detailCurrentCaption')).to_have_text('New')
        expect(self.page.locator('#detailPublication')).to_contain_text('Chưa đăng')
        self.page.locator('#detailCaption').fill('Approved #dongluc')
        # A concurrent caption change must not be overwritten by this detail form.
        database.update_video_caption('0','Concurrent edit','New')
        self.page.locator('#detailSaveCaption').click()
        expect(self.page.locator('#notice')).to_contain_text('Caption đã thay đổi')
        self.assertEqual(database.get_video('0')['caption'],'Concurrent edit')
        self.page.reload()
        expect(self.page.locator('#detailCaption')).to_have_value('Concurrent edit')
        self.page.locator('#detailCaption').fill('Approved #dongluc')
        self.page.locator('#detailSaveCaption').click()
        expect(self.page.locator('#notice')).to_contain_text('Đã lưu')
        self.assertEqual(database.get_video('0')['caption'],'Approved #dongluc')
        for width in (1440,390):
            self.page.set_viewport_size({'width':width,'height':1000})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
        self.page.screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/video-detail-mobile.png',full_page=True)
        self.page.set_viewport_size({'width':1440,'height':1000})
        self.page.screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/video-detail-desktop.png',full_page=True)
        self.page.get_by_role('link',name='← Về thư viện').click()
        expect(self.page.locator('.caption-rewrite-mark')).to_have_count(2)
        expect(self.page.locator('.caption-rewrite-mark').first).to_have_text('Đã viết lại')
        self.page.reload()
        expect(self.page.locator('.caption-rewrite-mark')).to_have_count(2)
        self.assertEqual(self.errors,[])

    def test_caption_toolbar_scope_filters_selected_videos_and_all_mode_rewrites_them(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'scope-videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([
            {'id':'draft','stt':1,'title':'Draft original','caption_ai':{'original':'Draft original','caption':'Existing draft'}},
            {'id':'saved','stt':2,'title':'Saved original','caption':'Existing saved'},
            {'id':'new','stt':3,'title':'Never written'},
        ])
        lookup=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        lookup.start(); self.addCleanup(lookup.stop)
        calls=[]
        def provider(items,instruction,**kwargs):
            calls.append([item['video_id'] for item in items])
            return {item['video_id']:{'caption':'New caption #tag'} for item in items}
        mock=patch('services.captions.routes.rewrite_captions',side_effect=provider)
        mock.start(); self.addCleanup(mock.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        expect(self.page.locator('#captionRewriteMode')).to_have_value('unwritten')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        expect(self.page.locator('#captionEligibleCount')).to_have_text('1 sẽ viết')
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionBatchFeedback')).to_contain_text('Đã viết lại 1/1')
        expect(self.page.locator('#captionEligibleCount')).to_have_text('0 sẽ viết')
        expect(self.page.locator('#rewriteCaptions')).to_be_disabled()
        self.assertEqual(calls,[['new']])
        self.assertEqual(database.get_video('draft')['caption_ai']['caption'],'Existing draft')
        self.page.locator('#captionRewriteMode').select_option('all')
        expect(self.page.locator('#captionEligibleCount')).to_have_text('3 sẽ viết')
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionBatchFeedback')).to_contain_text('Đã viết lại 3/3')
        self.assertEqual(calls,[['new'],['draft','saved','new']])
        self.assertLess(self.page.locator('#captionTools').bounding_box()['height'],180)
        self.page.locator('#captionTools').screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/caption-toolbar-desktop.png')
        self.page.set_viewport_size({'width':390,'height':1000})
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.page.locator('#captionTools').screenshot(path='.superpowers/sdd/2026-11-04-social-publishing/caption-toolbar-mobile.png')
        self.assertEqual(self.errors,[])

    def test_manual_hashtags_settings_persist_and_rewrite_auto_saves_changes(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'hashtag-videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':'one','stt':1,'title':'Original #old'}])
        lookup=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        lookup.start(); self.addCleanup(lookup.stop)
        provider=patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'New message #Invented'}})
        provider.start(); self.addCleanup(provider.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('.caption-options-row summary').click()
        self.page.locator('#captionHashtags').fill('MyBrand, #MyTopic #mybrand')
        self.page.locator('#saveCaptionHashtags').click()
        expect(self.page.locator('#captionHashtagState')).to_have_text('Đã lưu')
        self.page.reload()
        expect(self.page.locator('#captionHashtags')).to_have_value('#MyBrand #MyTopic')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionBatchFeedback')).to_contain_text('Đã viết lại 1/1')
        self.assertEqual(database.get_video('one')['caption'],'New message\n\n#MyBrand #MyTopic')
        self.page.locator('.caption-options-row summary').click()
        self.page.locator('#captionHashtags').fill('')
        self.page.locator('#captionRewriteMode').select_option('all')
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionHashtagState')).to_have_text('Không thêm hashtag')
        expect(self.page.locator('#rewriteCaptions')).to_be_enabled()
        self.assertEqual(self.store.get_caption_hashtags(),'')
        self.assertEqual(database.get_video('one')['caption'],'New message')
        self.assertEqual(self.errors,[])

    def test_provider_settings_hide_key_and_use_saved_model_for_rewrite(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'provider-videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':'one','stt':1,'title':'Original'}])
        lookup=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        lookup.start(); self.addCleanup(lookup.stop)
        provider=patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'New'}})
        ai=provider.start(); self.addCleanup(provider.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('.caption-options-row summary').click()
        self.page.locator('#captionModel').fill('custom-model')
        self.page.locator('#captionApiKey').fill('fake-test-secret')
        expect(self.page.locator('#captionApiKey')).to_have_attribute('type','password')
        self.page.locator('#saveCaptionProvider').click()
        expect(self.page.locator('#captionProviderState')).to_have_text('Đã lưu cấu hình')
        expect(self.page.locator('#captionApiKey')).to_have_value('')
        self.page.reload()
        expect(self.page.locator('#captionModel')).to_have_value('custom-model')
        expect(self.page.locator('#captionApiKey')).to_have_value('')
        data=self.page.request.get(f'http://127.0.0.1:{self.server.server_port}/api/captions/provider').text()
        self.assertNotIn('fake-test-secret',data)
        self.page.locator('.caption-options-row summary').click()
        self.page.locator('#captionModel').fill('second-model')
        self.page.locator('#captionUseTranscript').uncheck()
        self.page.locator('#captionSelectAll').check()
        self.page.locator('#rewriteCaptions').click()
        expect(self.page.locator('#captionBatchFeedback')).to_contain_text('Đã viết lại 1/1')
        self.assertEqual(ai.call_args.kwargs,{'model':'second-model','api_key':'fake-test-secret'})
        self.assertEqual(self.errors,[])

    def test_library_compact_rows_have_two_real_thumbnails_and_clickable_records(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        root=Path(self.tmp.name)
        downloads=root/'downloads'; downloads.mkdir()
        (downloads/'original.mp4').write_bytes(self.video_bytes)
        original_route=patch.object(studio,'DOWNLOADS_DIR',str(downloads))
        original_route.start(); self.addCleanup(original_route.stop)
        settings=patch.dict(studio.app.config,SOCIAL_DOWNLOADS_DIR=downloads)
        settings.start(); self.addCleanup(settings.stop)
        db=patch.object(database,'DB_FILE',str(root/'layout-videos.json'))
        db.start(); self.addCleanup(db.stop)
        title='A very long caption with important video context. '*25
        database._save_data([{'id':'one','stt':1,'title':title,'status':'completed','video_filename':'original.mp4','output_filename':'ready.mp4'}])
        lookup=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        lookup.start(); self.addCleanup(lookup.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        expect(self.page.get_by_role('columnheader',name='Xem Trước',exact=True)).to_have_count(0)
        expect(self.page.get_by_role('columnheader',name='Video gốc',exact=True)).to_be_visible()
        expect(self.page.get_by_role('columnheader',name='Thành phẩm',exact=True)).to_be_visible()
        expect(self.page.locator('#videoTableBody').get_by_role('link',name='Chi tiết',exact=True)).to_have_count(0)
        link=self.page.locator('.library-title-link')
        expect(link).to_have_attribute('title',title)
        self.assertEqual(link.evaluate('el=>getComputedStyle(el).webkitLineClamp'),'2')
        self.assertLess(link.evaluate('el=>el.clientHeight'),60)
        for kind in ('original','output'):
            thumbnail=self.page.locator(f'[data-media-kind="{kind}"] img')
            expect(thumbnail).to_be_visible()
            self.page.wait_for_function('(kind)=>{const img=document.querySelector(`[data-media-kind="${kind}"] img`);return img.complete && img.naturalWidth>0}',arg=kind)
            self.page.locator(f'[data-media-kind="{kind}"]').click()
            expect(self.page.locator('#videoModal')).to_be_visible()
            expect(self.page.locator('#modalVideoPlayer')).to_have_attribute('src','/video/download/original.mp4' if kind=='original' else '/video/output/ready.mp4')
            self.page.wait_for_function('document.getElementById("modalVideoPlayer").readyState >= 2')
            expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/')
            self.page.evaluate('closeModal()')
        self.page.locator('[data-caption-video]').check()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('#videoTableBody tr td').nth(1).click()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/videos/one')
        expect(self.page.locator('#detailTitle')).to_have_text(title)
        self.assertEqual(self.errors,[])

    def test_row_caption_button_runs_immediately_without_changing_selection(self):
        from playwright.sync_api import expect
        import database
        self.lookup.stop(); self.single.stop()
        db=patch.object(database,'DB_FILE',str(Path(self.tmp.name)/'row-caption-videos.json'))
        db.start(); self.addCleanup(db.stop)
        database._save_data([{'id':'one','stt':1,'title':'Original','caption':'Previously written','status':'completed','output_filename':'ready.mp4'}])
        lookup=patch.object(studio,'get_all_videos',side_effect=database.get_all_videos)
        lookup.start(); self.addCleanup(lookup.stop)
        provider=patch('services.captions.routes.rewrite_captions',return_value={'one':{'caption':'Row rewritten'}})
        ai=provider.start(); self.addCleanup(provider.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('#captionUseTranscript').uncheck()
        expect(self.page.locator('#captionRewriteMode')).to_have_value('unwritten')
        expect(self.page.locator('#rewriteCaptions')).to_be_disabled()
        pending=[]
        self.page.route('**/api/captions/rewrite',lambda route:pending.append(route))
        self.page.locator('[data-caption-rewrite="one"]').click()
        expect(self.page.locator('[data-caption-rewrite="one"]')).to_have_text('Đang viết…')
        expect(self.page.locator('[data-caption-rewrite="one"]')).to_be_disabled()
        self.page.evaluate('fetchVideos()')
        expect(self.page.locator('[data-caption-rewrite="one"]')).to_have_attribute('aria-busy','true')
        pending[0].continue_()
        expect(self.page.locator('.library-title-link')).to_have_text('Row rewritten')
        self.assertEqual(ai.call_count,1)
        expect(self.page.locator('#captionSelectedCount')).to_have_text('0 đã chọn')
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/')
        self.assertEqual(database.get_video('one')['caption'],'Row rewritten')
        self.assertEqual(self.errors,[])

    def test_library_row_schedule_dialog_creates_batch_and_retries_same_key(self):
        from playwright.sync_api import expect
        from datetime import datetime,timedelta
        lookup=patch.object(studio,'get_all_videos',return_value=[{'id':'one','stt':1,'title':self.caption,'status':'completed','output_filename':'ready.mp4'}])
        lookup.start(); self.addCleanup(lookup.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.locator('[data-schedule-video="one"]').click()
        expect(self.page.locator('#libraryScheduleDialog')).to_be_visible()
        expect(self.page.locator('#libraryScheduleCaption')).to_have_text(self.caption)
        self.page.locator('#libraryScheduleAt').fill((datetime.now()+timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
        self.page.locator('#libraryScheduleAudience').select_option('no')
        self.page.locator('#libraryScheduleConfirm').check()
        self.page.locator('#libraryScheduleAt').fill('2020-01-01T08:00')
        self.page.locator('#libraryScheduleSubmit').click()
        expect(self.page.locator('#libraryScheduleMessage')).to_contain_text('Chọn thời gian từ hiện tại')
        self.assertEqual(self.store.list_batches(),[])
        self.page.locator('#libraryScheduleAt').fill((datetime.now()+timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
        keys=[]
        def lost_response(route):
            keys.append(route.request.post_data_json['request_key'])
            response=route.fetch()
            if len(keys)==1:
                route.fulfill(status=503,content_type='application/json',body='{"message":"Lost response fixture"}')
            else:
                route.fulfill(response=response)
        self.page.route('**/api/social/batches',lost_response)
        self.page.locator('#libraryScheduleSubmit').click()
        expect(self.page.locator('#libraryScheduleMessage')).to_contain_text('Lost response fixture')
        self.assertEqual(len(self.store.list_batches()),1)
        self.page.locator('#libraryScheduleSubmit').click()
        expect(self.page.locator('#libraryScheduleDialog')).not_to_be_visible()
        self.assertEqual(len(keys),2)
        self.assertEqual(keys[0],keys[1])
        self.assertEqual(len(self.store.list_batches()),1)
        self.assertEqual(len(self.store.list_batches()[0]['tasks']),5)
        self.page.locator('[data-schedule-video="one"]').click()
        expect(self.page.locator('#libraryScheduleDialog')).to_be_visible()
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#libraryScheduleDialog')).not_to_be_visible()
        expect(self.page).to_have_url(f'http://127.0.0.1:{self.server.server_port}/')
        self.assertEqual(self.errors,[])

    def test_video_player_stays_between_header_and_footer_on_small_screens(self):
        from playwright.sync_api import expect
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','lavfi','-i','color=c=white:s=720x1280:r=5','-t','0.4','-c:v','libx264','-pix_fmt','yuv420p',str(Path(self.tmp.name)/'outputs'/'ready.mp4')],check=True,capture_output=True)
        self.page.route('**/video/download/ready.mp4',lambda route:route.fulfill(status=200,content_type='video/mp4',body=(Path(self.tmp.name)/'outputs'/'ready.mp4').read_bytes()))
        lookup=patch.object(studio,'get_all_videos',return_value=[])
        lookup.start(); self.addCleanup(lookup.stop)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        title='Caption dài cần hiển thị gọn mà không đẩy video tràn ra ngoài. '*5
        for width,height,ratio,kind in [(575,886,'9:16','output'),(390,700,'9:16','output'),(1000,500,'16:9','output'),(575,886,'9:16','original')]:
            self.page.set_viewport_size({'width':width,'height':height})
            if kind=='original':
                self.page.evaluate('title=>playOriginal("ready.mp4",title)',title)
            else:
                self.page.evaluate('([title,ratio])=>playOutput("ready.mp4",title,ratio,"cozy","stickman")',[title,ratio])
            expect(self.page.locator('#videoModal')).to_be_visible()
            self.page.wait_for_function('document.getElementById("modalVideoPlayer").readyState >= 2')
            boxes=self.page.evaluate('''() => {
                const box=selector=>{const r=document.querySelector(selector).getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right}};
                return {dialog:box('#modalDialog'),header:box('#modalDialog > div:first-child'),video:box('#modalVideoPlayer'),footer:box('#modalDialog > div:last-child')};
            }''')
            self.assertGreaterEqual(boxes['video']['top'],boxes['header']['bottom']-1)
            self.assertLessEqual(boxes['video']['bottom'],boxes['footer']['top']+1)
            self.assertGreaterEqual(boxes['dialog']['top'],0)
            self.assertLessEqual(boxes['dialog']['bottom'],height)
            self.assertGreaterEqual(boxes['video']['left'],boxes['dialog']['left'])
            self.assertLessEqual(boxes['video']['right'],boxes['dialog']['right'])
            expect(self.page.locator('#modalDownloadBtn')).to_be_visible()
            self.page.locator('#modalDialog button').first.click()
            expect(self.page.locator('#videoModal')).not_to_be_visible()
        self.assertEqual(self.errors,[])



if __name__ == '__main__':
    unittest.main()
