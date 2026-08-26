---
phase: quick
plan: 260826-f6k
subsystem: cli
tags: [cli, argparse, build]
status: complete
dependency-graph:
  requires: []
  provides: [cli-high-zl-flag, cli-cover-zl-flag]
  affects: [src/O4_CLI_Utils.py]
tech-stack:
  added: []
  patterns: ["argparse store_true / typed int flag mirroring --provider/--zl"]
key-files:
  created: []
  modified:
    - src/O4_CLI_Utils.py
decisions: []
metrics:
  duration: ~5m
  completed: 2026-08-26
actuals:
  tokens: 1200
  tasks: 1
  commits: 1
---

# Phase quick Plan 260826-f6k: Add --high-zl and --cover-zl flags to the CLI Summary

Added `--high-zl` (store_true) and `--cover-zl` (int) flags to the `build` subcommand,
threaded through `run_build`/`run_batch_build`/`dispatch` exactly like the existing
`--provider`/`--zl` pattern.

## Changes

- `build_parser()`: added `--high-zl` (`action="store_true"`, default False) and
  `--cover-zl` (`type=int`, default None) to the `build` subparser.
- `run_build(...)`: new `high_zl=False, cover_zl=None` params appended at end of
  signature; sets `tile.cover_airports_with_highres = "ICAO"` when `high_zl` is True,
  and `tile.cover_zl = cover_zl` when not None.
- `run_batch_build(...)`: same two params appended, passed through to `run_build` in
  the tile loop.
- `dispatch()`: both `build` call sites (ICAO/batch and single-tile) now pass
  `args.high_zl, args.cover_zl` through `run_and_report`.
- Self-check block: added assertions that `--high-zl --cover-zl 19` parses to
  `high_zl=True, cover_zl=19`, and that a bare `build 47 -122` defaults to
  `high_zl=False, cover_zl=None`.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

```
O4_CLI_Utils self-check OK
```

## Verification

- `venv\Scripts\python.exe src\O4_CLI_Utils.py` prints `O4_CLI_Utils self-check OK` — confirmed above.
- `git diff --stat` for the commit shows only `src/O4_CLI_Utils.py` changed (27 lines: 22 insertions, 5 deletions). `O4_DSF_Utils.py` and `O4_Cfg_Vars.py` untouched.

## Self-Check: PASSED

- FOUND: src/O4_CLI_Utils.py
- FOUND: commit ea2fc73
