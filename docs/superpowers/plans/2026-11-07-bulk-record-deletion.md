# Bulk record deletion

User request: select multiple library records and delete them together.

- [x] Reuse existing row checkboxes and select-all state. Add a library-only delete-selected button independent of caption API configuration. Keep caption operations mutually exclusive with deletion.
- [x] Confirm the count and existing media deletion behavior once. Capture selected IDs, call the existing idempotent DELETE endpoint sequentially, show progress and per-record failures, retain failed selections and provide retry for hidden records with cleanup pending. Continue after individual failures.
- [x] Preserve existing soft-deletion identity history, busy-record rejection, shared-file protection and account/schedule state. Do not delete the user's actual library as part of feature validation.
- [x] Verify real browser selection, cancellation, partial success, retry, select-all, network failure and cleanup-pending handling using temporary records/media; run existing deletion tests. Verify the live app serves the button.

Validation: four new browser tests passed, fifteen existing deletion tests passed, and three existing caption-row/library/mobile regression tests passed (22 total). JavaScript syntax checks and `git diff --check` passed. Logs: `/tmp/bulk-delete-ui-green.log`, `/tmp/bulk-existing-deletion-tests.log`, `/tmp/bulk-delete-caption-regression.log`.

Independent read-only review found no actionable issue. Live read-only browser inspection confirmed the button is visible and disabled with no selection. No server restart was required: changes are JavaScript and auto-reloaded templates, using the existing deletion endpoint. No user records were deleted during validation; end-to-end tests used temporary data and media.
