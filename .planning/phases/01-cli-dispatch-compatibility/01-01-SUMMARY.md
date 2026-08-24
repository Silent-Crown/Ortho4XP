---
phase: 01-cli-dispatch-compatibility
plan: 01
subsystem: cli
tags: [cli, argparse, dispatch, refactor]
status: complete
requires: []
provides:
  - O4_CLI_Utils.dispatch
  - O4_CLI_Utils.run_build
  - O4_CLI_Utils.parse_lat
  - O4_CLI_Utils.parse_lon
affects:
  - Ortho4XP.py entry point dispatch
tech-stack:
  added: []
  patterns:
    - "stdlib argparse subcommands with pre-argparse raw-argv sniff"
    - "math.floor(float()) coordinate flooring (replaces int() truncation)"
    - "traceback.print_exc + sys.exit(1) error wrapper (replaces bare except)"
    - "lazy CFG/VMAP/MESH/MASK/TILE imports inside run_build to preserve CFG-import-last"
key-files:
  created:
    - src/O4_CLI_Utils.py
  modified:
    - Ortho4XP.py
decisions:
  - "Legacy usage errors now exit 1 (was 0); argparse usage errors keep exit 2"
  - "lat/lon taken as strings by argparse so one shared floor/validate helper serves both paths"
metrics:
  duration: ~10m
  completed: 2026-08-24
actuals:
  tokens: 1500
  tasks: 2
  commits: 3
---

# Phase 1 Plan 01: CLI Dispatch & Compatibility Summary

Migrated `Ortho4XP.py` argv dispatch to a stdlib-argparse CLI in new `src/O4_CLI_Utils.py`, adding a `build` subcommand with `--help` discoverability while preserving no-arg GUI launch and legacy `lat lon [provider zl]` builds byte-for-byte; fixed coordinate flooring (`math.floor` not `int()`) and replaced the `except: print("Crash!")` catch-all with a real traceback + non-zero exit.

## What Was Built

- **`src/O4_CLI_Utils.py` (new):** `parse_and_floor_coord`/`parse_lat`/`parse_lon` (floor + range-validate, CLI-04), `build_parser` (one `build` subcommand, CLI-01), `run_build` (lazy build-module imports + 4-stage pipeline), `run_and_report` (CLI-03 wrapper), `_is_number`/`run_legacy` + `cmd_line` (CLI-02 legacy path), `dispatch` (raw-argv sniff before argparse). Includes an `if __name__ == "__main__"` assert-based self-check (no test framework in this repo).
- **`Ortho4XP.py` (modified):** `else:` branch now `import O4_CLI_Utils as CLI; CLI.dispatch(sys.argv[1:])`. Removed inline legacy parsing, the `cmd_line` assignment, and the bare-except crash handler. No-arg GUI branch and the entire pre-dispatch init block (Utils_dir check, makedirs loop, `IMG.initialize_*`) left untouched.

## Requirements Completed

- CLI-01: `Ortho4XP.py --help` / `build --help` document every command and flag.
- CLI-02: no args -> GUI (unchanged); `lat lon [provider zl]` -> legacy build via pre-argparse sniff.
- CLI-03: failures print full traceback to stderr and exit 1; catch-all silent handler removed.
- CLI-04: negative/decimal coords floor to the containing tile via one shared helper.

## Verification

Scriptable matrix (all pass):
- `python src/O4_CLI_Utils.py` -> self-check OK (exit 0).
- `python Ortho4XP.py --help` / `build --help` -> exit 0, list `lat`/`lon`/`--provider`/`--zl`.
- `dispatch(['-0.5','47.5'])` routes to `run_legacy`; `dispatch(['build','47','-122'])` routes to argparse with `provider=None, zl=None`.
- `dispatch(['47','-122','BI','16'])` -> `run_legacy` with `provider='BI', zl=16` (no argparse usage text).
- `python Ortho4XP.py build` -> exit 2 (argparse usage). `python Ortho4XP.py build 999 999` -> exit 1 with traceback.
- `parse_lat('47.9')==47`, `parse_lon('-122.1')==-123` (floor semantics).
- Lazy-import: importing `O4_CLI_Utils` does not import `O4_Config_Utils`.

**Human-check only (Tkinter cannot be scripted):** `python Ortho4XP.py` with no args opens the GUI and prints `Bon vol!` on close (CLI-02). Branch preserved byte-for-byte, so no regression expected.

## Deviations from Plan

None - plan executed exactly as written.

## Tracer Feedback Gate

Task 1 is the `type="tracer"` slice. Its automated `<verify>` (self-check, `build --help`, lazy-import assertion) was run end-to-end and passed before expanding into Task 2's legacy path. Auto mode was off, but all tracer verify steps are fully automated commands (no human interaction possible), so they were executed directly rather than surfaced as a human checkpoint.

## Self-Check: PASSED

- src/O4_CLI_Utils.py: FOUND
- Ortho4XP.py (modified): FOUND
- Commit f2b84ba (Task 1): FOUND
- Commit c3ca617 (Task 2): FOUND
