# Platform publishing controls

User request: enable/disable publication per account; library publication column shows successful destinations only; publication on one destination makes the video used and prevents new publication batches.

- [x] Add persistent per-account publishing toggle (default enabled for compatibility), strict API validation, enabled-only task creation and daily eligibility. Disabling cancels queued tasks, preserves active and uncertain tasks, and blocks retries while disabled. Existing login sessions remain available.
- [x] Reject new batches for any video already published on any platform. Preserve idempotent recovery of existing requests. Permit the remaining destinations in the same batch to complete; prevent older duplicate batches from starting after another batch has published that record. Daily selection continues excluding reserved/scheduled videos to prevent concurrent duplicates.
- [x] Add account controls, display actual enabled destinations in schedule confirmations, show only successful platforms in the library, and disable scheduling an already published video. Keep full diagnostic history in Results.
- [x] Verify migration, disabled/zero-target scheduling, idempotency across preference changes, publication protection, daily selection, routes, and real browser UI. Restart the worker only when idle, retaining historical and uncertain publication results. Do not publish live posts during validation.

Validation results and any scope decisions will be recorded below.

User confirmed that remaining destinations within the same batch continue after the first success; only new batches are blocked. Defaults preserve the existing enabled destinations, rather than changing the user's account choices automatically.

Focused final run: 79 tests passed across social store/routes/daily, caption history and six real browser UI cases. Includes toggling accounts and reloading, selected-destination scheduling, successful-only library badges, disabled rescheduling, and recovery after publication plus a toggle. Logs: `/tmp/platform-controls-focused-final.log`.

Full-suite run: 219 tests, 6 caption UI errors and 1 obsolete history-fixture failure. The fixture was updated to create its legacy duplicate before publication and limit it to Facebook, and its final focused rerun passed. The 6 unresolved errors are the existing 30-second timeout on the disabled rewrite button in `test_publishing_ui.PublishingUITests`:

- `test_ai_caption_preview_requires_explicit_save_and_keeps_original_title`
- `test_caption_later_batch_network_error_keeps_earlier_drafts`
- `test_caption_select_all_205_videos_sends_three_batches_and_restores_marks`
- `test_caption_toolbar_scope_filters_selected_videos_and_all_mode_rewrites_them`
- `test_library_rewrite_opens_individual_detail_for_review_and_save`
- `test_manual_hashtags_settings_persist_and_rewrite_auto_saves_changes`

Full log: `/tmp/platform-controls-full-tests.log`. Subsequent focused run also includes the new canonical-destination and pending-request regressions. JavaScript syntax and `git diff --check` passed.

Independent code review found two recovery edge cases: destination ordering/null validation, and the UI losing the pending request when publication removes its video from choices. Both received failing regression tests followed by fixes and passing reruns.

Restarted the idle app and worker after checking there were no pending/active publishing tasks or rendering videos. Verified localhost status endpoint, online worker, account migration retaining all five prior enabled settings, and served account-control source. No live posts were created during validation.
