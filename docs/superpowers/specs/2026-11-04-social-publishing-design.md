# Social publishing

## Agreed intent
Use Playwright for Facebook, Instagram, Threads, TikTok and YouTube. One schedule distributes a rendered video to all five. Reuse the existing caption (currently `video.title`, including hashtags); do not ask the user to type it again. Work on a new branch.

## Implementation choices
- Local Windows execution with a headed browser, a dedicated browser profile per platform, and one publishing worker. The computer must be awake and online.
- Facebook/Instagram publish one Reel on the personal account, not two duplicate posts. This is an implementation assumption because the earlier question was unanswered.
- Persistent SQLite jobs and independent per-platform outcomes. One account per platform for this first version. Capture the caption and an immutable, hashed MP4 copy when scheduling.
- User logs in manually and explicitly saves the session. Never automate CAPTCHA/2FA. Session files, screenshots, videos and database stay out of Git.
- Scheduling is consent to attempt publication at the chosen time. Require an explicit YouTube audience choice and an explicit confirmation of the five destinations.
- Every final publish click has a durable checkpoint. After a timeout/crash across that checkpoint, require checking the destination; never automatically click Publish again.
- Mark published only with a success indication and a platform-specific permalink. Otherwise show needs_review, with diagnostics. Never infer success from a click alone.
- Scope receipts to the platform's completion/share dialog or status announcement. Feed and recommendation links must never identify the upload. A user can resolve an ambiguous outcome by checking the account and supplying its permalink.
- Replaying an accepted schedule request returns the original batch even after its due time or source deletion. Changing the client intent under the same key is a conflict.
- Retry only a failed/needs_login destination; needs_review requires explicit acknowledgement that the user checked for an existing post. Never retry successful targets.
- A process lock prevents competing workers; DB leases prevent login and publish from using the same profile concurrently. Interrupted pre-submit jobs are retryable; interrupted submissions require review. Overdue schedules by more than 15 minutes require user review rather than silently posting late.
- Bind the dashboard to loopback and validate render settings before storing credentials. New mutation endpoints accept same-origin JSON only.

## Alternatives
API-only and hybrid were discussed. The user explicitly selected Playwright for all five. UI adapters are provisional until tested with the user's accounts; tests validate local control flow, not platform compatibility.

## Parts
`services/social/store.py`: SQLite batches, tasks, accounts and leases.
`services/social/browser.py`: browser profiles, manual login, UI automation adapters and receipts.
`services/social/worker.py`: durable scheduling and task execution, separate process.
`services/social/routes.py`: Flask blueprint and validation.
`templates/publishing.html`, `static/publishing.js`, `static/publishing.css`: accounts, preview, schedule and per-platform results.

## Limits
No platform APIs, bulk account management, automatic verification bypass or guaranteed simultaneous public visibility. Do not perform real posts during development without the user's connected sessions. The UI must identify unverified platform adapters honestly.

## Verification record
43 automated checks passed, including real local-browser upload fixtures for all five adapters, Flask dashboard scheduling, lost HTTP response recovery, malicious caption text rendering, media snapshots, per-platform retries, account binding and crash recovery. Desktop 1440px and mobile 390px checked without horizontal overflow. A real worker process was checked in an empty temporary data directory, including heartbeat and rejection of a competing worker. No real accounts or posts were used.
