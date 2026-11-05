# Recurring daily publishing

The user replaces per-video scheduling with a daily set of hours. At each selected time, automatically take one rendered video and its existing caption and distribute it to all five platforms using the existing Playwright worker. No per-video scheduling is required.

## Decisions
- Primary UI: daily times, fixed IANA timezone (default Asia/Bangkok), FIFO/random selection, YouTube audience choice, enable/save. Manual scheduling remains optional in a collapsed section.
- Content comes from completed local MP4 outputs with valid existing captions. The user selected random unused video selection; this is the default. FIFO remains optional. No new caption input.
- A video already used by any batch or reserved by the recurring scheduler is excluded permanently from automatic selection. Failures are retried on their original batch, not republished as a new batch. Previously cancelled manual batches also remain excluded to avoid silently resurrecting discarded content.
- Each UTC slot has one durable run record and at most one reserved video. Reservation and video exclusion are atomic. A crash resumes the same reservation/idempotency key rather than selecting another item.
- Run the scheduler in a background thread independent of long browser uploads. Existing process lock and task checkpoint protection continue to apply.
- Saving configuration applies only from that save forward. Switching off stops new daily selections; already-created batches continue and can be cancelled separately.
- After downtime, only the latest due slot within 15 minutes can run; older slots are logged as skipped, without catch-up bursts. Empty slots are recorded once and not filled later that hour.
- If no platform has a saved connected session, record a blocked slot without consuming a video. Individual expired sessions remain separate per-platform failures.
- Keep automation disabled until the user enters times and enables it. Development/tests must not enable the real configuration or publish anything.

## Components
Add `services/social/daily.py` for timezone/config validation, candidate discovery and daily dispatch. Extend Store with recurring configuration, atomic slot/video reservations and run receipts. Extend status/config API and the existing publishing page. Preserve caption snapshots, media snapshots and all previous per-platform recovery behavior.

## Verification
Temporary SQLite tests cover duplicate ticks, concurrent reservations, previous manual use, tomorrow rollover, timezone conversion, missed slots, empty queue, pause/reconfigure, random selection, snapshot failure/recovery, and delayed worker uploads. Real local-browser tests cover saving daily times without choosing a video. No live-account posting tests.
