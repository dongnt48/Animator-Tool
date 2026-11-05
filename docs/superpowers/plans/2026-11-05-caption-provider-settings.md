# Caption model and API key settings

User: provide a place to configure the caption model and API key.

Design: add model/password fields and Save API button inside existing compact toolbar options. Store local configuration in ignored SQLite metadata. Empty password preserves current key; never return saved key to browser. Saved key takes priority over existing XAH_API_KEY environment/.env fallback; default model stays gemini-3.8-flash. Endpoint remains XAH. Validate model/key and keep invalid saves atomic. Resolve credentials server-side once per batch, use sanitized errors and never include credentials in draft/media responses. No external provider calls for development validation.

- [x] Red tests for defaults/fallback, persistence, secret non-disclosure, blank-key retention, validation and actual request model/header.
- [x] Store/config helper, provider settings API and caption client model selection.
- [x] UI fields/load/save with password clearing and API availability update.
- [x] Full tests, review and safe reload/live GET verification.

Verification: 128 tests pass, including 6 provider tests with fake credentials/network blocked and a local Playwright save/reload/model-use test. Review found no material defects. Live root/provider GET returned200 after idle reload and exposed only public status fields. No live provider requests or real key changes were performed.
