---
phase: 03-icao-driven-build
plan: 01
subsystem: cli
tags: [cli, argparse, icao, batch-build]
requires: [O4_ICAO_Utils.resolve_icao, O4_CLI_Utils.run_build, O4_CLI_Utils.parse_lat, O4_CLI_Utils.parse_lon]
provides: [build --icao, build --icao-file, build --radius, neighbor_tiles, parse_icao_args, run_batch_build]
affects: [src/O4_CLI_Utils.py]
tech-stack:
  added: []
  patterns: [lazy-import-O4_ICAO_Utils, resolve-all-then-build, mutually-exclusive-argparse-group]
key-files:
  created:
    - tests/test_build_icao.py
  modified:
    - src/O4_CLI_Utils.py
decisions:
  - D-07 antimeridian wrap via modular longitude; D-08 pole skip (latitude never wraps)
  - D-09 second build-side neighbor generator (neighbor_tiles) rather than reusing report coverage_tiles
  - D-10 unknown ICAO skip-and-summarize; D-11 server-unreachable aborts before any build
  - D-13 binary 0/1 exit; D-15 dedupe to unique tile set; D-17 (lat,lon)-sorted build order
metrics:
  duration: ~20m
  completed: 2026-08-25
status: complete
actuals:
  tokens: 5000
  tasks: 3
  commits: 3
---

# Phase 3 Plan 01: ICAO-Driven Batch Build Summary

Extended the `build` subcommand to take `--icao` (one code or comma list), `--icao-file`
(newline list), and `--radius N` (Chebyshev square of whole tiles), reusing the Phase 2
resolver and Phase 1 `run_build` — batch orchestration only, no pipeline or resolver changes.

## What Was Built

- **Parser**: `build` positionals `lat`/`lon` now `nargs="?"`; `--icao`/`--icao-file` in a
  mutually-exclusive group; `--radius` int default 0. `_validate_build` enforces exactly one
  source, both-or-neither positionals, `--radius` requires an ICAO source, non-negative radius
  (all via `parser.error` → exit 2).
- **`neighbor_tiles(lat, lon, radius=0)`**: floors to a base tile, walks the Chebyshev square,
  wraps longitude across the antimeridian with `((lon+180)%360)-180` (D-07), skips latitudes
  past ±90 (D-08), returns a deduped `sorted()` list (D-15/D-17).
- **`parse_icao_args(icao, icao_file)`**: comma split or file read; blank and `#` lines skipped;
  missing/unreadable file and empty list both exit 1 with one clean stderr line (T-03-01).
- **`run_batch_build(idents, radius, provider, zl)`**: resolves ALL idents first (so an abort
  leaves no partial builds), `ICAONotFound`→skip (D-10), `AviationServerUnreachable`→abort before
  any build (D-11), expands each coord through `neighbor_tiles` into one deduped set, builds in
  sorted order, a per-tile build error is logged and skipped (D-12), exit 1 if any ICAO failed to
  resolve or any tile failed to build else 0 (D-13), plus an end-of-run summary line (D-14).
- **dispatch**: retains the parser object, validates, routes an ICAO source to `run_batch_build`
  and the positional path to `run_build` (unchanged). Raw-argv legacy `lat lon [provider zl]`
  sniff untouched.

## How to Verify

- `venv/Scripts/python.exe -m pytest tests/ -q` → 53 passed.
- `venv/Scripts/python.exe src/O4_CLI_Utils.py` → `O4_CLI_Utils self-check OK`.
- `venv/Scripts/python.exe Ortho4XP.py build --help` → lists `--icao`, `--icao-file`, `--radius`.
- `git diff --stat src/O4_Report_Utils.py` → empty (D-09: `coverage_tiles` untouched).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test correctness] Legacy positional test expectation**
- **Found during:** Task 1 verification.
- **Issue:** The `build 40 -74` positional path forwards the raw argv strings to `run_build`
  (which floors them internally); the initial test asserted pre-floored ints `(40, -74)`.
- **Fix:** Asserted the actual forwarded strings `("40", "-74")`; real flooring behavior is
  correct and unchanged.
- **Files modified:** tests/test_build_icao.py
- **Commit:** f0e0918

## TDD Gate Compliance

Tasks 1–3 all carry `tdd="true"` and touch a single module + single test file with tightly
coupled surfaces. Committed as one RED test commit (`test(03-01)`, 1457f9d) followed by one
GREEN implementation commit (`feat(03-01)`, f0e0918) rather than six per-task gate commits.
RED confirmed failing (16 failed / 2 passed) before implementation; GREEN is full-suite green.

## Known Stubs

None. All flags are wired to real orchestration; no placeholder data paths.

## Self-Check: PASSED
- src/O4_CLI_Utils.py — FOUND (modified)
- tests/test_build_icao.py — FOUND (created)
- Commit 1457f9d (test) — FOUND
- Commit f0e0918 (feat) — FOUND
