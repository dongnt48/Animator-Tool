"""Exercise actual Playwright on local DOM fixtures, without accounts or real posts."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from services.social.browser import UploadFlow, BrowserStepError


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements and Playwright Chromium for browser tests')
class BrowserFlowTests(unittest.TestCase):
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
