---
phase: 01-cli-dispatch-compatibility
verified: 2026-08-24T00:00:00Z
status: human_needed
score: 7/8 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Running `python Ortho4XP.py` with no arguments launches the Tkinter GUI and prints \"Bon vol!\" after the window closes (CLI-02)."
    test: "Run `venv/Scripts/python.exe Ortho4XP.py` with no arguments."
    expected: "The Tkinter GUI window opens; after closing it, the terminal prints \"Bon vol!\". Process exits cleanly."
    why_human: "Tkinter mainloop cannot be driven headlessly. Code path (Ortho4XP.py lines 48-51) is preserved byte-for-byte and confirmed by reading, but the runtime GUI launch + close + success message cannot be exercised programmatically."
human_verification:
  - test: "Run `venv/Scripts/python.exe Ortho4XP.py` with no arguments."
    expected: "GUI window opens; closing it prints \"Bon vol!\"."
    why_human: "Tkinter GUI cannot be scripted; no-arg branch preserved unchanged in code."
---

# Phase 1: CLI Dispatch & Compatibility Verification Report

**Phase Goal:** Users get a discoverable, argparse-based CLI without any regression to existing invocations or error behavior.
**Verified:** 2026-08-24
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--help` and `build --help` document every command and flag (CLI-01) | ✓ VERIFIED | `--help` lists `{build}`; `build --help` lists `lat`, `lon`, `--provider`, `--zl` with help text. Both exit 0. |
| 2 | No-arg launches Tkinter GUI + prints "Bon vol!" (CLI-02) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Ortho4XP.py:48-51 routes `len(sys.argv)==1` → `GUI.Ortho4XP_GUI().mainloop()` then `print("Bon vol!")`, byte-for-byte unchanged. Tkinter cannot run headlessly — see Human Verification. |
| 3 | Legacy `lat lon [provider zl]` reached via raw-argv sniff before argparse (CLI-02) | ✓ VERIFIED | dispatch() O4_CLI_Utils.py:149 sniff is first statement before `build_parser().parse_args()`. Runtime: `dispatch(['-0.5','47.5'])` → run_build; `dispatch(['build','47','-122'])` → argparse branch. |
| 4 | Negative/decimal coords floor via math.floor, one shared helper (CLI-04) | ✓ VERIFIED | `parse_lat('-0.5')=-1`, `parse_lon('-122.1')=-123`, `parse_lat('47.5')=47`. Both paths call parse_lat/parse_lon (lines 78-79, and run_legacy→run_build). |
| 5 | Out-of-range coords raise a clear specific error | ✓ VERIFIED | Range check O4_CLI_Utils.py:30-31 raises `ValueError(f"{name} {n} out of range [{lo}, {hi}]")`. Self-check asserts `parse_lat('999')` raises. Plus math.isfinite guard (line 27, WR-01 fix). |
| 6 | Failed build prints real traceback + exits non-zero; old catch-all gone (CLI-03) | ✓ VERIFIED | run_and_report() lines 99-105: `traceback.print_exc(file=sys.stderr)` + `sys.exit(1)`, `SystemExit` re-raised. Grep: no `print("Crash` handler remains in codebase. |
| 7 | CFG/VMAP/MESH/MASK/TILE imported lazily inside run_build, never at module top | ✓ VERIFIED | Imports at O4_CLI_Utils.py:72-76 inside run_build(). Runtime assert: importing O4_CLI_Utils does not import O4_Config_Utils. Module top = stdlib only (sys, math, traceback, argparse). |
| 8 | "Bon vol!" message + pre-dispatch init block unchanged | ✓ VERIFIED | Ortho4XP.py:31-51 init block (Utils_dir check, makedirs loop, 4× IMG.initialize_*) and "Bon vol!" print intact. |

**Score:** 7/8 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/O4_CLI_Utils.py` | New CLI module: parse helpers, build_parser, run_build, run_and_report, _is_number, run_legacy, dispatch | ✓ VERIFIED | All 8 functions present + cmd_line constant + `__main__` self-check. Substantive (178 lines), wired via Ortho4XP.py. |
| `Ortho4XP.py` | Entry point delegates `else:` branch to CLI.dispatch; init block preserved | ✓ VERIFIED | Lines 52-54: `import O4_CLI_Utils as CLI; CLI.dispatch(sys.argv[1:])`. `cmd_line =` count in file = 0. |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| Ortho4XP.py else-branch | CLI.dispatch(sys.argv[1:]) | import + call, line 53-54 | ✓ WIRED |
| dispatch() sniff | run_legacy(argv) OR parse_args→run_build | lines 149-154 | ✓ WIRED (runtime-confirmed both routes) |
| run_build() lazy imports | CFG.Tile → VMAP→MESH→MASK→TILE pipeline | lines 72-88 | ✓ WIRED |
| run_and_report() wrapper | both run_legacy and build call sites | lines 150, 154 | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI-01 top help | `Ortho4XP.py --help` | exit 0, lists `build` | ✓ PASS |
| CLI-01 build help | `Ortho4XP.py build --help` | exit 0, lists lat/lon/--provider/--zl | ✓ PASS |
| CLI-03 usage error | `Ortho4XP.py bogus` | exit 2, argparse error | ✓ PASS |
| CLI-04 flooring | `parse_lat('-0.5'),parse_lon('-122.1'),parse_lat('47.5')` | `-1 -123 47` | ✓ PASS |
| Module self-check | `python src/O4_CLI_Utils.py` | "self-check OK", exit 0 | ✓ PASS |
| Lazy import | assert O4_Config_Utils not in sys.modules | passes | ✓ PASS |
| Dispatch routing | monkeypatch run_build, dispatch legacy + build | both routes correct | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLI-01 | 01-01 | Discoverable `--help` for subcommands | ✓ SATISFIED | Truth 1 |
| CLI-02 | 01-01 | No-arg GUI + legacy lat/lon build unchanged | ⚠ NEEDS HUMAN (GUI) / ✓ SATISFIED (legacy) | Truths 2, 3 |
| CLI-03 | 01-01 | Non-zero exit + real error, catch-all removed | ✓ SATISFIED | Truth 6 |
| CLI-04 | 01-01 | floor() not int() truncation | ✓ SATISFIED | Truth 4 |

All 4 phase requirement IDs (CLI-01..04) declared in PLAN frontmatter and mapped to Phase 1 in REQUIREMENTS.md traceability table. No orphaned requirements. BUILD-* and RPT-* are correctly scoped to Phases 2-3.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| Ortho4XP.py | 41 | bare `except:` | ℹ️ Info | Inside the pre-existing makedirs init block, deliberately preserved byte-for-byte per CONTEXT.md. Not the removed build catch-all. No action. |

No debt markers (TBD/FIXME/XXX/TODO/HACK) in changed files. The old `except: print("Crash!")` silent-failure handler is gone from the codebase (grep confirms only a docstring reference remains).

### Human Verification Required

**1. No-arg GUI launch (CLI-02)**

**Test:** Run `venv/Scripts/python.exe Ortho4XP.py` with no arguments.
**Expected:** Tkinter GUI window opens; closing it prints "Bon vol!" to the terminal.
**Why human:** Tkinter mainloop cannot be driven headlessly. The no-arg branch (Ortho4XP.py:48-51) and the pre-dispatch init block are preserved unchanged and confirmed by reading, so no regression is expected — but the actual window launch/close cannot be exercised programmatically.

### Gaps Summary

No gaps. All programmatically verifiable truths pass. The single outstanding item is the Tkinter no-arg GUI launch, which is inherently unverifiable headlessly and is routed to human verification. The code path for it is preserved byte-for-byte. The WR-01 code-review warning (non-finite coordinate input) is fixed and present (math.isfinite guard, commit b1844da).

---

_Verified: 2026-08-24_
_Verifier: Claude (gsd-verifier)_
