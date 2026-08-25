---
phase: 02-report-icao-resolution
plan: 02
subsystem: cli-report
tags: [cli, icao, mcp, report, coverage]
status: complete
requires:
  - O4_ICAO_Utils.resolve_icao
  - O4_Report_Utils.tile_status
  - O4_Report_Utils.report_coverage
provides:
  - O4_Report_Utils.coverage_tiles
  - "resolver 3-way error taxonomy (AviationServerUnreachable / ICAONotFound)"
  - "report coverage: full 3x3 block + clean stderr exit"
affects:
  - src/O4_Report_Utils.py
tech-stack:
  added: []
  patterns: [inner-code-error-classification, floor-then-3x3-neighbor-block]
key-files:
  created: []
  modified:
    - src/O4_Report_Utils.py
    - tests/test_icao.py
    - tests/test_coverage.py
decisions:
  - "resolve_icao's inner-code classification already shipped in Plan 01 (ahead of plan); Task 1 was tests-only to lock the D-04 contract."
  - "Off-grid neighbors are skipped (not raised, not wrapped) per planner_assumptions; antimeridian/pole wraparound deferred to v1.x."
  - "report_coverage catches the two resolver exceptions and does single-line stderr + sys.exit(1), rather than letting them propagate to run_and_report (which prints a full traceback)."
metrics:
  duration: ~10m
  completed: 2026-08-24
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
---

# Phase 2 Plan 02: Report + ICAO Resolution Summary

Completes BUILD-01's three-way failure taxonomy and grows `report coverage` from the
containing tile to the full containing+8-neighbor 3x3 block (D-11), each tile labeled
built/partial/missing by the shared D-05 predicate. Failure modes fail loud with distinct,
specific, non-zero-exit messages — never a silent or wrong coordinate.

## What was built

- **`src/O4_Report_Utils.py`** — `coverage_tiles(lat, lon)` yields the containing tile plus
  its 8 neighbors after flooring via `O4_CLI_Utils.parse_lat`/`parse_lon`, skipping any
  neighbor that floors outside `[-90,89] x [-180,179]`. `report_coverage(icao)` now resolves
  once, prints the aligned 3x3 built/partial/missing table, and catches
  `AviationServerUnreachable`/`ICAONotFound` -> single-line stderr + `sys.exit(1)` (no
  traceback, no tile rows, no coordinate). Still read-only, FNAMES-only paths.
- **Resolver taxonomy (already present from Plan 01, test-locked here)** — inner-payload
  `code` branching: `AIRPORT_DETAILS_ERROR` -> `ICAONotFound("ICAO <CODE> not found")`;
  `SIM_DB_UNAVAILABLE`/other server code and top-level JSON-RPC `error` ->
  `AviationServerUnreachable` with wording distinct from the connection-refused message. Never
  branches on `isError` (RESEARCH correction, T-02-06 spoofing control).
- **Tests** — `tests/test_icao.py`: `test_resolve_unknown_icao`, `test_resolve_db_unavailable`,
  `test_resolve_jsonrpc_error`, `test_resolve_ident_too_long`,
  `test_resolve_isError_false_but_notfound`. `tests/test_coverage.py`: `test_coverage_block`,
  `test_coverage_unreachable_exit`, `test_coverage_unknown_exit`, `test_coverage_skips_offgrid`,
  `test_coverage_tiles_block`.

## Verification

- `venv/Scripts/python -m pytest tests/ -q` -> 23 passed (<0.3s, no live server).
- `python src/O4_Report_Utils.py` self-check passes.
- Dispatch branch in `O4_CLI_Utils.py` already routes `report coverage` through
  `run_and_report(RPT.report_coverage, args.icao)` — no change needed (listed in
  files_modified but confirmed already correct).
- **Deferred (end-of-phase UAT):** live smoke against a running `mcp_aviation_server`
  (`docker compose --profile http up -d`): `report coverage --icao KJFK` -> 3x3 table exit 0;
  `--icao ZZZZ` -> "not found" stderr, non-zero; server stopped -> "unreachable" stderr,
  non-zero.

## Deviations from Plan

- **[Rule scope] Task 1 was tests-only.** The resolver's inner-`code` three-way classification
  had already landed in Plan 01 (Plan 01 shipped slightly ahead of its stated scope). The
  RED gate passed immediately; Task 1 added the missing tests to lock the D-04 contract rather
  than re-implementing. No source change to `O4_ICAO_Utils.py`.
- **`src/O4_CLI_Utils.py`** listed in `files_modified` but unchanged — the dispatch branch was
  already correct from Plan 01.

## TDD Gate Compliance

Task 1's RED gate passed without a failing state because the implementation pre-existed from
Plan 01 — tests were added to pin behavior, not to drive new code. Task 2 followed
RED (new `coverage_tiles`/3x3 behavior) -> GREEN normally.

## Known Stubs

- `report tiles` and `report health` still raise `NotImplementedError` — bodies land in
  Plan 03 (unchanged from Plan 01; parser surface complete for `--help`).

## Self-Check: PASSED
- src/O4_Report_Utils.py, tests/test_icao.py, tests/test_coverage.py — all present.
- Commits 60bc191, 102576e present in git log.
