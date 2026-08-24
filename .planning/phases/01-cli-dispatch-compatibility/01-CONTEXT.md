# Phase 1: CLI Dispatch & Compatibility - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate the `Ortho4XP.py` entry point from positional `sys.argv` parsing to an
argparse-based CLI with discoverable subcommands and `--help`, **without regressing** any
existing invocation. Delivers CLI-01..04:

- CLI-01: `Ortho4XP.py <subcommand> --help` documents every command and flag.
- CLI-02: No args → GUI; `Ortho4XP.py lat lon [provider zl]` → legacy single-tile build,
  both detected on raw `sys.argv` before argparse runs.
- CLI-03: Failures exit non-zero with a real error, replacing `except: print("Crash!")`.
- CLI-04: Legacy lat/lon parsing floors to the containing tile (correct for negative
  hemispheres), not `int()` truncation.

This phase is CLI dispatch + compatibility only. ICAO resolution (Phase 2) and
ICAO-driven / report commands (Phase 2–3) are out of scope — but the dispatch structure
must leave room for them.

</domain>

<decisions>
## Implementation Decisions

### Command Surface & Dispatch
- Phase 1 ships a single real subcommand: `build LAT LON [--provider P] [--zl Z]`, so the
  argparse tree is non-empty and `--help` has content. `report` / ICAO subcommands are
  added in Phase 2–3, not scaffolded empty now.
- Legacy form is detected by sniffing raw `sys.argv` **before** argparse: empty → GUI;
  `argv[1]` and `argv[2]` both parse as numbers → legacy build; otherwise → argparse
  subcommand dispatch.
- The legacy `lat lon [provider zl]` path and the `build` subcommand route through **one
  shared build function** (build the `CFG.Tile`, run the 4-stage pipeline).
- CLI logic lives in a new thin `src/O4_CLI_Utils.py` module (argparse setup + dispatch +
  the shared build/floor helpers). `Ortho4XP.py` stays a shim that runs the existing init
  block then calls into it. Phase 2–3 extend this module rather than growing the entry point.

### Errors & Exit Codes (CLI-03)
- Replace `except: print("Crash!")` with: print the exception message **and traceback** to
  stderr, then `sys.exit(1)`.
- Exit-code scheme: `1` for any runtime/build failure; argparse's own `2` for usage errors.
- Current argument-error paths that call bare `sys.exit()` (bad lat/lon, unreadable tile
  config) now exit **non-zero** — today they exit 0, masking failure from scripts.
- Traceback is always shown on crash (no test suite exists; users need it to debug),
  not gated behind a verbosity level.

### Coordinate Flooring (CLI-04)
- Flooring uses `math.floor(float(x))` so both negative and decimal inputs map to the
  correct containing tile.
- Decimal coordinates are accepted (`build 47.5 -122.5` → tile 47, −123), not just integers.
- Validate range (lat ∈ [−90, 89], lon ∈ [−180, 179]); out-of-range input is a clear
  non-zero error.
- A single shared floor/parse helper is used by both the legacy path and the `build`
  subcommand — no duplicated coordinate logic.

### Backward-Compat Preservation
- Keep the legacy usage text (`cmd_line`) for the legacy path; argparse auto-generates
  usage/help for subcommands.
- Preserve the exact `"Bon vol!"` success message for both GUI and build paths.
- Keep the pre-dispatch init block unchanged (Utils_dir check, `makedirs` of data dirs,
  `IMG.initialize_*`), running for all paths before dispatch.
- No-arg behavior is unchanged: Tkinter GUI launches exactly as before argparse existed.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Ortho4XP.py` init block (lines 32–49): `Utils_dir` existence check, data-dir `makedirs`,
  and `IMG.initialize_extents_dict/color_filters_dict/providers_dict/combined_providers_dict`
  — must run before any dispatch. Reuse verbatim.
- Legacy build construction: `CFG.Tile(lat, lon, '')`, then optional
  `tile.default_website = provider_code` / `tile.default_zl = zoomlevel`.
- The 4-stage pipeline: `VMAP.build_poly_file(tile)` → `MESH.build_mesh(tile)` →
  `MASK.build_masks(tile)` → `TILE.build_tile(tile)`. This is the body of the shared build fn.
- `FNAMES` (`O4_File_Names`) is the path authority; `O4_UI_Utils` (`UI.vprint/lvprint`) is
  the logging convention.

### Established Patterns
- Two-letter uppercase module aliases (`IMG`, `VMAP`, `MESH`, `MASK`, `TILE`, `GUI`, `CFG`,
  `FNAMES`, `UI`); new module would be imported as `import O4_CLI_Utils as CLI`.
- snake_case functions, `build_`/`initialize_` prefixes; 4-space indent.
- `O4_Config_Utils` (CFG) **must remain imported last** — it mutates other modules'
  module-level variables at import time. A new CLI module must not disturb this order.

### Integration Points
- The sole dispatch site is the `if __name__ == '__main__'` block in `Ortho4XP.py`
  (lines 32–84). Everything below the init block is replaced by a call into `O4_CLI_Utils`.
- New `src/O4_CLI_Utils.py` is added to `sys.path` implicitly (src/ is already on path);
  it imports the build modules (VMAP/MESH/MASK/TILE/CFG) to run the pipeline.

</code_context>

<specifics>
## Specific Ideas

- The argparse `prog` is `Ortho4XP.py`; keep help output naming consistent with how users
  invoke it.
- `build` subcommand flags mirror the legacy positional 4th/5th args: `--provider`/`--zl`
  (provider code + integer zoom level).

</specifics>

<deferred>
## Deferred Ideas

- `report` and ICAO (`--icao`, `--radius`, list-file) subcommands — Phase 2–3, not this phase.
- `--json` / `--dry-run` flags — v1.x deferred per REQUIREMENTS.md.

</deferred>
