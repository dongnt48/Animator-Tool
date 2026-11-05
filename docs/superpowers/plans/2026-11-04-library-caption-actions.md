# Caption actions in the video library

User requirement: rewrite captions from the existing video creation/library page, indicate rewritten videos, and add hashtags automatically. Keep existing colors, width, all-video selection, 100-item AI batches and 300-character dialogue input.

Implementation: share editor/results partials between legacy caption page and library; use checkboxes in the existing library table, not a duplicate video list. Delegate selection events so periodic table refresh keeps selections. Row action selects that video and focuses the inline toolbar. Persisted drafts and explicit caption save stay intact. Remove separate caption sidebar entry; legacy URL remains supported. AI prompt adds 3–5 relevant nonduplicated hashtags.

- [x] Add UI regression for selecting in library, rewrite/save without navigating, refresh persistence; assert automatic hashtag prompt.
- [x] Extract shared editor/results partials and reuse caption controller with library table selection.
- [x] Update row action/status, navigation and provider prompt.
- [x] Run full suite, review, reload idle server and verify root page.

Verification: 106 tests passed, including local Playwright interaction in the root library, selection persistence during polling, explicit save, and badges after reload. Mobile/desktop library screenshots inspected. Review found no important regressions. No real provider, speech recognition or posting calls were made.
