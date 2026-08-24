# Phase 1: CLI Dispatch & Compatibility - Research

**Researched:** 2026-08-24
**Domain:** Python 3.13 stdlib `argparse` refactor of a single 84-line entry point
**Confidence:** HIGH

## Summary

This phase replaces raw `sys.argv` handling in `Ortho4XP.py` with `argparse`, while
preserving three legacy behaviors byte-for-byte: no-arg GUI launch, `lat lon [provider zl]`
build, and the `cmd_line` usage string. The mechanism is a **pre-argparse raw-argv sniff**:
inspect `sys.argv[1:]` directly, decide "empty / legacy-numeric / everything else", and
only hand control to `argparse.parse_args()` on the third branch. This is not an argparse
feature — it's a manual `try: float(argv[1]); float(argv[2])` check performed before
`ArgumentParser` is ever touched, so argparse never sees and never has a chance to
misinterpret the legacy positional form.

All new CLI logic goes in `src/O4_CLI_Utils.py`. The single hard constraint carried over
from the existing codebase is import order: `O4_Config_Utils` (CFG) must be the last
top-level import anywhere in the process, because it mutates other modules' module-level
variables via `exec()` at import time. `O4_CLI_Utils` must not import CFG (or VMAP/MESH/
MASK/TILE, which is fine to import early but conventionally follows CFG in the existing
file) at its own module top level — those imports belong inside the function that runs the
build, executed only after `Ortho4XP.py`'s existing top-level import block has already run
CFG last.

**Primary recommendation:** One `argparse.ArgumentParser(prog="Ortho4XP.py")` with
`add_subparsers(dest="command", required=True)` and one `build` subparser
(`lat`, `lon` positionals + `--provider`/`--zl` optionals). Guard `parser.parse_args()`
behind the raw-argv legacy/empty sniff so it's only ever called with subcommand-shaped
input. A single `run_build(lat, lon, provider=None, zl=None)` function in
`O4_CLI_Utils.py`, called from both the legacy branch and the `build` subcommand, does
lazy imports of CFG/VMAP/MESH/MASK/TILE and wraps the 4-stage pipeline in a
try/except that prints the exception + traceback to stderr and calls `sys.exit(1)`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw-argv legacy/empty sniff | Entry point shim (`Ortho4XP.py`) or `O4_CLI_Utils.dispatch()` | — | Must run before argparse touches `sys.argv`; logically part of dispatch, so it lives in `O4_CLI_Utils.dispatch()` for testability, called from the shim |
| argparse tree (parser + subparsers) | `O4_CLI_Utils.py` | — | New CLI module owns all argparse setup, per locked decision |
| Coordinate floor/validate helper | `O4_CLI_Utils.py` | — | Shared by legacy path and `build` subcommand |
| Build pipeline execution (VMAP→MESH→MASK→TILE) | `O4_CLI_Utils.py` (`run_build`) | Existing `O4_*_Utils` modules (unchanged) | CLI module orchestrates; does not reimplement pipeline stages |
| Error/exit-code wrapper | `O4_CLI_Utils.py` | — | Wraps the call to `run_build`, not the individual pipeline stages |
| Pre-dispatch init (dirs, `IMG.initialize_*`) | `Ortho4XP.py` (unchanged) | — | Explicitly preserved per locked decision; runs before any dispatch path |
| GUI launch | `Ortho4XP.py` (unchanged) | `O4_GUI_Utils` | No-arg path stays exactly as today |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | `Ortho4XP.py <subcommand> --help` documents every command and flag | argparse subparser with `help=`/`description=` on `add_parser` and each `add_argument` — see Pattern 1 |
| CLI-02 | No args → GUI; `lat lon [provider zl]` → legacy build, both sniffed pre-argparse | Pattern 2 (raw-argv sniff) |
| CLI-03 | Failures exit non-zero with real error, replacing `except: print("Crash!")` | Pattern 3 (error wrapper) |
| CLI-04 | Legacy lat/lon uses floor() not int() truncation | Pattern 4 (floor/validate helper) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib (3.13.5) | Subcommand CLI, `--help` generation | Already the locked decision (no new CLI framework); zero new dependency |
| `math.floor` | stdlib | Coordinate flooring per CLI-04 | Exact semantics requested in CONTEXT.md |
| `traceback` | stdlib | Full traceback to stderr on crash | Only stdlib way to get a formatted traceback string/print without re-raising |

No new packages are installed in this phase — no Package Legitimacy Audit section is
needed (stdlib only).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | `click`, `typer` | Explicitly excluded by project constraints ("stdlib argparse only, no new CLI framework") |
| Raw-argv sniff | `argparse` with `nargs='?'` fuzzing to accept both shapes in one parser | Rejected: CONTEXT.md locks the sniff-before-parse approach; mixing legacy positional-only args into the same parser as subcommands is exactly the ambiguity argparse subparsers don't handle well (a bare `47 -122` can't be told apart from a malformed subcommand invocation once argparse owns it) |

## Architecture Patterns

### System Architecture Diagram

```
sys.argv
   │
   ▼
Ortho4XP.py init block (unchanged: dir checks, makedirs, IMG.initialize_*)
   │
   ▼
O4_CLI_Utils.dispatch(argv[1:])
   │
   ├── len(argv) == 0 ──────────────────► GUI.Ortho4XP_GUI().mainloop() ─► "Bon vol!"
   │
   ├── argv[1] & argv[2] both numeric ──► legacy branch
   │        (float() succeeds on both)         │
   │                                            ▼
   │                                   parse legacy shape:
   │                                   lat lon | lat lon provider zl
   │                                            │
   │                                            ▼
   └── else ──► parser.parse_args(argv) ──► args.command == "build"
                        │                        │
                        │ (argparse usage error   │
                        │  → exit code 2)         │
                                                   ▼
                                    run_build(lat, lon, provider, zl)
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                     ▼                    ▼
                     floor_coord() validate   lazy import CFG/    try: VMAP→MESH→MASK→TILE
                     (shared helper)          VMAP/MESH/MASK/TILE except: traceback to stderr,
                                                                          sys.exit(1)
                                                   │
                                                   ▼
                                             "Bon vol!" (success)
```

### Recommended Project Structure
```
Ortho4XP.py            # unchanged init block; shim calls CLI.dispatch(sys.argv[1:])
src/
├── O4_CLI_Utils.py     # NEW: argparse setup, raw-argv sniff, shared build+floor helpers
├── O4_Config_Utils.py  # CFG — imported lazily inside O4_CLI_Utils.run_build(), not at module top
├── O4_Vector_Map.py    # VMAP — same, lazy import inside run_build()
├── O4_Mesh_Utils.py    # MESH — same
├── O4_Mask_Utils.py    # MASK — same
└── O4_Tile_Utils.py    # TILE — same
```

### Pattern 1: argparse tree with one real subcommand

**What:** Top-level parser with `add_subparsers(dest="command", required=True)`, one
`build` subparser.
**When to use:** Whenever `argparse.parse_args()` is actually invoked (i.e., argv did not
match the empty or legacy-numeric raw sniff).
**Example:**
```python
# Source: Python 3.13 argparse stdlib docs (docs.python.org/3/library/argparse.html)
import argparse

def build_parser():
    parser = argparse.ArgumentParser(
        prog="Ortho4XP.py",
        description="Ortho4XP scenery generation tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser(
        "build", help="Build a single 1x1 degree tile"
    )
    build_p.add_argument("lat", help="SW corner latitude (integer or decimal)")
    build_p.add_argument("lon", help="SW corner longitude (integer or decimal)")
    build_p.add_argument("--provider", default=None, help="Imagery provider code")
    build_p.add_argument("--zl", type=int, default=None, help="Zoom level")

    return parser
```
`lat`/`lon` are taken as strings here (not `type=float`) so the shared floor/validate
helper (Pattern 4) can apply identical parsing/range-checking logic to both the legacy
path and the subcommand path — avoiding two divergent coordinate parsers.
`Ortho4XP.py <subcommand> --help` and `Ortho4XP.py build --help` are both free from
argparse once `help=` strings are supplied; this satisfies CLI-01 without extra code.

### Pattern 2: Raw-argv sniff before parse_args()

**What:** Decide "GUI / legacy / subcommand" from `sys.argv[1:]` directly, before
`argparse` ever runs. This is a manual branch, not an argparse feature.
**When to use:** As the very first thing `O4_CLI_Utils.dispatch()` does.
**Example:**
```python
def _is_number(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def dispatch(argv):
    if len(argv) == 0:
        return run_gui()
    if len(argv) >= 2 and _is_number(argv[0]) and _is_number(argv[1]):
        return run_legacy(argv)          # lat lon [provider zl]
    parser = build_parser()
    args = parser.parse_args(argv)       # argparse usage errors -> SystemExit(2)
    if args.command == "build":
        return run_build(args.lat, args.lon, args.provider, args.zl)
```
`float(s)` handles negatives (`-45`) and decimals (`47.5`) correctly — Python's `float()`
constructor accepts a leading `-` and a fractional part natively, so no custom regex is
needed for CLI-04's "accept decimals" requirement. `argparse.parse_args()` is never
called on the legacy branch, so argparse cannot consume, reorder, or reinterpret those
two tokens (e.g. as an ambiguous subcommand name) — the sniff fully short-circuits it.
`float("build")` raises `ValueError` so `Ortho4XP.py build 47 -122` still correctly falls
through to the argparse branch.

### Pattern 3: Error/exit-code wrapper (CLI-03)

**What:** Replace `except: print("Crash!")` with a wrapper that prints the exception
message and full traceback to stderr, then exits 1.
**When to use:** Wraps the call to `run_build()` (both from the legacy path and the
`build` subcommand) — one wrapper, not duplicated per call site.
**Example:**
```python
# Source: Python 3.13 traceback stdlib docs (docs.python.org/3/library/traceback.html)
import sys
import traceback

def run_and_report(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except SystemExit:
        raise  # let intentional sys.exit() calls (e.g. usage errors) pass through
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
```
`traceback.print_exc(file=sys.stderr)` is the single stdlib call that prints both the
exception message and the full formatted traceback in the standard Python format — no
manual string assembly needed. Catching `Exception` (not bare `except:`) still catches
everything a build can realistically raise while letting `KeyboardInterrupt`/`SystemExit`
propagate normally, matching the "argparse's own 2 for usage errors" exit-code split in
CONTEXT.md. Bad lat/lon or unreadable tile config (today's bare `sys.exit()`, exit 0)
should instead raise/print via this same path so they land on exit 1, not 0.

### Pattern 4: Floor + validate coordinate helper (CLI-04)

**What:** One function used by both the legacy path and `build` subcommand to parse and
floor lat/lon.
**When to use:** Immediately after either dispatch branch has raw lat/lon strings.
**Example:**
```python
# Source: Python 3.13 math stdlib docs (docs.python.org/3/library/math.html#math.floor)
import math

def parse_and_floor_coord(value, *, lo, hi, name):
    try:
        f = float(value)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {value!r}")
    n = math.floor(f)
    if not (lo <= n <= hi):
        raise ValueError(f"{name} {n} out of range [{lo}, {hi}]")
    return n

def parse_lat(value):
    return parse_and_floor_coord(value, lo=-90, hi=89, name="lat")

def parse_lon(value):
    return parse_and_floor_coord(value, lo=-180, hi=179, name="lon")
```
`math.floor(-122.5)` → `-123` (floors toward negative infinity), which is the "containing
tile" semantics CONTEXT.md asks for — `int(-122.5)` → `-122` (truncates toward zero) is
the bug being fixed. `math.floor()` on a float returns a Python `int` in 3.13, so no
extra `int()` cast is needed downstream.

### Anti-Patterns to Avoid
- **Calling `parser.parse_args()` unconditionally, then branching on the result to decide
  "was this legacy?":** Once argparse has consumed argv it may have already errored out
  (exit 2) on input that was actually valid legacy shape, or silently reinterpreted a
  legacy positional as something else. The sniff must happen strictly before
  `parse_args()` is called, per locked decision.
- **Importing CFG/VMAP/MESH/MASK/TILE at the top of `O4_CLI_Utils.py`:** `O4_CLI_Utils`
  would then be imported by `Ortho4XP.py` at module load time (to get `dispatch`), which
  would force CFG's mutating side effects to run at whatever point `O4_CLI_Utils` is
  imported — before `Ortho4XP.py`'s own existing `import O4_Config_Utils as CFG` line
  finishes establishing the "CFG last" order. Doing the CFG-family imports lazily inside
  `run_build()` (called only after dispatch, well after all top-level imports have
  settled) sidesteps this entirely.
- **`int(sys.argv[1])`** for coordinate parsing — this is precisely the CLI-04 bug
  (truncates negative decimals toward zero instead of flooring).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subcommand `--help` text | Custom usage-string formatter | `argparse` `help=`/`description=` + `add_subparsers` | argparse already generates correct, consistent `--help` for both top-level and per-subcommand invocations |
| Traceback formatting | Manual `str(e)` + frame walking | `traceback.print_exc()` | Exact match to default Python crash output; zero edge cases to get wrong |
| "Is this arg numeric" check | Regex for `-?\d+\.?\d*` | `float(s)` in a `try/except ValueError` | `float()` already handles sign, decimals, exponents, and whitespace correctly; a hand-rolled regex must be independently verified against every one of those |

**Key insight:** Every part of this phase — arg parsing, help text, floor semantics,
traceback printing — has an exact stdlib primitive. There is nothing here that
legitimately needs a third-party library.

## Common Pitfalls

### Pitfall 1: Sniff runs after argparse has already exited
**What goes wrong:** If the raw-argv check is placed after any call to `parser.parse_args()`
in the same function/branch, argparse's `required=True` on subparsers means an
unrecognized token (e.g. a bare `47`) raises `SystemExit(2)` from inside `parse_args()`
before the sniff code is ever reached.
**Why it happens:** `parse_args()` calls `sys.exit()` internally on error; it does not
return control on failure the way most parsing functions do.
**How to avoid:** The sniff must be the literal first statement in `dispatch()`, with
`parser.parse_args()` only reachable in the final `else` branch.
**Warning signs:** `Ortho4XP.py 47 -122` (legacy build) prints an argparse usage error
and exits 2 instead of running the build.

### Pitfall 2: `provider`/`zl` optionality diverges between legacy and subcommand paths
**What goes wrong:** Legacy form is positional (`lat lon` OR `lat lon provider zl` — no
partial form), while the `build` subcommand exposes `--provider`/`--zl` as independently
optional flags. A naive shared helper that assumes "both or neither" will reject
`build 47 -122 --provider BI` (zl omitted) even though CFG.Tile happily accepts a
provider override with no zl override (or vice versa).
**Why it happens:** The two call shapes are structurally different (positional pair vs.
independent optional flags), even though they both end up calling the same `run_build`.
**How to avoid:** `run_build(lat, lon, provider=None, zl=None)` treats each of
`provider`/`zl` independently nullable; only set `tile.default_website` /
`tile.default_zl` when the corresponding argument is not `None`. The legacy branch's own
parsing (todays's `len(sys.argv) == 3` vs `== 5` check) still enforces the "both or
neither" rule at the legacy call site, not inside `run_build`.
**Warning signs:** `build` subcommand with only `--zl` set silently ignores it, or throws
on a missing provider.

### Pitfall 3: Legacy `cmd_line` usage text drifts from actual accepted syntax
**What goes wrong:** CONTEXT.md requires preserving the exact legacy usage string
verbatim, but if the legacy branch's parsing logic changes shape (e.g. decimal support
added) without updating `cmd_line`, the printed usage text becomes misleading.
**Why it happens:** `cmd_line` is a static string, disconnected from the parsing code
that enforces it.
**How to avoid:** Keep `cmd_line` textually unchanged per locked decision (it does not
mention int-vs-float, so no update is actually needed) but only ever print it from the
same failure branch that used to print it — do not repurpose it for `build` subcommand
errors (those get argparse's own generated usage text for free).

## Code Examples

Verified patterns from official sources:

### Suppressing argparse's default `SystemExit` in a wrapper (not required, documented for completeness)
```python
# Source: Python 3.13 argparse stdlib docs
# By default argparse.ArgumentParser.error() prints usage + message to stderr and calls
# sys.exit(2). This matches CONTEXT.md's exit-code scheme ("argparse's own 2 for usage
# errors") with zero custom code — no need to subclass ArgumentParser or override error().
parser.parse_args(argv)  # exits 2 on bad/missing args, no try/except needed here
```

### Reading `sys.argv` slice for dispatch (avoids double-counting `argv[0]`)
```python
# Ortho4XP.py shim
if __name__ == '__main__':
    # ... existing unchanged init block (dir checks, makedirs, IMG.initialize_*) ...
    import O4_CLI_Utils as CLI
    CLI.dispatch(sys.argv[1:])
```
Passing `sys.argv[1:]` (not `sys.argv`) into `dispatch()` keeps index arithmetic in
`O4_CLI_Utils` consistent with what `argparse.parse_args(argv)` expects (it also defaults
to `sys.argv[1:]` when called with no argument) — one indexing convention throughout.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `int(sys.argv[1])` for lat/lon | `math.floor(float(x))` via shared helper | This phase (CLI-04) | Negative/decimal coords now map to correct containing tile |
| Bare `except: print("Crash!")` | `except Exception: traceback.print_exc(); sys.exit(1)` | This phase (CLI-03) | Real diagnostics + correct exit code for scripting |
| Positional-only `sys.argv` parsing | `argparse` with subcommands | This phase (CLI-01/02) | Discoverable `--help`; room for Phase 2-3 subcommands |

**Deprecated/outdated:** None — this is a pure additive/replacement refactor of one file;
no external API or library version is being deprecated.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `argparse`'s default `error()` behavior (usage + message to stderr, `sys.exit(2)`) requires no subclassing to match CONTEXT.md's "argparse's own 2 for usage errors" | Pattern 3, Code Examples | Low — this is argparse's documented default behavior across all 3.x versions; if wrong, a plan task would need to add an `ArgumentParser` subclass overriding `error()`, a small addition |
| A2 | `float()`'s acceptance of leading/trailing whitespace and scientific notation (e.g. `"1e2"`) as "numeric" is acceptable for the legacy-vs-subcommand sniff, even though such forms are not realistic lat/lon input | Pattern 2 | Very low — worst case, an absurd input like `Ortho4XP.py 1e2 1e2` gets routed to the legacy branch instead of erroring at the sniff stage; it will still fail range validation in Pattern 4 (`lo <= n <= hi`) shortly after |

**Verified this session:** `Tile.__init__(self, lat, lon, custom_build_dir)` signature
confirmed by reading `src/O4_Config_Utils.py:144` — `def __init__(self, lat, lon, custom_build_dir):`
[VERIFIED: src/O4_Config_Utils.py:144]. `Ortho4XP.py`'s existing 84-line body — including
the `cmd_line` string (line 30), the init block (lines 32-49), and the bare
`except: print("Crash!")` (lines 83-84) — read in full this session
[VERIFIED: Ortho4XP.py:1-84].

## Open Questions

1. **Does `Tile.__init__` or the pipeline stages ever call `sys.exit()` internally on
   bad input (as opposed to raising)?**
   - What we know: `Tile.make_dirs()` (`O4_Config_Utils.py:159-179`) raises a bare
     `Exception` on directory permission failure — it does not call `sys.exit()` itself.
   - What's unclear: Whether every code path inside VMAP/MESH/MASK/TILE consistently
     raises rather than calling `sys.exit()` directly, which would bypass the new
     error wrapper entirely (a `sys.exit(0)` deep in the pipeline would still exit 0).
   - Recommendation: Not worth auditing 5 large modules for this narrow phase; the
     wrapper's `except Exception` won't catch a rogue `sys.exit()`, but that's pre-existing
     behavior unrelated to this phase's scope — flag as a known limitation, not a blocker.

## Environment Availability

Skipped — this phase has no external tool/service dependency; it only touches
`Ortho4XP.py` and adds one pure-Python stdlib module. Python 3.13.5 itself is confirmed
already in use per `.claude/CLAUDE.md` (Technology Stack section).

## Validation Architecture

No test framework exists in this repo (confirmed: no pytest/unittest config, no
`tests/` directory referenced in CLAUDE.md). All CLI-01..04 validation is manual CLI
invocation, run from the repo root with the venv active.

### Phase Requirements -> Manual Verification Map

| Req ID | Behavior | Manual Command | Expected Result |
|--------|----------|-----------------|------------------|
| CLI-01 | `--help` documents every command/flag | `python Ortho4XP.py --help`<br>`python Ortho4XP.py build --help` | Top-level help lists `build`; `build --help` lists `lat`, `lon`, `--provider`, `--zl` with their help text |
| CLI-02 (no-arg) | No args launches GUI unchanged | `python Ortho4XP.py` | Tkinter GUI window opens; closing it prints `Bon vol!` |
| CLI-02 (legacy) | `lat lon [provider zl]` legacy build | `python Ortho4XP.py 47 -122`<br>`python Ortho4XP.py 47 -122 BI 16` | Runs the 4-stage pipeline for tile (47,-122); no argparse usage text printed |
| CLI-03 | Failure exits non-zero with real error | `python Ortho4XP.py 999 999` (invalid lat/lon, forces a raise)<br>then `echo $?` (bash) or `echo %errorlevel%` (cmd) | Exception message + traceback printed to stderr; exit code `1` |
| CLI-03 (usage) | Bad subcommand args exit 2 | `python Ortho4XP.py build` (missing lat/lon) | argparse usage error to stderr; exit code `2` |
| CLI-04 | Floor semantics on negative/decimal coords | `python Ortho4XP.py build 47.9 -122.1 --provider BI --zl 12`<br>compare tile dir created: should be tile `47,-123`, not `47,-122` | Confirms `math.floor(-122.1) == -123` is applied, not `int(-122.1) == -122` |
| Compatibility | Existing tile-config-only invocation still works | `python Ortho4XP.py 47 -122` in a dir with an existing `zOrtho4XP_+47-122.cfg` | Loads tile config as before (3-arg legacy form), no regression |

### Sampling Rate
- **Per task commit:** Run the single most relevant manual command from the table above
  (e.g. after implementing the floor helper, run the CLI-04 row).
- **Per wave merge / phase gate:** Run every row in the table above once, in order,
  before `/gsd-verify-work`.

### Wave 0 Gaps
- None — no test infrastructure to stand up; this phase intentionally stays manual-only
  per project constraints ("no test suite, no linter; runs from source").

## Security Domain

`security_enforcement` is enabled in `.planning/config.json`, but this phase is a pure
CLI-dispatch refactor with no new network, auth, or crypto surface — it does not call
`mcp_aviation_server` (that's Phase 2/BUILD-01) and does not add persistence.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | No auth surface introduced in this phase |
| V3 Session Management | no | N/A — CLI process, no sessions |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes | `parse_and_floor_coord()` range-validates lat/lon (`[-90,89]`/`[-180,179]`) before constructing `CFG.Tile`; argparse itself validates `--zl` as `int` |
| V6 Cryptography | no | No crypto/secrets touched by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Unvalidated lat/lon reaching `CFG.Tile`/`FNAMES.build_dir` (path construction from numeric input) | Tampering | `parse_and_floor_coord()`'s range check (Pattern 4) rejects out-of-range values before they reach path-building code; both lat and lon are floored `int`s, not attacker-controlled strings, by the time they reach `FNAMES.build_dir` |
| Traceback leakage to stderr on crash | Information Disclosure | Acceptable and intentional here per CONTEXT.md ("no test suite exists; users need it to debug") — this is a local single-user CLI tool, not a network service; traceback goes to the invoking user's own terminal, not a remote client |

## Sources

### Primary (HIGH confidence)
- Python 3.13 `argparse` stdlib documentation — subparsers, `error()`/exit-code default
  behavior, `parse_args()` semantics (training knowledge of a stable, versioned stdlib
  API; behavior unchanged across recent 3.x releases)
- Python 3.13 `math.floor` / `traceback.print_exc` stdlib documentation — flooring
  semantics and default traceback formatting

### Verified in-repo (HIGH confidence)
- `Ortho4XP.py:1-84` — full file read this session
- `src/O4_Config_Utils.py:142-179` — `Tile.__init__`/`make_dirs` read this session
- `.planning/phases/01-cli-dispatch-compatibility/01-CONTEXT.md` — locked decisions
- `.planning/REQUIREMENTS.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/config.json`

### Tertiary (LOW confidence)
None used — no web search was needed; this phase is entirely stdlib + in-repo code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only, versions fixed by the already-running Python 3.13.5
- Architecture: HIGH — directly derived from locked CONTEXT.md decisions + the actual
  84-line source file read in full
- Pitfalls: HIGH — each pitfall traced to a specific line/behavior in the existing file

**Research date:** 2026-08-24
**Valid until:** Stable — stdlib `argparse`/`math`/`traceback` behavior does not churn;
no expiry-relevant external dependency in this phase
