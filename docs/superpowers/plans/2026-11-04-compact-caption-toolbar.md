# Compact caption toolbar and rewrite scope

User: compact the caption area; choose rewrite all or only not-yet-rewritten videos.

Design: one wrapping toolbar using original palette; fold explanatory text and instruction into options. Preserve transcript toggle and library selection. Mode defaults to unwritten in UI and applies to selected records; all mode intentionally includes existing drafts/saved captions. Eligible count updates on selection, mode and polling. Freeze IDs/mode for a run and keep batch100/300 dialogue. Backend rechecks the selected mode and skips persisted drafts/saved/legacy rewritten captions before recognition or AI, while omitted mode remains all for existing callers.

- [x] Failing API/UI tests for scope, no unnecessary AI/STT, eligibility changes and all mode.
- [x] Mode validation/skip behavior and compact template/controller/styles.
- [x] Full suite, screenshot inspection, review and idle reload.

Verification: 113 tests pass. UI verifies existing draft/saved records excluded in unwritten mode, all mode includes every selected record, counts update, and default is unwritten. Desktop toolbar including result feedback is below 180px; desktop/mobile screenshots inspected. Review found no material bugs. Live library GET200 confirms selector/default after idle reload.
