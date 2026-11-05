# Video record detail

Requirement: Remove the long inline Caption mới block and open one record's details on click. Keep bulk rewrite on library, drafts and explicit save.

Design: `/videos/<id>` uses the shared full-width admin shell and original palette. Library titles and a Chi tiết link open it. Show video previews, metadata/render status, publication states, current caption and one editable AI draft with save, and collapsed dialogue. GET does not invoke AI/STT. Bulk rewrite shows a compact count/error report and retains drafts in storage; detail page reviews/applies them. Legacy caption URL stays compatible.

- [x] Regression tests: library has no caption editor list, detail navigation/display/save, stale conflict, missing record404, API data and no side effects.
- [x] Detail API/page/controller, safe media and publication links.
- [x] Library links and compact batch feedback, remove inline result partial only from library.
- [x] Full tests, read-only review, safe reload and live verification.

Verification: 109 tests pass. Local Playwright covers bulk rewrite, detail navigation, stale edit rejection, explicit save, back navigation and responsive widths. Desktop screenshot inspected. Review found no important defects. Live root, one existing record page and its API returned 200 after idle-server reload; root contains no inline captionResults. No real AI/STT or posting calls were made.
