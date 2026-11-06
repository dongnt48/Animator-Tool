# Cấu trúc dự án

```text
app.py                         Flask entrypoint, video library API
database.py                    Local video library persistence
services/
  animation/
    settings.py                Antigravity mode/model and CLI/speech runtime discovery
    timing.py                  Word timestamp validation and phrase grouping
    speech_worker.py           Local CPU/int8 faster-whisper in a separate Python process
    planner.py                 One structured CLI request, semantic validation, reusable cache
    routes.py                  Local animation configuration/readiness API
  captions/
    client.py                  Server-side XAH completion request, sanitized errors
    routes.py                  Select/rewrite videos, direct AI save and manual caption edits
    transcripts.py             Recognize dialogue on demand and reuse media-aware cache
    hashtags.py                Validate user hashtag settings and sanitize generated captions
    provider.py                Validate local model/key updates and expose key-free status
  downloader.py                Download original videos
  video_identity.py            Source IDs, normalized video URLs and retained hash identity
  video_deletion.py            Soft-delete record and safely remove related local media
  transcriber.py               Audio extraction and transcription
  analyzer.py                  Build animation scenes
  renderer.py                  Invoke tracked Remotion engine; preserve old output on errors
  social/
    pages.py                   Admin HTML routes only
    thumbnails.py              Safe local video frame extraction and fingerprinted JPEG cache
    routes.py                  Publishing JSON API and process startup
    store.py                   SQLite schedules, sessions, reservations
    daily.py                   Recurring hours and unused-video selection
    browser.py                 Playwright platform upload flows
    login.py                   Manual login process
    worker.py                  Independent publishing worker
templates/
  index.html                   Entry template selecting the standalone library page
  admin/
    layout.html                Shared admin shell
    partials/                  Sidebar, daily controls, shared caption editor/results
      library-schedule.html    Inline scheduling dialog on the library page
    pages/
      overview.html            /publishing
      schedule.html            /publishing/schedule
      accounts.html            /publishing/accounts
      results.html             /publishing/results
      new.html                 /publishing/new
      library.html             / (video management, captions and publication status)
      create.html              /create (download/render controls and processing activity)
      animation.html           /animation (dedicated Antigravity workflow)
      captions.html            /publishing/captions (legacy bulk caption results)
      video-detail.html        /videos/<id> (one record, caption editor and publication)
static/admin/
  css/controls.css             Shared publishing controls
  css/layout.css               Admin navigation and responsive layout
  js/core.js                   Shared API, notices, polling and DOM helpers
  js/pages/                    One module per admin page
  js/pages/library-schedule.js  Library row scheduling, validation and idempotent retry
  js/library.js                Existing video controls, extracted from index.html
tests/                         Unit and local-browser integration checks
remotion/                      Tracked Cozy composition and timed action library
tools/setup-animation.ps1      Optional Python speech environment and renderer setup
data/social/                   Ignored: SQLite, sessions, media, diagnostics
downloads/, outputs/           Ignored: original and rendered media
```

Each admin page loads only its own JavaScript module and extends the same layout. Sidebar links navigate to distinct URLs. A legacy `/publishing?video=<id>` link redirects to `/publishing/new?video=<id>`.

Admin pages use `templates/admin/` exclusively. The obsolete route-migration notice template has been removed.

The video library stays at `/` and uses the same admin layout and navigation as publishing. It includes bulk caption controls and compact progress, with selection checkboxes, detail links and per-video rewritten badges in the existing table. Manual caption editing use `/videos/<id>` and `pages/video-detail.js`; `/api/social/videos/<id>` supplies whitelisted metadata, saved caption, cached dialogue, safe local media URLs and publication summary without external calls. `pages/library.js` imports the shared caption controller; `library.js` emits `library:updated` so periodic table replacements preserve selections. The standalone caption URL remains compatible but has no separate sidebar entry. Existing video actions remain in `static/admin/js/library.js`; local utility CSS is compiled into `static/admin/css/library-utilities.css` using `tools/ui/library.tailwind.cjs`. The optional rebuild command is recorded at the top of that config. Pages work without a runtime Tailwind CDN; Font Awesome remains an optional external icon stylesheet.

The AI Remotion engine lives in tracked `remotion/`. Legacy rendering continues to use the former sibling project when present, with the tracked engine as a fallback. Generated audio/props and Node dependencies are ignored. Optional `.venv-speech` isolates the stable speech-recognition runtime; `data/animation/` stores source/model-aware speech and storyboard caches. `/animation` alone loads `video-animation-settings.html` and `pages/animation-settings.js`, with its video picker and render controller in `pages/animation.js`. AI renders use `/api/animation/render/<video_id>` and snapshot settings at enqueue. The original create/library render endpoints explicitly use legacy mode regardless of saved AI settings. AI output files use an `antigravity_` prefix to retain the old rendered media.

Video creation is at `/create`, with download/render controls, default settings, counters and processing activity. It loads `pages/create.js` for shell polling and the shared video controller, without caption configuration requests. The library keeps record actions and its video player. Shared markup lives in `partials/video-create-controls.html`, `video-stats.html` and `video-player.html`; Tailwind scans these partials when rebuilding utilities.

Creation activity shows all running jobs before waiting jobs, with thumbnail, record link, status and real pipeline stage/log. It recognizes batch queue log entries separately from active rendering, preserves observed completions for 60 seconds and avoids replacing unchanged rows during polling. Old completed library items stay out of this activity list. Poll failures mark the summary as stale until recovery. Validation: 175 tests passed; dedicated browser coverage exercises 12 simultaneous visible jobs, queue classification, stage indicators, completion expiry, mobile width, focus retention and connection recovery. Live rendering was simulated in the browser without creating jobs or changing library records.

## Adding a page

`services/covers/` decodes bounded raster uploads, selects local video frames, composes Vietnamese cover titles/crops and serves `/api/covers/videos/<id>`. The detail page loads `pages/cover-editor.js`. Metadata and replaceable cover files belong to the library record; immutable schedule JPEGs live beside video snapshots under the social data directory's `media/`. Daily workers generate missing legacy covers in a temporary directory without writing the library JSON. `social/cover_flow.py` applies supported cover UI conservatively and stores preview/frame/automatic/review status separately from post publication status.

1. Add its view and route to `services/social/pages.py`.
2. Add `templates/admin/pages/<name>.html` extending `admin/layout.html`.
3. Add `static/admin/js/pages/<name>.js` importing shared helpers from `../core.js`.
4. Add a sidebar link and browser navigation coverage. Do not duplicate API or worker logic in page modules.
