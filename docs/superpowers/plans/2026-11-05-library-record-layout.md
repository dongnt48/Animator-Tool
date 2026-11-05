# Compact library records and separate media columns

User: short ellipsized titles, remove Preview column, move Original and Rendered to two thumbnail columns, remove Details action and click record to open.

Design: two-line CSS clamp keeps full caption in title tooltip and detail page. Add lazy image thumbnails extracted from each actual local video via safe read-only cached JPEG endpoint. Missing media shows clear placeholder. Each thumbnail opens existing player; checkbox/buttons/selects/links do not trigger row navigation. Title link plus keyboard Enter on row preserve detail access. Keep palette/full width and all existing actions.

- [x] UI regression for headers/truncation, thumbnail preview and record navigation without interfering with controls.
- [x] Cached first-frame endpoint constrained to valid local library media, missing-media checks.
- [x] Refactor table rows/headers, compact styles and delegated row events.
- [x] Relevant tests, screenshots/review and safe reload/live verification.

Verification: 135 tests pass, including real fixture-video JPEG extraction/playback and selection/row-click isolation. Three unit tests cover caching/invalidation, unsafe paths and timeout cleanup. Review found no material issues. After idle reload, live library has 12 matching headers/cells, two-line clamping and valid thumbnails; live screenshot inspected. No provider/STT or posting actions were performed.
