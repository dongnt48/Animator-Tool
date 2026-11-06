# Express dialogue with animated scenes

User clarified that the initial AI output still looked like the original sitting character; the desired result is animation expressing the sentence's meaning. The prior light gestures did not fulfill that intent.

## Implementation

- AI must select one of ten semantic situations plus a supported action and a real spoken cue word: parting, support, burden, crossroads, growth, journey, conversation, reflection, celebration, peace.
- Group consecutive subtitles with the same visual into a shot and retain triggered actions across subtitle boundaries. Reset state on a new visual. Articulated arms/legs and coordinated actors/props express the story.
- New `DialogueStoryVideo.tsx` renders only AI (`timedDialogue`) props; original creation/library flow and Cozy composition stay separate.
- `storyMotion.ts` contains pure timing and rig math; Node assertions cover cue gating, motion of limbs, same-shot continuity, new-shot reset and silence.
- Story cache version is separate from speech cache version. Upgrading the prompt/schema causes one new story request but preserves local recognition cache. No live AI requests are needed for deterministic checks.
- A 30-second ten-scene fixture demonstrates motion without narration. It is a test artifact, not a claim of a live AI-planned user video.

## Validation

- 156 Python/UI tests passed before final illustration refinements; TypeScript and pure motion checks passed.
- Full semantic scene fixture exported to ignored `data/animation/story-scenes.mp4`; inspected contact sheet at action timestamps.
- Legacy generation does not choose the new scene renderer or call Antigravity.
- Follow-up motion checks ensure later nod/idle subtitle cues cannot reset a structural event such as releasing a rock, and the shot waits for its meaningful cue.
- A second independent reviewer was unavailable because its execution quota was exhausted; the implementation was reviewed directly and validated with TypeScript, Node motion assertions, 17 focused Python tests and the 156-test full suite.
- Final ten-scene fixture exported successfully after illustration fixes. Studio reloaded using verified idle process IDs; `/animation` and `/create` return HTTP 200. No live model calls or posts were triggered by these checks; existing v1 videos need an explicit AI rerender.

## Run status follow-up

User screenshot showed a job already failed on a legacy `semantic_dark` style while the UI retained its accepted-request message. AI routing now maps known legacy styles to compatible runtime styles and rejects unknown options before queueing. AI runtime aliases do not overwrite original style/ratio/character settings in the library.

Added prominent running/error/completed state, busy spinner, four-stage progress indicator (not fake percent), and terminal messages replacing stale acceptance text. UI tests cover processing → error → retry → completed; legacy-style normalization and preservation are covered in Python. Final full suite: 159 tests passed in 60.697 seconds. Live browser confirmed failed video #6 shows `Thất bại`, `aria-busy=false`. Server reloaded idle; no model call or rerender was triggered.
