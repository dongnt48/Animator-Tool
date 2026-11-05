# Social Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Schedule a rendered video with its existing caption to five personal social accounts through Playwright.

**Architecture:** A local Flask page creates a SQLite batch with five independent targets. A separate worker controls dedicated browser profiles; a durable submission checkpoint prevents automatic duplicate posting after ambiguous outcomes.

**Tech Stack:** Python, Flask, sqlite3, Playwright Python, vanilla JavaScript and CSS.

**Spec:** `docs/superpowers/specs/2026-11-04-social-publishing-design.md`

## Global Constraints
- Use Playwright for Facebook, Instagram, Threads, TikTok and YouTube.
- Reuse video.caption if present, otherwise video.title. No new caption entry.
- Facebook/Instagram post one Reel per destination. Local machine must stay awake.
- Never automatically retry a task after its final publication checkpoint.
- Do not commit profiles, diagnostics, databases or media.
- Do not publish to real accounts in automated tests.

## Review Focus
- Concurrent workers cannot claim one target twice or open a leased profile.
- Lost response after Publish becomes needs_review, never queued.
- Stale schedules after downtime do not unexpectedly publish.
- Malformed timestamps, path traversal and non-same-origin requests are rejected.
- Repeated scheduling requests and retries cannot replay successful targets.

### Task 1: Durable schedules
**Files:** Create `services/social/__init__.py`, `store.py`, `tests/test_social_store.py`.
**Interfaces:** `Store(path)`, `create_batch(video_id, media_path, caption, scheduled_at, made_for_kids, request_key)`, `list_batches()`, `claim_next(owner, now)`, `mark_submitting(task_id, owner)`, `finish(task_id, owner, state, message, url)`, account session/lease methods.
- [x] Write failing tests for five targets, caption snapshots, atomic claims, leases, restart recovery, overdue tasks, duplicate request keys and retry guards.
- [x] Run `python -m unittest discover -s tests -v`; confirm missing feature failures.
- [x] Implement SQLite transactions, hashes, durable checkpoints and leases.
- [x] Run tests and confirm pass.

### Task 2: Playwright publishing
**Files:** Create `services/social/browser.py`, `worker.py`, `login.py`, `tests/test_social_worker.py`, `tests/test_social_browser.py`.
**Interfaces:** `publish(platform, media_path, caption, made_for_kids, profile_dir, before_publish) -> Receipt`; `Worker(store, publisher).run_once()`; login subprocess exchanges save/cancel commands through Store.
- [x] Write failing tests for failure before/after submission, successful receipt, missing media, stale media hash, unavailable account and safe permalink matching.
- [x] Implement headed browser contexts and five UI adapters with bounded waits and explicit success receipts. Implement login and a single worker lock.
- [x] Test real browser interactions against local HTML fixtures, never social accounts.
- [x] Run tests and confirm pass.

### Task 3: Dashboard and local security
**Files:** Create `services/social/routes.py`, `templates/publishing.html`, `static/publishing.js`, `static/publishing.css`, `tests/test_social_routes.py`; modify `app.py`, `services/renderer.py`, `.gitignore`, `run.bat`; add `requirements.txt`.
**Interfaces:** GET `/publishing`, GET `/api/social/status`, POST `/api/social/accounts/<platform>/connect|save|cancel`, POST `/api/social/batches`, POST `/api/social/tasks/<id>/retry`, POST `/api/social/batches/<id>/cancel`.
- [x] Write failing tests for available video selection, reuse existing caption, invalid timestamps/audience, missing output, same-origin enforcement and unsafe render settings.
- [x] Build an accessible page matching the existing warm theme. Preview video/caption, explicit confirmation, all five destinations and independent receipts. Use textContent for remote text.
- [x] Connect blueprint, use loopback binding, validate renderer enums and avoid unquoted command construction.
- [x] Run unit tests, JavaScript syntax checks and browser smoke tests at desktop/mobile sizes.

### Task 4: Review and handoff
**Files:** Update `README.md`, design/plan progress.
- [x] Document install, browser setup, manual login, worker startup, missed schedules and ambiguous submissions.
- [x] Run all tests and review the whole change with a fresh reviewer. Fix material findings and rerun relevant checks.
- [x] Report branch, verification and limits. No push or real posting during implementation.

## Execution ledger
- Ruling: proceed in the requested new branch in this checkout, preserving existing files; no worktree relocation because Remotion currently relies on its sibling path.
- Ruling: user said to implement after choosing the approach; proceed without another approval round.
- Git baseline commit attempted but identity is not configured. Do not invent an author or change global Git settings. Branch `feat/social-publishing` created successfully; original files staged by the baseline attempt.
- Pre-flight: Task 1 produces Store state machine consumed by worker/routes. Task 2 produces Receipt consumed by worker and displayed by Task 3. State names and interfaces must remain consistent.

- Task 1: complete ? durable SQLite schedules, idempotency, independent targets, account leases and media snapshots verified.
- Task 2: complete ? headed login/publish processes, five adapters, scoped receipts and checkpoint recovery verified against local browser fixtures.
- Task 3: complete ? responsive dashboard, existing caption preview, per-platform retry/manual receipt and loopback security checks pass.
- Task 4: complete ? 43 tests passed with Playwright installed; JavaScript/Python syntax checks, worker lifecycle smoke and ignore rules verified. No real posts made.
- Review: fresh reviewer found time-sensitive idempotency and unrelated receipt-link acceptance. Added failing regressions, fixed both; follow-up caught the matching UI freshness check, also reproduced and fixed with a browser test.
- Ruling: immutable media snapshots added because changing an output while a scheduled upload waits could otherwise change published content. Disk copies persist until explicitly cleaned when no longer needed.
- Ruling: keep the requested feature branch in place. No merge/push requested. No commits created because Git author identity is absent; do not invent it.
- Platform compatibility remains unverified without the user's manual login and controlled real posting test.
- Facebook follow-up: real failure log and screenshot showed the final Settings screen with Đăng after only one Next. Removed the fixed two-Next assumption, filled caption while its editor is visible, and added three local-browser regression cases. Preparation still never clicks Publish. Clarified active-profile behavior and lack of a Fanpage selector. Fresh reviewer found no material regression; no real post was retried during this fix.
