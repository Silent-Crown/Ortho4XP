---
phase: 01-cli-dispatch-compatibility
reviewed: 2026-08-24T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - Ortho4XP.py
  - src/O4_CLI_Utils.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-24
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

The CLI dispatch refactor is sound. I traced every argv path: legacy `lat lon [provider zl]`
sniff, the argparse `build` subcommand, `-h`/`--help`, and negative-number coordinates.
Compatibility contracts hold — GUI launch on no args, headless build on args, init block
(directory creation + `initialize_*` provider setup) runs before both branches, and `"Bon vol!"`
prints on success in both GUI and build paths. Legacy usage errors exit 1, argparse usage errors
exit 2, and `SystemExit` correctly passes through `run_and_report` (CLI-03). The negative-number
sniff is correct: `_is_number` accepts `-122` so legacy `47 -122` routes to `run_legacy` before
argparse can misread it, and argparse's own negative-number matcher handles `build 47 -122`.

No BLOCKER-class defects found. One robustness gap (non-finite coordinate inputs violate the
documented `ValueError` contract) and four low-severity notes.

## Warnings

### WR-01: Non-finite coordinates leak `OverflowError`, breaking the documented `:raises ValueError` contract

**File:** `src/O4_CLI_Utils.py:23-30` (with `_is_number` at `107-113`)
**Issue:** `parse_and_floor_coord` wraps only `float(value)` in the `try`. `math.floor(f)` runs
outside it. `_is_number("inf")`, `_is_number("1e400")`, and `_is_number("nan")` all return `True`
(confirmed: `float("1e400") == inf`), so a legacy call like `Ortho4XP.py 47 inf` or
`build 47 1e400` reaches `math.floor`, which raises `OverflowError` for `inf`/`1e400` (confirmed)
and `ValueError` with a low-level message for `nan`. The docstring promises `:raises ValueError:
if not a number or out of [lo, hi]`, but `OverflowError` escapes that contract and reaches
`run_and_report`, which dumps a Python traceback instead of the clean
`"lon inf out of range"` style message the function is designed to give. It does not crash the
process uncaught (`run_and_report` catches `Exception` → exit 1), so impact is a confusing error
message for bad input, not data loss.
**Fix:**
```python
try:
    f = float(value)
except (ValueError, TypeError):
    raise ValueError(f"{name} must be a number, got {value!r}")
if not math.isfinite(f):
    raise ValueError(f"{name} must be a finite number, got {value!r}")
n = math.floor(f)
```
Optionally add one self-check line at `__main__`: `try: parse_lat("inf")` / `except ValueError: pass`.

## Info

### IN-01: `build` subcommand rejects exotic negative-coordinate notations that the legacy path accepts

**File:** `src/O4_CLI_Utils.py:53-54, 147`
**Issue:** argparse's negative-number matcher only recognizes `^-\d+$|^-\d*\.\d+$`. So
`Ortho4XP.py build 47 -1e2` fails at argparse ("expected one argument" / "unrecognized
arguments"), while the legacy form `Ortho4XP.py 47 -1e2` passes `_is_number` and builds
(floors to -100). Same input, two different outcomes depending on whether `build` is typed.
Minor surprise, not a correctness bug.
**Fix:** Document that `build` coordinates should use plain decimal notation, or accept the
inconsistency — legacy tolerance was always looser.

### IN-02: Coordinate validation errors in the `build` subcommand surface as tracebacks (exit 1), not argparse usage errors (exit 2)

**File:** `src/O4_CLI_Utils.py:53-54, 76-77, 150-152`
**Issue:** `lat`/`lon` are plain string positionals; validation happens later inside `run_build`
via `parse_lat`/`parse_lon`, whose `ValueError` is caught by `run_and_report` and printed as a
traceback with exit 1. So `build 999 0` yields a Python traceback rather than a clean
`argparse` message. This matches the CLI-03 "failures print a traceback, exit 1" decision, so
it is intentional, but a friendlier path exists.
**Fix (optional):** Set `type=parse_lat` / `type=parse_lon` on the positionals so argparse
converts and reports invalid coordinates as usage errors (exit 2) with a clean message. Leave
`run_build` parsing for the legacy path.

### IN-03: Dead `if args.command == "build"` guard with no `else`

**File:** `src/O4_CLI_Utils.py:151-152`
**Issue:** `subparsers` is `required=True` with only `build` registered, so any other token
already exits 2 before this line. The `if` is therefore always true when reached, and an
unmatched command would silently no-op (exit 0). Harmless today; a trap if a future subcommand
is added and someone forgets the dispatch branch.
**Fix:** Either drop the `if` (call `run_build` directly) or add an explicit
`else: parser.error(...)` when more subcommands land.

### IN-04: Legacy 2-arg path lost the friendly "could not read tile config file" message

**File:** `src/O4_CLI_Utils.py:78`, vs removed block in `Ortho4XP.py`
**Issue:** The old inline code caught a failing `CFG.Tile(lat, lon, '')` and printed
`"ERROR: could not read tile config file."` then exit 0. Now a missing/broken per-tile config
raises out of `CFG.Tile`, is caught by `run_and_report`, and prints a raw traceback with exit 1.
This is consistent with the CLI-03 "failures exit non-zero + traceback" decision (and exit 1 for
a real error is arguably more correct than the old exit 0), so recorded as Info only.
**Fix (optional):** If a clean message is desired for the common "no tile config yet" case, catch
that specific condition in `run_build` and emit a one-line hint before exiting.

---

_Reviewed: 2026-08-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
