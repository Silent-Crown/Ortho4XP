---
phase: 03-icao-driven-build
plan: 02
subsystem: cli-icao
tags: [icao, batch-build, bugfix, tdd]
requires: [O4_ICAO_Utils.resolve_icao, O4_CLI_Utils.run_batch_build]
provides: ["G-03-7 closed: real not-found code skips-and-continues in batch"]
affects: [src/O4_ICAO_Utils.py, tests/conftest.py, tests/test_build_icao.py]
tech-stack:
  added: []
  patterns: [tdd-red-green]
key-files:
  created: []
  modified:
    - src/O4_ICAO_Utils.py
    - tests/conftest.py
    - tests/test_build_icao.py
decisions:
  - "Match both AIRPORT_NOT_FOUND (real) and AIRPORT_DETAILS_ERROR (assumed) as ICAONotFound; other codes still abort (fail-closed, T-03-03 accept)."
metrics:
  duration: ~6m
  completed: 2026-08-25
status: complete
actuals:
  tokens: 2000
  tasks: 2
  commits: 2
gap_closure: true
gap_ids: [G-03-7]
requirements: [BUILD-03, BUILD-04]
---

# Phase 03 Plan 02: G-03-7 Not-Found Code Fix Summary

`resolve_icao` now classifies the real mcp_aviation_server unknown-ICAO code
`AIRPORT_NOT_FOUND` as `ICAONotFound`, so one bad ICAO in a batch is skipped
(D-10) instead of aborting the whole run via the `AviationServerUnreachable`
branch.

## What changed

- **src/O4_ICAO_Utils.py** — `code == "AIRPORT_DETAILS_ERROR"` widened to
  `code in ("AIRPORT_NOT_FOUND", "AIRPORT_DETAILS_ERROR")`.
- **tests/conftest.py** — not-found fixture `code` now the real server string
  `"AIRPORT_NOT_FOUND"`, so a regression fails a test again.
- **tests/test_build_icao.py** — new
  `test_batch_unknown_icao_real_resolver_skips_and_summarizes`: drives the real
  resolver via a monkeypatched `requests.Session.post`, proves `ZZZZ,KJFK`
  builds `(40,-74)`, exits 1, and prints `1/2 ICAOs resolved`.

## TDD gates

- RED: `test(03-02)` f8864c9 — fixture change flipped 3 existing test_icao.py
  tests plus the new batch test to failing against unpatched source (exactly
  the expected 4). Confirmed G-03-7 reproduced, not a no-op.
- GREEN: `fix(03-02)` 6f2609c — full suite `54 passed`.

## Test results

- RED: `4 failed, 27 passed` (expected: test_resolve_not_found,
  test_resolve_unknown_icao, test_resolve_isError_false_but_notfound,
  test_batch_unknown_icao_real_resolver_skips_and_summarizes).
- GREEN: `54 passed`.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- f8864c9 test(03-02): reproduce G-03-7 with real not-found code (RED)
- 6f2609c fix(03-02): classify AIRPORT_NOT_FOUND as ICAONotFound (GREEN)

## Self-Check: PASSED

- src/O4_ICAO_Utils.py, tests/conftest.py, tests/test_build_icao.py — all present.
- Commits f8864c9, 6f2609c — both in git log.
