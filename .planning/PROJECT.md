# Ortho4XP — Command-Line Automation

## What This Is

Ortho4XP is a scenery generation tool for X-Plane that builds terrain mesh and
orthophoto textures for 1°×1° tiles. This milestone extends its thin headless mode into
a real command-line interface: build tiles around ICAO airport codes, report on
already-built terrain, and grow more automation commands over time — for users who script
scenery generation instead of driving the Tkinter GUI.

## Core Value

A scriptable Ortho4XP: given an ICAO code (or a list), build the right tiles unattended —
without opening the GUI.

## Requirements

### Validated

<!-- Inferred from existing code via .planning/codebase/ map -->

- ✓ Headless single-tile build — `Ortho4XP.py lat lon [provider zl]` runs the 4-stage
  pipeline (vector map → mesh → masks → tile) — existing
- ✓ GUI build & tile management (Tkinter) — existing
- ✓ Per-tile + global config system (`O4_Cfg_Vars`, `O4_Config_Utils`) — existing
- ✓ ICAO tag parsing from OSM during a build (`O4_Airport_Utils`) — existing
- ✓ Imagery providers, DEM sources, Overpass/OSM download — existing
- ✓ Discoverable argparse CLI — `Ortho4XP.py build --help`, legacy `lat lon [provider zl]`
  and no-arg GUI preserved, real errors + non-zero exit, floor()-based coord parsing —
  **validated in Phase 1** (CLI-01..04)

### Active

<!-- This milestone. Hypotheses until shipped. -->

- [ ] Build around an ICAO — resolve ICAO → lat/lon, build the containing tile plus tiles
  within a configurable radius
- [ ] Batch ICAO build — accept multiple ICAOs (args or a list file)
- [ ] Terrain report — inventory of built tiles (provider, zoom, build date, on-disk size)
- [ ] Report: coverage by ICAO — is a given airport's tile(s) already built?
- [ ] Report: health/staleness — flag partial builds, missing DDS/DSF, stale tiles
- [ ] Report: detail areas — surface per-tile custom higher-zoom zones
- [ ] Report: disk overlap — detect overlapping/redundant coverage wasting disk space

### Out of Scope

- Rewriting the GUI — the CLI wraps the same `O4_` modules; GUI stays as-is
- Changing the build pipeline algorithms — this milestone is orchestration + reporting only
- Bundling a new ICAO dataset if `mcp_aviation_server` can serve lookups — avoid duplicate
  airport data (fallback only if integration proves too heavy)

## Context

- Entry point `Ortho4XP.py` currently parses `sys.argv` positionally with a bare
  `try/except` that prints "Crash!" on any failure — the argparse migration should also
  surface real errors.
- No test suite, linter config, or build step exists; the app runs from source with
  vendored native binaries under `Utils/{win,mac,lin}`.
- `O4_File_Names.py` (FNAMES) is the single source of truth for all tile/data paths —
  the report commands read built-tile state through it, not hardcoded paths.
- `mcp_aviation_server` (Silent-Crown) is a FastMCP server over an airports/runways DB
  (SQLite/Postgres/MySQL, Dockerized) — the chosen ICAO→coordinate source.

## Constraints

- **Compatibility**: Existing headless invocations (`Ortho4XP.py lat lon [provider zl]`)
  and no-arg GUI launch must keep working — scripts and docs depend on them.
- **Tech stack**: Python 3.13, stdlib `argparse` (no new CLI framework); reuse existing
  `O4_` modules rather than reimplementing build logic.
- **Dependencies**: ICAO lookup goes through `mcp_aviation_server`; degrade gracefully
  (clear error, optional local fallback) when it is unreachable.
- **Platform**: Runs on Windows/macOS/Linux — path handling via FNAMES, not OS-specific code.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extend `Ortho4XP.py` with argparse (not a separate script) | One tool, parity with GUI, keeps a single entry point | ✓ Done (Phase 1) — CLI in `src/O4_CLI_Utils.py`, entry point is a shim |
| ICAO→coords via `mcp_aviation_server` | Silent-Crown already has the aviation DB; avoid bundling duplicate data | — Pending |
| Build scope = containing tile + `--radius` neighbors | Airports straddle tile edges; radius is opt-in | — Pending |
| Reporting reads built-tile state through FNAMES | Path authority already centralized; avoids drift | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-24 after Phase 1 (CLI Dispatch & Compatibility) completion*
