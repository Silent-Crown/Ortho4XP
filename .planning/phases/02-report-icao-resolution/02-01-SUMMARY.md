---
phase: 02-report-icao-resolution
plan: 01
subsystem: cli-report
tags: [cli, icao, mcp, report, tracer]
status: complete
requires: []
provides:
  - O4_ICAO_Utils.resolve_icao
  - O4_ICAO_Utils.get_server_url
  - O4_Report_Utils.read_cfg
  - O4_Report_Utils.tile_status
  - O4_Report_Utils.report_coverage
  - "CLI: report coverage --icao"
  - "config var: mcp_aviation_server_url"
  - "pytest harness (tests/conftest.py)"
affects:
  - src/O4_CLI_Utils.py
  - src/O4_Cfg_Vars.py
tech-stack:
  added: [pytest==9.1.1]
  patterns: [hand-rolled-mcp-http-client, plain-text-cfg-reader, argparse-nested-subparsers]
key-files:
  created:
    - src/O4_ICAO_Utils.py
    - src/O4_Report_Utils.py
    - tests/conftest.py
    - tests/test_icao.py
    - tests/test_coverage.py
    - requirements-dev.txt
  modified:
    - src/O4_CLI_Utils.py
    - src/O4_Cfg_Vars.py
decisions:
  - "Config var added to cfg_app_vars only (option b), not list_app_vars, to avoid shifting the GUI folder-picker rows (gui_app_vars_long = list_app_vars[-3:])."
  - "Resolver is requests-only (D-02); no MCP SDK, no new runtime dependency."
  - "report_coverage handles the containing tile only this plan; 3x3 block + distinct error messages deferred to Plan 02/03."
metrics:
  duration: ~15m
  completed: 2026-08-24
actuals:
  tokens: 13000
  tasks: 2
  commits: 3
---

# Phase 2 Plan 01: Report + ICAO Resolution Tracer Summary

`report coverage --icao <CODE>` works end-to-end: argv → argparse `report` subtree →
hand-rolled MCP-over-HTTP resolver (`requests`-only streamable-HTTP handshake + SSE parse) →
floor to containing tile → D-05 `tile_status` predicate → printed built/partial/missing line,
all proven against canned server bodies and a fixture tile (13 tests, <0.5s, no live server).

## What was built

- **`src/O4_ICAO_Utils.py`** — `resolve_icao(ident, base_url, timeout=10.0)` does the
  streamable-HTTP handshake (initialize → capture `Mcp-Session-Id` → `notifications/initialized`
  → `tools/call get_airport_details`), parses SSE or plain-JSON bodies (`_parse_body`), rejects
  empty/over-10-char idents before any HTTP call, validates coords are finite and in range, and
  fails loud (`AviationServerUnreachable` / `ICAONotFound`) — never returns a coordinate on a
  failure path. `get_server_url()` reads `mcp_aviation_server_url` from `Ortho4XP.cfg` with the
  declared default as fallback (lazy imports; no O4_Config_Utils).
- **`src/O4_Report_Utils.py`** — `read_cfg` (plain-text key=value parser, no exec/eval),
  `tile_status` (D-05 predicate; built requires non-empty DSF AND non-empty `textures/`, else
  partial), `report_coverage` (containing tile only). FNAMES-only paths, read-only.
- **`src/O4_CLI_Utils.py`** — nested `report` subcommand (`tiles`/`coverage`/`health`);
  `coverage --icao` routes through `run_and_report`; `tiles`/`health` raise NotImplementedError
  (bodies land in Plan 03) so `--help` lists the full surface.
- **`src/O4_Cfg_Vars.py`** — `mcp_aviation_server_url` declared in `cfg_app_vars` only.
- **Test harness** — `tests/conftest.py` (src on path, `make_tile` factory, canned SSE/JSON
  bodies, `FakeResponse`), `tests/test_icao.py`, `tests/test_coverage.py`; `requirements-dev.txt`
  pins `pytest==9.1.1`.

## Verification

- `venv/Scripts/python -m pytest tests/ -q` → 13 passed.
- `python src/O4_ICAO_Utils.py` / `python src/O4_Report_Utils.py` self-checks pass.
- Neither new module imports `O4_Config_Utils` (grep clean).
- `build_parser().parse_args(["report","coverage","--icao","KJFK"])` → command=report,
  report_cmd=coverage, icao=KJFK.
- **Deferred (end-of-phase UAT):** live smoke against a running `mcp_aviation_server`
  (`docker compose --profile http up -d`) — the exact FastMCP 3.1 SSE envelope is the A2
  backstop truth, confirmed against canned bodies here.

## Deviations from Plan

None — plan executed as written. (Plan already documented its own RESEARCH deviations from
CONTEXT: `tools/call get_airport_details` instead of the non-existent `airport://` resource,
and the `Ortho4XP_<latlon>.cfg` filename — both honored.)

## Known Stubs

- `report tiles` and `report health` raise `NotImplementedError` — intentional; parser surface
  is complete for `--help`, bodies land in Plan 03 (per plan).

## Self-Check: PASSED
- src/O4_ICAO_Utils.py, src/O4_Report_Utils.py, tests/conftest.py, tests/test_icao.py,
  tests/test_coverage.py, requirements-dev.txt — all present.
- Commits 0ea437d, 651a509 present in git log.
