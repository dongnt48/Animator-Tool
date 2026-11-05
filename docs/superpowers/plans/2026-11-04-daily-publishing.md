# Daily Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Implement natively with a fresh reviewer at completion.

**Goal:** Automatically take one unused rendered video at each user-selected daily time and publish to all five platforms.
**Architecture:** Persistent configuration and atomic slot reservations drive existing five-target batches. A separate scheduler thread runs alongside the browser worker, so uploading does not block future slots.
**Tech Stack:** Python sqlite3, zoneinfo/tzdata, Flask, vanilla JS and existing Playwright adapters.
**Spec:** `docs/superpowers/specs/2026-11-04-daily-publishing-design.md`

## Global Constraints
- All five platforms and existing caption/media snapshot behavior remain unchanged.
- No real publishing or activating real daily settings during development.
- At most one video per slot, no reuse of previously selected videos.
- Default Asia/Bangkok; do not use host timezone implicitly.
- Preserve existing manual history and optional manual scheduling.

## Review Focus
- Duplicate/concurrent ticks must not reserve a video twice.
- Crashes between reservation, snapshot and batch creation must resume idempotently.
- Editing/pausing during snapshot must not create a batch under stale consent.
- Empty queues, disconnected accounts and missed slots must not generate catch-up bursts.
- Polling status must not overwrite unsaved configuration in the browser.

### Task 1: Durable daily dispatch
Files: `services/social/daily.py`, `store.py`, `worker.py`, `tests/test_social_daily.py`.
- [x] Write failing tests for configuration validation, timezone-aware slots, FIFO/random, one batch per slot, exclusions, crash recovery and stale configuration.
- [x] Implement Store configuration/reservations and DailyScheduler.tick; preserve existing create_batch idempotency.
- [x] Integrate a scheduler thread into worker main; test independent ticks.
- [x] Run daily tests and existing store/worker suite.

### Task 2: Daily API and UI
Files: `services/social/routes.py`, `templates/publishing.html`, `static/publishing.js`, `static/publishing.css`, route/UI tests.
- [x] Write failing tests for saving times without video choice, malformed input/consent, and dirty-form polling.
- [x] Add daily config/status API. Make daily schedule primary, manual schedule collapsible.
- [x] Show queue availability, next selected time and last automatic outcomes.
- [x] Run browser UI tests at desktop/mobile sizes and JS syntax check.

### Task 3: Verify and reload
- [x] Fresh read-only review and regression fixes; run full suite.
- [x] Document operation and update progress.
- [x] Safely reload idle server/worker without enabling real automation; otherwise preserve running tasks and report restart needed.

## Ledger
- User has explicitly requested the changed behavior; proceed with implementation without another approval loop.
- Remain on `feat/social-publishing`; no destructive integration or author identity changes.
- Pre-flight: daily dispatcher produces existing batches via Store.create_batch. Worker task states/receipts stay unchanged. Routes and worker share candidate validation through daily module to avoid Flask-context coupling.

- Task 1 complete: persistent daily slots, atomic reservations, random unused selection, timezone handling and crash recovery implemented.
- Task 2 complete: daily configuration is primary UI, manual scheduling is collapsible, dirty form survives polling, status shows unused count and recent slot outcomes.
- Task 3 verification: 69 tests passed including local browser UI; JS syntax check passed. Reviewed reservation/config races and preserved submission checkpoints.
- User selected random unused video selection; changed default accordingly. No live automation was enabled and no real posts were made.
- Runtime reload NOT performed: automatic execution policy rejected the combined process-restart command before execution. User must close old Studio/worker and reopen run.bat. Existing login profiles and history are preserved.
