# Separate creation and library pages

User: separate video creation from library management. Keep current colors/full width.

Design: `/create` contains download/render controls, default render settings, counters and concise processing activity. `/` remains library to preserve existing record/caption links, contains counters, caption toolbar and management table/player only. Sidebar has distinct Tạo video and Thư viện entries. Extract shared video controls/stats/player partials and assets. Existing classic video handlers guard absent elements; create module starts shared shell polling without caption settings requests. Library retains per-record render actions. Tailwind content includes extracted partials.

- [x] Red route/UI checks for separation, navigation and functional creation controls.
- [x] Extract templates, add route/nav/module, make shared video controller page-aware.
- [x] Build utilities with preserved variable initialization and run relevant/full tests.
- [x] Review, idle reload and live page/screenshot verification.

Verification: 135 tests pass. UI covers mocked download/render requests, processing/completed counters, empty-library link and navigation between pages. Review found no material regressions; corrected empty-state copy. Idle server reloaded. Live `/create` has form/no table/no caption API requests; `/` has caption toolbar and five records/no form. Desktop creation screenshot inspected; responsive checks pass. No real download/render, AI/STT or posting jobs were triggered.
