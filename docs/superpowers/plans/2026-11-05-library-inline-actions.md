# Run row actions within library

User: row caption rewrite and scheduling should operate directly in library like render-again.

Design: row rewrite immediately submits that record (explicit rewrite ignores bulk unwritten filter), using current dialogue/provider/tag settings and direct-save pipeline. Disable/relabel its button across table polling; leave bulk selection unchanged. Bulk rewrite remains. Scheduling opens native accessible dialog on library with selected caption preview, datetime, YouTube audience and existing confirmation for all five platforms. Create through current API; no real posts during validation. Preserve request payload/key on uncertain response for idempotent retry. No navigation from row action buttons. API status/errors shown in place.

- [x] Tests for row rewrite bypassing filter/selection, progress state through polling and immediate table update.
- [x] Inline schedule dialog with current record/validation/idempotency and no navigation.
- [x] Full UI regression suite and backend checks, live page verification after safe reload if needed.

Verification: 137 tests pass. New row test holds the request, refreshes the table and verifies progress/disabled state, then confirms direct save and unchanged selection. Schedule test rejects past dates, simulates a lost response after saving and retries with same request key, producing exactly one five-task batch; Escape closes the dialog. Live desktop/mobile dialog inspected without submitting; no real provider/STT or posting calls. Changes are frontend/template-only and load on refresh, with no server restart needed.
