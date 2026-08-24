---
status: testing
phase: 02-report-icao-resolution
source: [02-VERIFICATION.md]
started: 2026-08-24T00:00:00Z
updated: 2026-08-24T00:00:00Z
---

## Current Test

number: 1
name: Live FastMCP envelope — report coverage --icao KJFK
expected: |
  Prints a 3x3 built/partial/missing table and exits 0 — confirms the real FastMCP 3.1
  tools/call envelope (result.content[0].text) matches the canned-body assumption
  (Plan 01 backstop truth).
awaiting: user response

## Tests

### 1. Live FastMCP envelope — report coverage --icao KJFK
expected: Start mcp_aviation_server in HTTP mode (cd ../mcp_aviation_server && docker compose --profile http up -d), then run `venv/Scripts/python Ortho4XP.py report coverage --icao KJFK`. Prints a 3x3 built/partial/missing table and exits 0 — confirms the real FastMCP 3.1 tools/call envelope matches the canned-body assumption.
result: [pending]

### 2. Live failure taxonomy — unknown ICAO and server-stopped
expected: With the server up, run `Ortho4XP.py report coverage --icao ZZZZ`; then stop the server and rerun `--icao KJFK`. ZZZZ -> "ICAO ZZZZ not found" on stderr, non-zero exit. Server-stopped -> "unreachable" message on stderr, non-zero exit. No coordinate or tile rows printed on either failure.
result: [pending]

### 3. Real-tree smoke — report tiles and report health
expected: Run `Ortho4XP.py report tiles` and `Ortho4XP.py report health` against the real Tiles/ tree. Each prints an aligned table (or the clean "no tiles built" / "no issues" line) and exits 0; neither mutates the tree.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
