# Save AI captions directly

User explicitly removes the draft/review step. Successful AI results must immediately replace video.caption and update library display. Keep original title, optimistic conflict protection, mode selection, tags/provider settings and batch100. Errors leave existing captions intact. Already scheduled snapshots are unchanged.

Store each successful result as caption plus optional caption_ai_result provenance. Convert existing matching legacy drafts at normal app startup before worker starts, backing up videos.json under ignored data/social first; never replace a changed caption with a stale draft. Detail page edits current caption; no draft language. Legacy caption page's generated results are already saved; optional further edits still require explicit manual save.

- [x] Red coverage for immediate persistence, per-item errors/conflicts, old-draft conversion and schedule preservation.
- [x] Direct-save storage/routes, safe migration and UI wording/refresh.
- [x] Update tests to new behavior, full suite, review, idle restart and verify actual captions.

Verification: 131 tests pass. Review found no material issues. Safe restart converted 3 matching existing drafts; live API confirms all 3 captions applied, zero legacy drafts remain, original titles unchanged and backup exists. Existing scheduled caption snapshots are covered by a regression test. No real AI/STT or social posting calls were made.
