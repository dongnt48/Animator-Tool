# Soft-delete video records and retain duplicate history

User requested soft-deleted records with hard-deleted media so previously removed videos remain detectable as duplicates.

- Persist `deleted_at`, source identity and original-media SHA256 in the existing JSON store. Keep original IDs/STT/metadata, hide tombstones from normal lookups, captions, rendering and daily selection.
- Match TikTok numeric source ID, normalized video URL, and known original-file hash, including deleted records. Check before downloading and again after resolving/downloading a new unique file. Do not use captions/titles for deduplication.
- Preserve metadata before deleting local original/output/thumbnail files. Remove known render variants belonging to the record, keep deletion manifest for retry, constrain all paths, refuse deletion of processing videos and preserve shared files still referenced by active records.
- Reject duplicate direct URLs before background work; channel downloads skip duplicate items, including tombstones. Existing files are never overwritten by a speculative download.
- Automated validation uses temporary media/JSON stores and mocked downloaders only; no real user media deletion, posting or AI requests.

## Verification and rollout

- 15 focused tests cover tombstone retention, file/variant deletion, content-hash and canonical-source duplicates, channel skips, shared file preservation, cleanup retry, path traversal, corruption protection, atomic writes and a render/delete race.
- Independent review found a render/delete race in the initial preflight check. Fixed by rejecting `processing` and persisting tombstone under the same database lock; renderer stops if its first processing claim finds a deleted record.
- JSON writes now use fsync and atomic replace. Invalid history blocks writes instead of being silently discarded. Deleted records have `status=deleted` plus `status_before_delete`, also protecting selection by older worker processes until they reload.
- Full suite passed: **174 tests in 62.882 seconds**. JavaScript syntax and changed Python source parsing passed. No real downloader, AI, posts or destructive media tests were run.
- Studio reloaded while idle. Live duplicate-check endpoint returned the existing source match. Current record count stayed 1 and JSON checksum remained `630b7bf380974aa48b85b8384f91b49d0ed31592fa6f7608d390eb0379622ab4` across reload; actual user records/media were not deleted or modified during verification.
