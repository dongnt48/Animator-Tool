# Publishing cover images

User approved: local frame + short headline, editable in video details, uploaded image alternative, one common cover with portrait/landscape variants. Scheduling freezes the cover alongside video/caption. Playwright must report verified custom cover, selected video frame, automatic cover or review-needed separately from publication success.

## Tasks

- [x] Test and implement bounded image decoding, Vietnamese text composition, frame selection, stored cover metadata and guarded loopback routes in `services/covers/`; add editor to detail page with crop positioning.
- [x] Add cover snapshot/hash columns to social batches and task cover-status fields; wire manual/daily scheduling and verify immutable files before publishing.
- [x] Add conservative cover adapters at actual edit steps. Use explicit cover-scoped image inputs/dialogs only; confirm changed preview or frame slider, never infer success from upload alone. Unsupported UI uses platform preview and reports it.
- [x] Integrate default cover generation after rendering/scheduling; include assets in soft-delete media cleanup; test browser fixtures, migrations, snapshot retention, malicious uploads and old schedules. No live posts, logins, AI or external uploads during testing.

## Constraints

5 MiB uploads; JPEG/PNG/WebP only, <=20 million pixels. Generated JPEG variants 1080×1920 and 1280×720, headline <=100 characters; no automatic AI request. Store snapshot paths privately and return cover-state/status only through public publishing responses. Old tasks remain compatible without covers. Image rendering failure must not invalidate an otherwise completed video. A generated poster inserted into the MP4 is not part of this change.

Validation: full suite 191 tests passed; subsequent cover/browser suite 23 tests passed including crop focus. Local browser checks cover actual upload, caption/title changes and mobile sizing. Review fixes retain transcript persistence and keep daily worker cover generation read-only against the JSON library. Platform-account UI remains unverified against live accounts; cover status reflects preview evidence before publishing, never inferred final live-post confirmation.
