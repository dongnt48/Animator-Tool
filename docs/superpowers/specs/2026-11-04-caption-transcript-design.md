# Caption rewriting from video dialogue

User wants video dialogue included as input to caption AI. Send recognized dialogue text, existing caption and user instruction; do not send raw video/audio to XAH. Use whole dialogue up to an application cap of 12,000 characters, reject longer text explicitly rather than silently truncating. This is an application input cap, not a claimed provider context limit.

The AI page defaults its visible `Dùng lời thoại` checkbox on. Its disclosure explains that uncached audio is recognized through the existing Google speech recognition integration; XAH receives text only. Legacy API calls omitting `include_transcript` keep caption-only behavior.

Persist real recognized dialogue in the local video record, including when rendering new videos. Never persist the rendering fallback phrase as recognized dialogue. Existing videos can transcribe on demand from safe local original media or rendered output. Cache with a media stat fingerprint; reuse cached text when the source still matches, or when the source is gone. Serialize extraction for a video so duplicate requests do not transcribe it simultaneously.

Missing audio, recognition failure and over-limit dialogue produce per-video errors without an AI request. Preview responses show exact dialogue text and character count used. Preserve caption preview/explicit-save behavior and scheduled caption snapshots.

Verification uses temporary media/database and mocked recognition/provider calls. No user audio sent to external services during development. Test strict no-fallback behavior, cleanup, cache, safe paths, source changes and exact provider payload.
