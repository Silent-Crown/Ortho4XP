# Roadmap: Ortho4XP Command-Line Automation

## Overview

Three phases turn Ortho4XP's headless mode into a real CLI. Phase 1 migrates the entry
point to argparse without breaking either frozen legacy invocation (no-arg GUI launch,
`lat lon [provider zl]` build). Phase 2 builds a read-only reporting layer over the
existing `FNAMES` path authority, and pulls the ICAO→lat/lon resolver in early so
coverage-by-ICAO has something to resolve against. Phase 3 spends that resolver to
deliver ICAO-driven builds — single tile, radius, multi-ICAO, and list-file batch runs.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: CLI Dispatch & Compatibility** - Argparse migration with `--help` discoverability, preserving both frozen legacy invocations and replacing the bare "Crash!" handler with real errors. (completed 2026-08-24)
- [ ] **Phase 2: Report & ICAO Resolution** - Read-only tile inventory, coverage-by-ICAO, and health/staleness reporting, backed by an ICAO→lat/lon resolver via `mcp_aviation_server`.
- [ ] **Phase 3: ICAO-Driven Build** - Build a tile (or radius of tiles) around one or more ICAOs, from args or a list file, for unattended runs.

## Phase Details

### Phase 1: CLI Dispatch & Compatibility

**Mode:** mvp
**Goal**: Users get a discoverable, argparse-based CLI without any regression to existing invocations or error behavior.
**Depends on**: Nothing (first phase)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):

  1. User can run `Ortho4XP.py <subcommand> --help` and see every command and flag documented.
  2. User can run `Ortho4XP.py` with no args and the GUI launches exactly as before argparse was introduced.
  3. User can run `Ortho4XP.py lat lon [provider zl]` and get the legacy single-tile build, with negative (southern/western-hemisphere) coordinates correctly floored to the containing tile rather than truncated toward zero.
  4. When a build or command fails, the user sees a real, non-generic error message and the process exits non-zero, instead of the bare "Crash!" catch-all.

**Plans**: 1 plan
Plans:

- [x] 01-01-PLAN.md — argparse CLI dispatch (build subcommand tracer + legacy compat expansion)

### Phase 2: Report & ICAO Resolution

**Mode:** mvp
**Goal**: Users can inspect what's already built — including by ICAO — without side effects, and the ICAO resolver that Phase 3's builds will reuse is proven here first.
**Depends on**: Phase 1
**Requirements**: RPT-01, RPT-02, RPT-03, BUILD-01
**Success Criteria** (what must be TRUE):

  1. User can list built tiles with provider, zoom level, build date, and on-disk size, read through `O4_File_Names` without importing build/config side-effect modules.
  2. User can resolve an ICAO code to lat/lon via `mcp_aviation_server` and get a clear, specific error (never a silent wrong result) when the lookup is unreachable or the ICAO is unknown.
  3. User can ask whether a given ICAO's tile(s) are already built, using that same resolver against the tile inventory.
  4. User can run a health/staleness report that flags partial builds (missing DSF/DDS, crashed-run leftovers) and stale tiles via one shared "is this tile complete" predicate.

**Plans**: 3/3 plans executed
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — tracer: ICAO resolver + `report coverage --icao` end-to-end (containing tile), test harness, config var

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — resolver 3-way error classification + full 3x3 coverage block

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — `report tiles` inventory + `report health` (partial/crashed leftovers)

### Phase 3: ICAO-Driven Build

**Mode:** mvp
**Goal**: Users can build tiles unattended by naming ICAOs instead of computing lat/lon by hand.
**Depends on**: Phase 2
**Requirements**: BUILD-02, BUILD-03, BUILD-04, BUILD-05
**Success Criteria** (what must be TRUE):

  1. User can build the 1°×1° tile containing a given ICAO with a single command.
  2. User can pass `--radius N` to also build neighboring tiles within N whole tiles (Chebyshev square) of the ICAO's containing tile, correctly handling negative coordinates and antimeridian wraparound.
  3. User can build for multiple ICAOs in one invocation (e.g. `--icao KJFK,KLGA,KEWR`).
  4. User can point the build command at a list file of ICAOs (one per line, `#` comments ignored) for unattended/scheduled runs.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CLI Dispatch & Compatibility | 1/1 | Complete    | 2026-08-24 |
| 2. Report & ICAO Resolution | 3/3 | In Progress|  |
| 3. ICAO-Driven Build | 0/TBD | Not started | - |
