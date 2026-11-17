"""Facebook receipts must belong to the active actor and actual posting interval."""
import tempfile
import time
import unittest
from pathlib import Path
from services.social.store import Store


def story(actor='page-owner', caption='Caption\n#tag', posted=1000, video='12345'):
    return {'__typename':'Story','post_id':video,'creation_time':posted,
            'permalink_url':f'https://www.facebook.com/reel/{video}/',
            'actors':[{'id':actor}], 'attachments':[{'styles':{'attachment':{'media':{'__typename':'Video','id':video,'owner':{'id':actor}}}}}], 'comet_sections':{'content':{'story':{'message':{'text':caption}}}}}


class FacebookReceiptTests(unittest.TestCase):
    def test_graphql_story_matches_actor_full_caption_time_and_reel_link(self):
        from services.social.facebook_verification import facebook_story_receipts, find_facebook_receipt
        payload={'data':{'node':story()}}
        evidence=facebook_story_receipts(payload,'page-owner')
        self.assertEqual(find_facebook_receipt(evidence,'Caption #tag',995,1010),'https://www.facebook.com/reel/12345')
        self.assertEqual(facebook_story_receipts(payload,'different-page'),[])
        self.assertIsNone(find_facebook_receipt(evidence,'Caption',995,1010))
        self.assertIsNone(find_facebook_receipt(evidence,'Caption #tag',1005,1010))
        wrong=story();wrong['permalink_url']='https://evil.test/reel/12345'
        self.assertEqual(facebook_story_receipts(wrong,'page-owner'),[])
        duplicate=evidence+facebook_story_receipts({'data':{'node':story(video='67890')}},'page-owner')
        self.assertIsNone(find_facebook_receipt(duplicate,'Caption #tag',995,1010))

    def test_missing_fields_and_nested_unrelated_story_cannot_supply_evidence(self):
        from services.social.facebook_verification import facebook_story_receipts
        for field in ('creation_time','post_id','actors','permalink_url','attachments'):
            bad=story();bad.pop(field)
            self.assertEqual(facebook_story_receipts(bad,'page-owner'),[])
        bad=story(actor='other-person');bad['attached_story']=story(actor='page-owner',posted=900)
        evidence=facebook_story_receipts(bad,'page-owner')
        self.assertEqual(len(evidence),1)
        self.assertEqual(evidence[0]['posted_at'],900)

    def test_shared_reel_owned_by_someone_else_is_not_an_upload_receipt(self):
        from services.social.facebook_verification import facebook_story_receipts
        payload=story()
        payload['attachments']=[{'styles':{'attachment':{'media':{'__typename':'Video','id':'12345','owner':{'id':'another-person'}}}}}]
        self.assertEqual(facebook_story_receipts(payload,'page-owner'),[])

    def test_legacy_actor_requires_persisted_cookie_that_predates_attempt(self):
        import sqlite3
        from services.social.facebook_verification import facebook_actor_history
        from services.social.profiles import profile_path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cookies=profile_path(root,'facebook')/'Default'/'Cookies';cookies.parent.mkdir(parents=True)
            with sqlite3.connect(cookies) as db:
                db.execute('CREATE TABLE cookies(host_key TEXT,name TEXT,path TEXT,creation_utc INTEGER,last_update_utc INTEGER,value TEXT)')
                epoch=11644473600
                db.execute('INSERT INTO cookies VALUES (?,?,?,?,?,?)',('.facebook.com','i_user','/',(epoch+900)*1000000,(epoch+950)*1000000,'page-owner'))
            actual=[{'name':'i_user','value':'page-owner','domain':'.facebook.com','path':'/'}]
            self.assertEqual(facebook_actor_history(root,actual),('page-owner',950))
            with sqlite3.connect(cookies) as db:db.execute("UPDATE cookies SET value='different-page'")
            self.assertIsNone(facebook_actor_history(root,actual))
            with sqlite3.connect(cookies) as db:db.execute("UPDATE cookies SET value=''")
            self.assertIsNone(facebook_actor_history(root,actual))
            self.assertIsNone(facebook_actor_history(root,[{'name':'c_user','value':'personal','domain':'.facebook.com','path':'/'}]))

    def test_background_verification_handles_facebook_without_touching_tiktok(self):
        from services.social.verification import reconcile_pending
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=Store(root/'social.sqlite3');media=root/'test.mp4';media.write_bytes(b'video');now=time.time()
            owner=store.begin_login('facebook');store.complete_login('facebook',owner,'account-owner')
            store.create_batch('video',str(media),'Caption',now,False,'request',platforms=['facebook'])
            task=store.claim_next('worker',now=now);store.mark_submitting(task['id'],'worker',actor_identity='page-owner');store.finish(task['id'],'worker','needs_review')
            with store.transaction() as db:
                self.assertEqual(db.execute('SELECT actor_identity FROM tasks WHERE id=?',(task['id'],)).fetchone()[0],'page-owner')
            before=next(a for a in store.accounts() if a['platform']=='tiktok')
            found=reconcile_pending(store,root,platform='facebook',collector=lambda root,identity,tasks:{tasks[0]['id']:'https://www.facebook.com/reel/12345'})
            self.assertEqual(found,1)
            self.assertEqual(store.task_state(task['id']),'published')
            self.assertEqual(before,next(a for a in store.accounts() if a['platform']=='tiktok'))
            account=next(a for a in store.accounts() if a['platform']=='facebook')
            self.assertEqual(account['identity'],'account-owner');self.assertIsNone(account['lease_owner'])

if __name__=='__main__':unittest.main()
