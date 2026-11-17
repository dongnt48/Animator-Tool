"""Exercise actual Playwright on local DOM fixtures, without accounts or real posts."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from services.social.browser import UploadFlow, BrowserStepError


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements and Playwright Chromium for browser tests')
class BrowserFlowTests(unittest.TestCase):
    def test_tiktok_own_posts_redirect_confirms_uploaded_caption_and_time(self):
        import time
        from urllib.parse import urlsplit
        now = int(time.time())
        def route(request):
            path = urlsplit(request.request.url).path
            if path == '/tiktokstudio/upload':
                request.fulfill(status=200, content_type='text/html', body='''<div role="textbox" contenteditable="true">Caption #tag</div><button onclick="location.href='/tiktokstudio/content'">Post</button>''')
            elif path == '/tiktokstudio/content':
                request.fulfill(status=200, content_type='text/html', body='''<a href="/@owner/video/12345">Own post</a><script>fetch('/tiktok/creator/manage/item_list/v1/')</script>''')
            else:
                request.fulfill(status=200, content_type='application/json', body=json.dumps({'status_code':0, 'item_list':[{'item_id':'12345','desc':'Caption #tag','post_time':str(now),'status':102}]}))
        self.page.route('https://www.tiktok.com/**', route)
        self.page.goto('https://www.tiktok.com/tiktokstudio/upload')
        flow = UploadFlow(self.page, timeout=2)
        flow.expected_tiktok_caption = 'Caption #tag'
        receipt = flow.submit('tiktok', '^Post$', lambda: None)
        self.assertEqual(receipt.url, 'https://www.tiktok.com/@owner/video/12345')

    def test_tiktok_closes_joyride_before_publication_checkpoint(self):
        self.page.set_content('''<button onclick="window.posted=true;document.getElementById('receipt').hidden=false">Post</button>
            <div id="receipt" role="status" hidden>Your video has been published <a href="https://www.tiktok.com/@someone/video/12345">View</a></div>
            <div id="react-joyride-portal"><div role="presentation" data-test-id="overlay" class="react-joyride__overlay" style="position:fixed;inset:0;background:#0008;z-index:100"></div>
            <div class="react-joyride__tooltip" style="position:fixed;top:100px;left:100px;z-index:101"><p>Welcome to TikTok Studio</p><button data-action="close" onclick="document.getElementById('react-joyride-portal').remove()">Close</button></div></div>''')
        flow = UploadFlow(self.page, timeout=.5)
        checkpoints = []
        def checkpoint():
            self.assertEqual(self.page.locator('#react-joyride-portal').count(), 0)
            self.assertIsNone(self.page.evaluate('window.posted'))
            checkpoints.append('ready')
        receipt = flow.submit('tiktok', '^Post$', checkpoint)
        self.assertEqual(checkpoints, ['ready'])
        self.assertTrue(self.page.evaluate('window.posted'))
        self.assertTrue(receipt.url.endswith('/12345'))

    def test_tiktok_phone_preview_got_it_dismissed_before_publication(self):
        self.page.set_content('''<button onclick="document.getElementById('receipt').hidden=false">Post</button>
            <div id="receipt" role="status" hidden>Your video has been published <a href="https://www.tiktok.com/@someone/video/12345">View</a></div>
            <div id="react-joyride-portal"><div data-test-id="overlay" class="react-joyride__overlay" style="position:fixed;inset:0;z-index:100"></div>
            <div data-test-id="tooltip" style="position:fixed;top:20px;left:20px;z-index:101">
            <h3>Preview your video on your phone</h3><p>Now you can view your video as it will appear on TikTok.</p>
            <button data-action="next" onclick="document.getElementById('react-joyride-portal').remove()">Got it</button></div></div>''')
        checkpoints = []
        receipt = UploadFlow(self.page, timeout=.5).submit('tiktok', '^Post$', lambda: checkpoints.append('ready'))
        self.assertEqual(checkpoints, ['ready'])
        self.assertTrue(receipt.url.endswith('/12345'))
        self.assertEqual(self.page.locator('#react-joyride-portal').count(), 0)

    def test_phone_preview_tip_cannot_dismiss_verification_with_got_it(self):
        self.page.set_content('''<div id="react-joyride-portal"><div data-test-id="tooltip">
            <h3>Preview your video on your phone</h3><p>Verify identity</p>
            <button onclick="window.closedVerification=true">Got it</button></div></div>''')
        UploadFlow(self.page).dismiss_tiktok_onboarding()
        self.assertIsNone(self.page.evaluate('window.closedVerification'))

    def test_tiktok_orphan_tour_overlay_stops_before_publication_checkpoint(self):
        self.page.set_content('''<button onclick="window.posted=true">Post</button>
            <div id="react-joyride-portal"><div data-test-id="overlay" class="react-joyride__overlay" style="position:fixed;inset:0;background:#0008;z-index:100"></div></div>''')
        self.page.set_default_timeout(200)
        flow = UploadFlow(self.page, timeout=.2)
        checkpoints = []
        with self.assertRaises(BrowserStepError):
            flow.submit('tiktok', '^Post$', lambda: checkpoints.append('submitting'))
        self.assertEqual(checkpoints, [])
        self.assertIsNone(self.page.evaluate('window.posted'))

    def test_joyride_helper_does_not_close_identity_verification(self):
        self.page.set_content('''<div id="react-joyride-portal"><div class="react-joyride__tooltip"><h2>Verify identity</h2><input type="text"><button data-action="close" onclick="window.closedVerification=true">Close</button></div></div>''')
        UploadFlow(self.page).dismiss_tiktok_onboarding()
        self.assertIsNone(self.page.evaluate('window.closedVerification'))

    def test_tiktok_onboarding_text_cannot_cancel_unrelated_verification(self):
        self.page.set_content('''<p>Turn on automatic content checks?</p>
            <div role="dialog"><h2>Verify identity</h2><input type="text"><button onclick="window.cancelledVerification=true">Cancel</button></div>''')
        UploadFlow(self.page).dismiss_tiktok_onboarding()
        self.assertIsNone(self.page.evaluate('window.cancelledVerification'))

    def test_tiktok_closes_only_known_onboarding_without_enabling_checks(self):
        self.page.set_content('''<input type="file"><div role="textbox" contenteditable="true">filename.mp4</div>
            <section><h2>Turn on automatic content checks?</h2><button onclick="this.parentNode.remove()">Cancel</button><button onclick="window.enabledChecks=true">Turn on</button></section>
            <section><h3>New editing features added</h3><button onclick="this.parentNode.remove()">Got it</button></section><button>Post</button>''')
        flow = UploadFlow(self.page, timeout=1)
        flow.prepare('tiktok', str(self.media), 'Caption đúng', False)
        self.assertEqual(self.page.get_by_role('textbox').inner_text(), 'Caption đúng')
        self.assertEqual(self.page.get_by_text('Turn on automatic content checks?', exact=True).count(), 0)
        self.assertEqual(self.page.get_by_text('New editing features added', exact=True).count(), 0)
        self.assertIsNone(self.page.evaluate('window.enabledChecks'))

    def test_tiktok_rechecks_caption_before_publish_after_filename_autofill(self):
        self.page.set_content('''<input type="file"><div role="textbox" contenteditable="true"></div>
            <button onclick="window.postedCaption=document.querySelector('[role=textbox]').innerText;const receipt=document.createElement('div');receipt.setAttribute('role','status');receipt.innerHTML='Your video has been published <a href=https://www.tiktok.com/@someone/video/12345>View</a>';document.body.append(receipt)">Post</button>''')
        flow = UploadFlow(self.page, timeout=1)
        pattern = flow.prepare('tiktok', str(self.media), 'Caption đúng', False)
        self.page.get_by_role('textbox').fill('unexpected-filename.mp4 Caption đúng')
        receipt = flow.submit('tiktok', pattern, lambda: None)
        self.assertEqual(self.page.evaluate('window.postedCaption'), 'Caption đúng')
        self.assertTrue(receipt.url.endswith('/12345'))

    def test_youtube_vertical_video_uses_portrait_cover_and_horizontal_uses_landscape(self):
        from PIL import Image
        from services.social.cover_flow import CoverFlow
        for shape in ('portrait', 'landscape'):
            Image.new('RGB', (30,40), 'red').save(Path(self.tmp.name)/(shape+'.jpg'))
        for ratio, expected in [('9:16','portrait.jpg'), ('16:9','landscape.jpg')]:
            with self.subTest(ratio=ratio):
                self.page.set_content('''<div data-testid="cover-editor"><input type="file" accept="image/jpeg"
                    onchange="const i=document.createElement('img');const reader=new FileReader();reader.onload=()=>{i.src=reader.result;this.parentNode.append(i)};reader.readAsDataURL(this.files[0])"></div>''')
                flow = CoverFlow(self.page, {'mode':'upload', 'aspect_ratio':ratio,
                    'portrait_path':str(Path(self.tmp.name)/'portrait.jpg'),
                    'landscape_path':str(Path(self.tmp.name)/'landscape.jpg')})
                flow.apply('youtube')
                self.assertEqual(flow.state, 'applied')
                self.assertEqual(self.page.locator('input').evaluate('(e)=>e.files[0].name'), expected)

    def test_cover_upload_is_scoped_and_requires_new_preview(self):
        from PIL import Image
        from services.social.cover_flow import CoverFlow
        path = Path(self.tmp.name)/'cover.jpg'; Image.new('RGB', (30, 40), 'red').save(path)
        self.page.set_content('''<input id="video" type="file" accept="video/mp4">
            <div data-testid="cover-editor"><input id="cover" type="file" accept="image/jpeg" onchange="const i=document.createElement('img');const reader=new FileReader();reader.onload=()=>{i.src=reader.result;this.parentNode.append(i)};reader.readAsDataURL(this.files[0])"></div>''')
        flow = CoverFlow(self.page, {'mode': 'upload', 'portrait_path': str(path), 'landscape_path': str(path), 'aspect_ratio': '9:16'})
        flow.apply('instagram'); flow.finalize()
        self.assertEqual(flow.state, 'applied')
        self.assertEqual(self.page.locator('#video').evaluate('(e)=>e.files.length'), 0)
        self.assertEqual(self.page.locator('#cover').evaluate('(e)=>e.files[0].name'), 'cover.jpg')

    def test_tiktok_nonbutton_edit_cover_uploads_app_image_and_saves(self):
        from PIL import Image
        from services.social.cover_flow import CoverFlow
        path=Path(self.tmp.name)/'app-cover.jpg';Image.new('RGB',(30,40),'orange').save(path)
        self.page.set_content('''<input id="video" type="file" accept="video/mp4">
          <div class="cover-container"><img id="savedPreview"><div class="edit-container" onclick="document.getElementById('editor').hidden=false">Edit cover</div></div>
          <div id="editor" role="dialog" aria-modal="true" hidden>
            <div>Edit cover</div><button onclick="this.parentNode.hidden=true">Cancel</button>
            <button onclick="document.getElementById('savedPreview').src=document.getElementById('customPreview').src;window.coverSaved=true;this.parentNode.hidden=true">Save</button>
            <div role="button" aria-label="Upload cover image"><input id="coverInput" type="file" accept="image/jpeg, image/png, image/jpg"
              onchange="const reader=new FileReader();reader.onload=()=>document.getElementById('customPreview').src=reader.result;reader.readAsDataURL(this.files[0])"></div>
            <img id="customPreview">
          </div><button onclick="window.posted=true">Post</button>''')
        flow=CoverFlow(self.page,{'mode':'frame','portrait_path':str(path)})
        flow.apply('tiktok');flow.finalize()
        self.assertEqual(flow.state,'applied')
        self.assertTrue(self.page.evaluate('window.coverSaved'))
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.locator('#coverInput').evaluate('e=>e.files[0].name'),path.name)
        self.assertEqual(self.page.locator('#video').evaluate('e=>e.files.length'),0)
        self.assertIsNone(self.page.evaluate('window.posted'))

    def test_tiktok_canvas_cover_stays_recognized_after_upload_input_is_removed(self):
        from PIL import Image, ImageDraw
        from services.social.cover_flow import CoverFlow
        path=Path(self.tmp.name)/'app-cover.jpg';picture=Image.new('RGB',(30,40),'orange');ImageDraw.Draw(picture).text((2,10),'APP',fill='black');picture.save(path)
        self.page.set_content('''<input id="video" type="file" accept="video/mp4">
          <div class="cover-container"><img id="savedPreview"><div onclick="document.getElementById('editor').hidden=false">Edit cover</div></div>
          <div id="editor" role="dialog" data-dialog-content="true" hidden><div>Edit cover</div>
            <button onclick="this.parentNode.hidden=true">Cancel</button>
            <button onclick="document.getElementById('savedPreview').src=document.getElementById('customPreview').toDataURL();this.parentNode.hidden=true;window.coverSaved=true">Save</button>
            <input id="coverInput" type="file" accept="image/jpeg" onchange="const reader=new FileReader();window.uploadedName=this.files[0].name;reader.onload=()=>{const image=new Image();image.onload=()=>{document.getElementById('customPreview').getContext('2d').drawImage(image,0,0);this.remove();};image.src=reader.result;};reader.readAsDataURL(this.files[0])">
            <canvas id="customPreview" width="30" height="40"></canvas>
          </div><button onclick="window.posted=true">Post</button>''')
        flow=CoverFlow(self.page,{'mode':'frame','portrait_path':str(path)})
        flow.apply('tiktok');flow.finalize()
        self.assertEqual(flow.state,'applied')
        self.assertTrue(self.page.evaluate('window.coverSaved'))
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.evaluate('window.uploadedName'),path.name)
        self.assertEqual(self.page.locator('#video').evaluate('e=>e.files.length'),0)
        self.assertIsNone(self.page.evaluate('window.posted'))

    def test_tiktok_waits_for_uploaded_image_to_render_on_new_canvas_before_save(self):
        from PIL import Image, ImageDraw
        from services.social.cover_flow import CoverFlow
        path=Path(self.tmp.name)/'app-cover.jpg';picture=Image.new('RGB',(30,40),'orange');ImageDraw.Draw(picture).text((2,10),'APP',fill='black');picture.save(path)
        self.page.set_content('''<div class="cover-container"><img id="savedPreview"><div onclick="document.getElementById('editor').hidden=false">Edit cover</div></div>
          <div id="editor" role="dialog" data-dialog-content="true" hidden><div>Edit cover</div><button onclick="this.parentNode.hidden=true">Cancel</button>
            <button onclick="window.savedBeforeImage=!window.imageReady;document.getElementById('savedPreview').src=document.getElementById('customPreview').toDataURL();this.parentNode.hidden=true">Save</button>
            <div id="previewHost"></div><input type="file" accept="image/jpeg" onchange="const canvas=document.createElement('canvas');canvas.id='customPreview';canvas.width=30;canvas.height=40;document.getElementById('previewHost').append(canvas);const reader=new FileReader();reader.onload=()=>{const image=new Image();image.onload=()=>setTimeout(()=>{canvas.getContext('2d').drawImage(image,0,0);window.imageReady=true;this.remove();},700);image.src=reader.result;};reader.readAsDataURL(this.files[0])">
          </div>''')
        flow=CoverFlow(self.page,{'mode':'frame','portrait_path':str(path)})
        flow.apply('tiktok');flow.finalize()
        self.assertEqual(flow.state,'applied')
        self.assertFalse(self.page.evaluate('window.savedBeforeImage'))

    def test_tiktok_supplied_cover_cannot_silently_use_an_automatic_thumbnail(self):
        from PIL import Image
        from services.social.cover_flow import CoverFlow
        path=Path(self.tmp.name)/'custom-cover.jpg';Image.new('RGB',(30,40),'orange').save(path)
        self.page.set_content('<input id="video" type="file" accept="video/mp4"><div data-testid="cover-editor"><input id="nativeFrame" type="range" min="0" max="100" value="0" style="width:380px"></div><button>Post</button>')
        flow=CoverFlow(self.page,{'mode':'frame','portrait_path':str(path),'duration':10,'timestamp':6})
        flow.apply('tiktok')
        with self.assertRaisesRegex(ValueError,'ảnh bìa'):
            flow.finalize()
        self.assertEqual(flow.state,'needs_review')
        self.assertEqual(self.page.locator('#nativeFrame').input_value(),'0')
        self.assertEqual(self.page.locator('#video').evaluate('e=>e.files.length'),0)

    def test_cover_frame_selector_reports_frame_instead_of_custom_image(self):
        from services.social.cover_flow import CoverFlow
        self.page.set_content('<div data-testid="cover-editor" style="width:400px"><input type="range" min="0" max="100" value="0" style="width:380px"></div>')
        flow = CoverFlow(self.page, {'mode': 'frame', 'timestamp': 6, 'duration': 10, 'portrait_path': 'unused.jpg'})
        flow.apply('facebook'); flow.finalize()
        self.assertEqual(flow.state, 'frame')
        self.assertIn('không được tải lên', flow.message)

    def test_missing_cover_controls_never_touch_video_input(self):
        from services.social.cover_flow import CoverFlow
        self.page.set_content('<input id="video" type="file" accept="video/mp4"><button>Post</button>')
        flow = CoverFlow(self.page, {'portrait_path': 'must-not-upload.jpg'})
        flow.apply('facebook'); flow.finalize()
        self.assertEqual(flow.state, 'automatic')
        self.assertEqual(self.page.locator('#video').evaluate('(e)=>e.files.length'), 0)

    def test_opening_existing_preview_does_not_verify_an_ignored_upload(self):
        from PIL import Image
        from services.social.cover_flow import CoverFlow
        path = Path(self.tmp.name)/'cover.jpg'; Image.new('RGB', (30,40), 'red').save(path)
        self.page.set_content('''<button onclick="document.querySelector('[data-testid]').hidden=false">Edit cover</button>
            <div data-testid="cover-editor" hidden><img width="20" height="20" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"><input type="file" accept="image/jpeg"></div>''')
        flow = CoverFlow(self.page, {'mode':'upload', 'portrait_path':str(path)})
        flow.apply('instagram'); flow.finalize()
        self.assertEqual(flow.state, 'needs_review')

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media = Path(self.tmp.name) / 'video.mp4'
        self.media.write_bytes(b'fixture upload')

    def test_all_five_adapters_preserve_caption_and_checkpoint_before_publish(self):
        receipts = {
            'facebook': 'https://www.facebook.com/reel/12345',
            'instagram': 'https://www.instagram.com/reel/ABC123/',
            'threads': 'https://www.threads.com/@someone/post/ABC123',
            'tiktok': 'https://www.tiktok.com/@someone/video/12345',
            'youtube': 'https://youtu.be/abcdefghijk',
        }
        caption = "Caption O'Brien <script>text only</script> #hashtag"
        for platform, url in receipts.items():
            with self.subTest(platform=platform):
                caption_field = ('<div id="description-textarea"><div id="textbox" contenteditable="true"></div></div>'
                                 '<div id="title-textarea"><div id="textbox" contenteditable="true"></div></div>'
                                 if platform == 'youtube' else '<div role="dialog"><div role="textbox" contenteditable="true"></div></div>')
                self.page.set_content('''<button>Create</button><button>Upload videos</button>
                    <input type="file"><button onclick="window.steps=(window.steps||0)+1">Next</button>
                    <input type="radio" name="VIDEO_MADE_FOR_KIDS_NOT_MFK"><input type="radio" name="PUBLIC">
                    ''' + caption_field + '''<button id="publish"></button>
                    <script>window.checkpoint=false; window.steps=0;
                    document.getElementById('publish').onclick=()=>{
                       if(!window.checkpoint) throw new Error('Missing checkpoint');
                       const msg=document.createElement('h2');msg.textContent='Your video has been published';
                       const a=document.createElement('a');a.href=''' + json.dumps(url) + ''';a.textContent='View';
                       const receipt=document.createElement('ytcp-video-share-dialog');receipt.setAttribute('role','dialog');
                       receipt.append(msg,a);document.body.append(receipt);
                    };</script>''')
                self.page.locator('#publish').evaluate('(e, name)=>e.textContent=name',
                                                       'Share' if platform in ('facebook', 'instagram') else 'Publish' if platform == 'youtube' else 'Post')
                if platform == 'facebook':
                    self.page.locator('#publish').evaluate('(e)=>e.hidden=true')
                    self.page.get_by_role('button', name='Next', exact=True).evaluate('''e=>e.onclick=function advance(){
                        window.steps=(window.steps||0)+1;
                        if(window.steps===2) document.getElementById('publish').hidden=false;
                        else {const replacement=document.createElement('button');replacement.textContent='Next';replacement.onclick=advance;this.replaceWith(replacement);}
                    }''')
                flow = UploadFlow(self.page, timeout=2)
                pattern = flow.prepare(platform, str(self.media), caption, False)
                observed = self.page.locator('#description-textarea #textbox' if platform == 'youtube' else '[role="textbox"]').inner_text()
                self.assertEqual(observed, caption)
                self.assertEqual(self.page.locator('input[type=file]').evaluate('(e)=>e.files[0].name'), 'video.mp4')
                expected_steps = 3 if platform == 'youtube' else 2 if platform in ('facebook', 'instagram') else 0
                self.assertEqual(self.page.evaluate('window.steps'), expected_steps)
                if platform == 'youtube':
                    # Studio exposes this upload's share link before the final Publish click.
                    self.page.evaluate('(url)=>{const a=document.createElement("a");a.href=url;a.textContent="Upload preview";document.body.append(a)}', url)
                receipt = flow.submit(platform, pattern, lambda: self.page.evaluate('window.checkpoint=true'))
                self.assertEqual(receipt.url, url)

    def test_click_without_success_and_permalink_is_ambiguous(self):
        self.page.set_content('<button>Post</button><a href="https://www.tiktok.com/@someone/video/12345">Old post</a>')
        flow = UploadFlow(self.page, timeout=0.1)
        with self.assertRaises(BrowserStepError):
            flow.submit('tiktok', '^Post$', lambda: None)

    def test_success_message_without_new_permalink_is_ambiguous(self):
        self.page.set_content('<button onclick="document.body.append(\'Your video has been published\')">Post</button>')
        with self.assertRaises(BrowserStepError):
            UploadFlow(self.page, timeout=0.1).submit('threads', '^Post$', lambda: None)

    def test_recommended_post_link_is_not_an_upload_receipt(self):
        self.page.set_content('''<input type="file"><div role="textbox" contenteditable="true"></div>
            <button onclick="const status=document.createElement('div');status.setAttribute('role','status');status.textContent='Your video has been published';document.body.append(status)">Post</button>''')
        flow = UploadFlow(self.page, timeout=0.1)
        pattern = flow.prepare('tiktok', str(self.media), 'caption', False)
        self.page.evaluate("const a=document.createElement('a');a.href='https://www.tiktok.com/@other/video/12345';a.textContent='Recommendation';document.body.append(a)")
        with self.assertRaises(BrowserStepError):
            flow.submit('tiktok', pattern, lambda: None)

    def test_facebook_confirms_own_page_story_after_composer_redirect(self):
        import time
        from urllib.parse import urlsplit
        from tests.test_facebook_verification import story
        self.page.context.add_cookies([{'name':'c_user','value':'personal-account','domain':'.facebook.com','path':'/'},
                                      {'name':'i_user','value':'page-owner','domain':'.facebook.com','path':'/'}])
        evidence=story(posted=int(time.time()))
        def route(request):
            path=urlsplit(request.request.url).path
            if path=='/reels/create/':
                request.fulfill(status=200,content_type='text/html',body='''<button onclick="location.href='/home.php'">Share</button>''')
            elif path=='/api/graphql/':
                request.fulfill(status=200,content_type='application/json',body='for (;;);'+json.dumps({'data':{'node':evidence}}))
            else:
                request.fulfill(status=200,content_type='text/html',body='''<script>fetch('/api/graphql/')</script>''')
        self.page.route('https://www.facebook.com/**',route)
        self.page.goto('https://www.facebook.com/reels/create/')
        flow=UploadFlow(self.page,timeout=2)
        flow.expected_facebook_caption='Caption #tag'
        receipt=flow.submit('facebook','^Share$',lambda:None)
        self.assertEqual(receipt.url,'https://www.facebook.com/reel/12345')

    def test_facebook_checks_own_profile_when_feed_has_no_post_receipt(self):
        import time
        from urllib.parse import urlsplit
        from tests.test_facebook_verification import story
        self.page.context.add_cookies([{'name':'c_user','value':'999','domain':'.facebook.com','path':'/'},
                                      {'name':'i_user','value':'123','domain':'.facebook.com','path':'/'}])
        evidence=story(actor='123',posted=int(time.time()))
        def route(request):
            path=urlsplit(request.request.url).path
            if path=='/reels/create/':
                body='''<button onclick="location.href='/home.php'">Share</button>'''
            elif path=='/profile.php':
                body='<script type="application/json">'+json.dumps({'data':{'node':evidence}})+'</script>'
            else:
                body='<p>News feed without upload receipt</p>'
            request.fulfill(status=200,content_type='text/html',body=body)
        self.page.route('https://www.facebook.com/**',route)
        self.page.goto('https://www.facebook.com/reels/create/')
        flow=UploadFlow(self.page,timeout=4);flow.expected_facebook_caption='Caption #tag'
        receipt=flow.submit('facebook','^Share$',lambda:None)
        self.assertEqual(receipt.url,'https://www.facebook.com/reel/12345')
        self.assertIn('profile.php?id=123',self.page.url)

    def test_facebook_cover_modal_upload_is_saved_before_next_step(self):
        from PIL import Image
        cover_path = Path(self.tmp.name)/'facebook-cover.jpg'
        Image.new('RGB', (30, 40), 'orange').save(cover_path)
        self.page.set_default_timeout(1200)
        self.page.set_content('''<input id="video" type="file" accept="video/mp4"><div role="textbox" contenteditable="true"></div>
          <div data-testid="cover-editor"><img id="preview"><button onclick="document.getElementById('modal').hidden=false">Edit cover</button></div>
          <div id="modal" hidden style="position:fixed;inset:0;background:white;z-index:99">
            <div role="dialog" aria-label="Chọn hình thu nhỏ"><h2>Chọn hình thu nhỏ</h2><button aria-label="Đóng" onclick="document.getElementById('modal').hidden=true">×</button></div>
            <img id="coverPreview"><input id="coverFile" type="file" accept=".png,.jpg,.jpeg" hidden
              onchange="const reader=new FileReader();reader.onload=()=>{document.getElementById('coverPreview').src=reader.result;setTimeout(()=>document.getElementById('saveCover').disabled=false,700);};reader.readAsDataURL(this.files[0])">
            <button onclick="document.getElementById('coverFile').click()">Tải lên</button>
            <button id="saveCover" disabled onclick="document.getElementById('preview').src=document.getElementById('coverPreview').src;this.parentNode.hidden=true;window.savedCover=true">Lưu</button>
          </div>
          <button id="next" onclick="this.hidden=true;document.getElementById('post').hidden=false;window.advanced=true">Tiếp</button>
          <button id="post" hidden onclick="window.posted=true">Đăng</button>''')
        flow = UploadFlow(self.page, timeout=5)
        flow.prepare('facebook', str(self.media), 'Caption nguyên vẹn', False,
                     cover={'mode':'upload','portrait_path':str(cover_path)})
        self.assertEqual(flow.cover_flow.state, 'applied')
        self.assertTrue(self.page.evaluate('window.savedCover'))
        self.assertTrue(self.page.evaluate('window.advanced'))
        self.assertIsNone(self.page.evaluate('window.posted'))
        self.assertFalse(self.page.locator('#modal').is_visible())
        self.assertEqual(self.page.locator('#video').evaluate('e=>e.files[0].name'), self.media.name)
        self.assertEqual(self.page.locator('#coverFile').evaluate('e=>e.files[0].name'), cover_path.name)
        self.assertEqual(self.page.locator('[role=textbox]').inner_text(), 'Caption nguyên vẹn')

    def test_cover_frame_waits_for_save_before_reporting_selected_frame(self):
        from services.social.cover_flow import CoverFlow
        self.page.set_content('''<div role="dialog" aria-label="Select thumbnail"><h2>Select thumbnail</h2>
          <input type="range" min="0" max="100" value="0" style="width:380px" onchange="setTimeout(()=>document.getElementById('save').disabled=false,700)">
          <button id="save" disabled onclick="window.savedFrame=true;this.parentNode.hidden=true">Save</button>
          <button onclick="window.cancelledFrame=true;this.parentNode.hidden=true">Close</button></div>''')
        flow=CoverFlow(self.page,{'mode':'frame','timestamp':6,'duration':10,'portrait_path':'unused.jpg'})
        flow.apply('facebook')
        self.assertEqual(flow.state,'frame')
        self.assertTrue(self.page.evaluate('window.savedFrame'))
        self.assertIsNone(self.page.evaluate('window.cancelledFrame'))

    def test_facebook_disabled_cover_save_is_closed_without_clicking_composer(self):
        from PIL import Image
        cover_path = Path(self.tmp.name)/'facebook-cover.jpg'
        Image.new('RGB', (30, 40), 'orange').save(cover_path)
        self.page.set_default_timeout(1200)
        self.page.set_content('''<input type="file"><div role="textbox" contenteditable="true"></div>
          <button onclick="document.getElementById('modal').hidden=false">Edit cover</button>
          <div role="dialog" id="modal" hidden style="position:fixed;inset:0;background:white;z-index:99"><h2>Chọn hình thu nhỏ</h2>
            <button aria-label="Đóng" onclick="this.parentNode.hidden=true">×</button><button disabled>Lưu</button></div>
          <button onclick="this.hidden=true;document.getElementById('post').hidden=false">Tiếp</button>
          <button id="post" hidden onclick="window.posted=true">Đăng</button>''')
        flow = UploadFlow(self.page, timeout=4)
        flow.prepare('facebook', str(self.media), 'Caption', False,cover={'mode':'upload','portrait_path':str(cover_path)})
        self.assertEqual(flow.cover_flow.state, 'automatic')
        self.assertFalse(self.page.locator('#modal').is_visible())
        self.assertIsNone(self.page.evaluate('window.posted'))

    def test_facebook_one_next_step_fills_caption_before_settings(self):
        self.page.set_content('''<input type="file"><div id="stage"><textarea aria-label="Mô tả thước phim"></textarea>
          <button onclick="window.savedCaption=document.querySelector('textarea').value; document.getElementById('stage').innerHTML='<h2>Cài đặt</h2><button onclick=window.didPublish=true>Đăng</button>'">Tiếp</button></div>''')
        caption = "Caption O'Brien #reels"
        pattern = UploadFlow(self.page, timeout=0.5).prepare('facebook', str(self.media), caption, False)
        self.assertEqual(self.page.evaluate('window.savedCaption'), caption)
        self.assertIsNone(self.page.evaluate('window.didPublish'))
        self.assertTrue(__import__('re').fullmatch(pattern, 'Đăng', __import__('re').I))

    def test_facebook_caption_can_appear_between_two_next_steps(self):
        self.page.set_content('''<input type="file"><div id="stage"><button id="first">Next</button></div>
          <script>document.getElementById('first').onclick=()=>{
            const stage=document.getElementById('stage');
            stage.innerHTML='<div role="textbox" contenteditable="true"></div><button id="second">Tiếp theo</button>';
            document.getElementById('second').onclick=()=>{
              window.savedCaption=document.querySelector('[role=textbox]').innerText;
              stage.innerHTML='<h2>Cài đặt</h2><button>Đăng</button>';
            };
          };</script>''')
        UploadFlow(self.page, timeout=0.5).prepare('facebook', str(self.media), 'existing caption', False)
        self.assertEqual(self.page.evaluate('window.savedCaption'), 'existing caption')

    def test_facebook_does_not_publish_when_caption_step_was_not_found(self):
        self.page.set_content('<input type="file"><button onclick="window.didPublish=true">Đăng</button>')
        with self.assertRaisesRegex(BrowserStepError, 'caption'):
            UploadFlow(self.page, timeout=0.2).prepare('facebook', str(self.media), 'must not disappear', False)
        self.assertIsNone(self.page.evaluate('window.didPublish'))


if __name__ == '__main__':
    unittest.main()
