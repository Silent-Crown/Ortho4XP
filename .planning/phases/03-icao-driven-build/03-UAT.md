---
status: complete
phase: 03-icao-driven-build
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-08-25T00:00:00Z
updated: 2026-08-25T02:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Build help lists new flags
expected: `Ortho4XP.py build --help` lists --icao, --icao-file, and --radius options.
result: pass

### 2. Build a single ICAO
expected: `build --icao KJFK` resolves the airport and builds its tile(s) with no error; exit 0.
result: pass

### 3. Build a comma-separated ICAO list
expected: `build --icao KJFK,KLGA` resolves both, dedupes tiles, builds them in sorted order, ends with a summary line.
result: pass

### 4. Build from an ICAO file
expected: `build --icao-file codes.txt` (one ICAO per line, blank/# lines ignored) builds all listed airports' tiles.
result: pass

### 5. Radius expands to neighbor tiles
expected: `build --icao KJFK --radius 1` builds the airport tile plus its surrounding Chebyshev square (up to 9 tiles), deduped.
result: skipped
reason: "Too slow to run 9 full builds; neighbor_tiles expansion covered by unit tests."

### 6. Argument validation errors
expected: Missing source, only one positional, --radius without an ICAO source, or a negative radius each print a clear error and exit 2.
result: pass

### 7. Unknown ICAO skips and summarizes
expected: An unknown code (e.g. `--icao ZZZZ,KJFK`) skips the bad one, still builds the good one, summary notes the skip, exit 1.
result: pass
retested: "2026-08-25 after G-03-7 fix: build --icao ZZZZ,KJFK printed 'skipping ZZZZ: ICAO ZZZZ not found', built tile +40-074 (KJFK) through all 4 stages incl. DSF, and ended 'batch: 1/2 ICAOs resolved, 1 tiles built, 0 failed'. Skip-and-continue confirmed end-to-end."

### 8. Server unreachable aborts before building
expected: When the aviation server is unreachable, the run aborts before any tile is built with a clear message; no partial builds.
result: pass

### 9. Legacy positional build still works
expected: `build 40 -74` (and the raw `Ortho4XP.py 40 -74 [provider zl]` form) still builds via the original path, unchanged.
result: pass

## Summary

total: 9
passed: 8
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

- gap_id: G-03-7
  truth: "An unknown ICAO in a batch is skipped (D-10); resolvable codes still build; a summary reports the skip; exit 1."
  status: closed
  closed_by: 03-02
  closed_at: 2026-08-25
  reason: "User reported: build --icao ZZZZ,KJFK aborted on ZZZZ (AIRPORT_NOT_FOUND) — KJFK never built, no batch summary line. Unknown-ICAO error is treated as fatal instead of skip-and-continue."
  severity: major
  test: 7
  root_cause: "resolve_icao maps only code=='AIRPORT_DETAILS_ERROR' to ICAONotFound; the real mcp_aviation_server returns code=='AIRPORT_NOT_FOUND' for an unknown ICAO, which falls through to `raise AviationServerUnreachable` (the D-11 abort path) instead of the D-10 skip path. Tests stayed green because conftest.py's not-found fixture hard-codes AIRPORT_DETAILS_ERROR — the mock encodes the bug."
  artifacts:
    - path: "src/O4_ICAO_Utils.py"
      issue: "lines 106-112: not-found classified by wrong code string ('AIRPORT_DETAILS_ERROR'); real code 'AIRPORT_NOT_FOUND' falls through to AviationServerUnreachable"
    - path: "tests/conftest.py"
      issue: "lines 41-45: not-found fixture uses 'AIRPORT_DETAILS_ERROR', masking the mismatch"
  missing:
    - "resolve_icao must treat the server's real unknown-airport code ('AIRPORT_NOT_FOUND') as ICAONotFound, keeping other/unknown codes on the AviationServerUnreachable abort path"
    - "Update conftest.py not-found fixture to the server's real code string so the test catches this"
  debug_session: ""

## Deferred Follow-Ups

- test: 3
  idea: "Default-value builds (no provider/zl) spam 'Unknown provider or it has no data' lines per node — an eyesore. Suppress or summarize when no imagery provider is configured."
  deferred_at: 2026-08-25
