# Antigravity dialogue animation implementation plan

> Updated 2026-11-06 per user request: Antigravity now has a dedicated `/animation` tab. Create/library legacy buttons never opt into AI and no longer load its configuration/controller. A separate AI endpoint, video picker, model settings and progress display own the AI workflow. Legacy keeps its original sibling engine when available; AI output names have a separate prefix. This supersedes the shared-mode UI described in the original design below.
>
> Verification of segregation: 155 tests passed in 54.285 seconds, including legacy single/batch/download paths ignoring AI settings and mobile inline AI configuration/render UI. JavaScript syntax checks and independent review passed. No live AI calls or social posts were made for this update.

**Goal:** Use the user's Antigravity subscription through the official CLI for semantic scene planning, with local timed speech recognition and Remotion rendering.

**Approved direction:** User selected transcript + timestamps → Antigravity JSON storyboard → local Remotion. Existing caption rewriting and its 300-character limit are independent. Animation uses the full transcript.

**Design:** Keep the existing render mode available. A compact shared settings panel selects the mode for the next run, CLI model (blank uses account default), and local Whisper model. The server snapshots settings for the whole queued run. Recognize on CPU/int8 with faster-whisper word timestamps; group at pauses or at most 9 words. AI chooses only supported scene moods, actions and annotations, referencing immutable segment IDs and cue word indices. Python retains all timing and spoken text, validates complete AI coverage, and builds Remotion props. Cache by source fingerprint, recognition model, prompt version and AI model. Serialize expensive planning and per-video rendering. Errors stop the AI render clearly, never silently switch provider or fabricate dialogue. Preserve existing output on failure.

**CLI:** Official `agy`, authenticated by the user in their own terminal. No API key extraction, no XAH fallback. Run in an isolated temporary directory, with no tool permissions, finite timeout, JSON schema/output, no automatic quota retries. Public readiness only checks installation/dependencies without making a model call.

**Remotion:** Bring the existing Cozy composition into tracked `remotion/`, leaving the external sibling untouched. Add optional timed actions and speech-aware subtitles/mouth/equalizer while keeping older props compatible. Reuse all existing characters, themes and aspect ratios. This phase uses the existing character/action library; full generated illustration and multi-character story scenes are outside this change.

## Tasks

- [x] Add failing tests for CLI errors/schema, real timing preservation, cache invalidation, settings validation and render mode routing.
- [x] Implement `services/animation/` settings, timed transcription, planning/cache and Flask routes.
- [x] Connect renderer and compact settings on create/library; preserve download-only and existing captions/schedules.
- [x] Track Remotion engine and implement timed cue actions, bounded subtitles and silence handling.
- [x] Install local dependencies/official CLI; run unit, UI, TypeScript and fixture rendering checks. Automated checks never call AI; manual smoke probes use Antigravity quota. Document interactive login and limits.

## Verification focus

No speech, missing timestamps, delayed speech and silence, malformed/incomplete AI output, quota/auth/timeouts, changed source files, rerender caching, duplicate clicks, unavailable CLI and existing-mode compatibility. No live posts or user-content AI calls during automated verification.

## Implementation decisions and evidence

- Existing Python is 3.15; speech dependencies installed in a separate Python 3.13 environment. Pinned PyAV 16.0.1 because PyAV 19 removed `metadata_errors`, used by faster-whisper 1.2.1.
- Official `agy` 1.5.1 installed and its models command verified. A single tiny live schema probe succeeded through the account session; automated tests use mocks only. A manual 15-second media preview verifies local recognition, one semantic planning request and rendering without modifying the library or posting.
- No output overwrite until Remotion creates the replacement successfully. Rendering uses per-video locks; expensive speech/AI planning is serialized. Speech and storyboard cache keys are independent so changing the AI model does not repeat recognition.
- Global selected mode is snapshotted at enqueue rather than silently preferring an old per-video setting. This makes the visible configuration apply to every requested render consistently.
- Final independent code review found no significant issues. TypeScript and six-second fixture rendering passed. The live 15-second preview has seven semantic scenes and preserved original audio; exported to ignored `data/animation/demo-dialogue.mp4`.
- Final full verification: 153 tests passed in 55.416 seconds; TypeScript check, source parsing, fixture MP4 render and secret-pattern scan passed. No social posts were triggered.
- Backend restart was attempted only after confirming no active rendering/posting; automatic command approval rejected both process-stop approaches with `blocked by policy`. The existing Studio process was left running. User must reopen `run.bat` to load the new backend.
