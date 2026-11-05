# User-controlled caption hashtags

User: stop automatic AI hashtag generation and provide hashtag settings.

Design: persist one user-defined hashtag set in SQLite metadata, empty by default. The compact toolbar's options contain a hashtag field/save button. Rewrite also saves changed field content and freezes the resulting hashtag set for all batches. AI is instructed not to create/preserve tags; output tags are removed and only user-configured tags appended server-side. Existing captions/drafts are not modified retroactively; explicit caption editing/saving remains untouched. Validate length/syntax, normalize optional hash prefix and comma/newline separators, deduplicate Unicode-aware. Settings GET does not call providers.

- [x] Red tests for settings persistence/validation, AI prompt and output sanitation, exact custom suffix and batch snapshot.
- [x] Implement hashtag helper, store methods/settings API and rewrite integration.
- [x] Add compact settings UI and freeze/saving behavior; update affected tests/docs.
- [x] Full suite, review and idle reload/live verification.

Verification: 121 tests pass, including seven settings/formatting tests with external provider blocked and a local Playwright UI test for persistence, clearing and autosaving. Review found no material bugs. Live settings API/root returned200 after idle reload, settings default empty. Existing saved captions/drafts were not migrated or rewritten.
