# Manual TikTok channel verification

User selected: when automated channel discovery fails, open official Chrome, let the user complete TikTok verification manually, then continue discovering videos and the existing download/render workflow.

- [x] Add a headed Chrome channel scanner with a ten-minute bounded wait, progress messages, explicit close/timeout/private-channel errors, exact channel URL filtering, deduplication, scrolling and end-of-list detection. Never interact with CAPTCHA controls.
- [x] Reserve the existing TikTok profile without changing account login state, identity or publishing preferences; release its lease after browser closure on success, cancellation or failure.
- [x] Use the scanner only after both existing discovery paths fail; preserve duplicate detection and integrate progress into both download-only and download/render records. Bound the extractor subprocess wait.
- [x] Test using local Playwright pages, temporary SQLite profiles and mocked external transports. Verify the app restart while idle. No real posting or CAPTCHA automation during validation.

Final focused run: 49 tests passed (`test_channel_browser`, `test_downloader_runtime`, `test_video_deletion`, `test_animation`), including visible and hidden iframe CAPTCHA cases, manual verification completion, scrolling, duplicates, closed browser, profile conflicts and lease cleanup. Log: `/tmp/manual-channel-focused-final.log`.

Full-suite run: 237 tests, 231 passed, six existing caption UI timeouts on the disabled rewrite button; log `/tmp/manual-channel-full-tests.log`. The later iframe regressions and fix were verified in the final focused run. The six unresolved `test_publishing_ui.PublishingUITests` cases are:

- `test_ai_caption_preview_requires_explicit_save_and_keeps_original_title`
- `test_caption_later_batch_network_error_keeps_earlier_drafts`
- `test_caption_select_all_205_videos_sends_three_batches_and_restores_marks`
- `test_caption_toolbar_scope_filters_selected_videos_and_all_mode_rewrites_them`
- `test_library_rewrite_opens_individual_detail_for_review_and_save`
- `test_manual_hashtags_settings_persist_and_rewrite_auto_saves_changes`

Independent review identified child-frame image challenges missing from the first implementation. Added failing iframe regression, inspected each visible frame and its ancestors, and reran the focused suite successfully. Hidden or detached verification frames do not block normal discovery.

Known minor limitation: if browser discovery succeeds but every individual media download fails, the existing app fallback error still describes channel scanning failure; per-video errors are logged. This diagnostic wording was not expanded in this change.

The app was restarted only after confirming no video was processing. Existing publisher worker and saved accounts were retained. Verified localhost status, online publisher worker and served updated UI instructions. Actual CAPTCHA completion requires the user's manual interaction on their next channel request; validation did not solve CAPTCHA, publish a post, or populate the user's library with test videos.
