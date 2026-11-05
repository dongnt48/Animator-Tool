# Bulk caption rewrite plan

Goal: Select the whole library, process sequential groups of at most 100 videos with one AI completion per group, and persist generated previews and their status.

Architecture: Browser freezes selected IDs and settings, sends groups sequentially and retains earlier results on failure. Server prepares dialogue locally (up to three recognition workers), submits all valid items together, validates response IDs and stores previews without replacing approved captions. Save remains explicit and conflict checked. Based on the previous 12,000-character dialogue setting, 300 is interpreted as the dialogue input limit; this assumption was disclosed while awaiting optional clarification. Keep full cached dialogue, send first 300 characters and report shortening.

- [x] Add failing coverage for a single 100-item provider call, ID mapping, malformed/missing/duplicate results, persistence and batch limits.
- [x] Implement batch provider and preview persistence; retain sanitized errors and original captions.
- [x] Update selection, sequential requests, progress, restore previews, markers and chunked saves.
- [x] Apply disclosed 300-character dialogue assumption and verify bounds.
- [x] Run focused and complete tests, request review, safely reload idle server and check live page.

Verification: 105 tests passed (including real local Playwright UI with mocked provider/STT). A 205-video selection makes 100/100/5 requests, restores all previews and saves all captions. A later network failure retains the first batch. Review found no material defects. Live caption page/API returned 200 after safe reload. No real provider, audio recognition or social posting calls were made during this change.
