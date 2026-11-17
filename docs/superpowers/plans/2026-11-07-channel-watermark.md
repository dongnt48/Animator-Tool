# Channel Watermark Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline.

**Goal:** Save a channel name and burn a translucent central watermark into newly rendered videos.
**Architecture:** Extend saved animation settings with `channel_name`, snapshot it for every render flow, and overlay a shared Remotion component over either video composition. Empty text disables the overlay. Existing exports stay unchanged.
**Tech Stack:** Flask, SQLite metadata, React/Remotion, Playwright.
**Spec:** User chose a translucent watermark in the middle of the video on 2026-11-07. Use the existing animation configuration form; no new dependencies. Builder choices: maximum 80 characters, reject line/control characters, 18% opacity, adaptive centered text throughout playback.

## Global Constraints
- Preserve login sessions, records and existing exported files.
- Legacy rendering must not start AI work.
- Apply saved channel branding to download/render, batch and AI flows.

## Review Focus
- Blank name produces no watermark.
- Vietnamese and punctuation remain literal text.
- Reject non-string, multiline and oversized names.
- Both portrait and landscape names stay inside the frame.
- Failed settings save does not overwrite saved branding.

### Task 1: Persist and snapshot branding
- [x] Add API tests for trim, persistence, validation, and render snapshots; run and observe failure.
- [x] Extend animation settings and existing form with channel name; include saved branding in all render configurations.
- [x] Run animation tests and settings UI check.

### Task 2: Render shared watermark
- [x] Test renderer props with a supplied channel name; run and observe missing watermark prop.
- [x] Add shared center overlay at root for both compositions, responsive font sizing and safe text rendering.
- [x] Run Python tests, TypeScript check and render a temporary test still for visual verification.
- [x] Document feature, review diff, restart idle server and verify it responds.
