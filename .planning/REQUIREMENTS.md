# Requirements — Ortho4XP Command-Line Automation

**Milestone:** v1 CLI automation
**Defined:** 2026-08-24
**Core value:** A scriptable Ortho4XP — given an ICAO (or list), build the right tiles unattended, without the GUI.

## v1 Requirements

### CLI (argparse migration + compatibility)

- [x] **CLI-01**: User can run `Ortho4XP.py <subcommand> --help` and discover every command and flag (argparse-based dispatch).
- [x] **CLI-02**: Existing invocations still work unchanged — no args launches the GUI; `Ortho4XP.py lat lon [provider zl]` runs the legacy single-tile build. (Legacy shapes detected on raw `sys.argv` before argparse runs.)
- [x] **CLI-03**: A failed build or command exits non-zero with a real error message, replacing the bare `except: print("Crash!")`.
- [x] **CLI-04**: Legacy lat/lon parsing uses `floor()` semantics, not `int()` truncation, so southern/western-hemisphere coordinates map to the correct tile.

### Build (ICAO-driven builds)

- [ ] **BUILD-01**: User can resolve an ICAO code to lat/lon via `mcp_aviation_server`; an unreachable/unknown lookup fails with a clear message (and optional local fallback), never a silent wrong result.
- [ ] **BUILD-02**: User can build the 1°×1° tile containing a given ICAO with a single command.
- [ ] **BUILD-03**: User can pass `--radius N` to also build neighboring tiles within N whole tiles (Chebyshev square) of the ICAO's containing tile, correctly handling negative coords and antimeridian wraparound.
- [ ] **BUILD-04**: User can build for multiple ICAOs in one invocation (e.g. `--icao KJFK,KLGA,KEWR`).
- [ ] **BUILD-05**: User can build from a list file of ICAOs (one per line, `#` comments ignored) for unattended/scheduled runs.

### Report (read-only terrain reporting)

- [ ] **RPT-01**: User can list built tiles with provider, zoom level, build date, and on-disk size — read through `O4_File_Names` (FNAMES), never importing the build/config side-effect modules.
- [ ] **RPT-02**: User can ask whether a given ICAO's tile(s) are already built (coverage-by-ICAO), reusing the BUILD-01 resolver and RPT-01 inventory.
- [ ] **RPT-03**: User can get a health/staleness report flagging partial builds (missing DSF/DDS, crashed-run leftovers) and stale tiles, using one shared "is this tile complete" predicate.

## v1.x Requirements (deferred)

- [ ] Detail-zone report — aggregate view of per-tile custom higher-zoom zones from `.cfg` (thin read over RPT-01's data model).
- [ ] Disk overlap / redundant-artifact report — flag stale artifacts left when a tile is rebuilt at a different provider/zoom (NOT geometric overlap; the grid is non-overlapping).
- [ ] Dry-run (`--dry-run`) on batch build — resolve ICAOs → tile list and print what would build, without downloading/computing.
- [ ] `--json` output on report commands — machine-readable, additive over the same data model.

## Out of Scope

- Radius in km / nautical miles — Ortho4XP's world model is 1°×1° tiles; km→tile conversion is latitude-dependent and invites off-by-one errors. Radius is in whole tiles.
- True geometric overlap detection between tiles — tiles are a fixed non-overlapping grid; they cannot intersect. "Overlap" is reinterpreted as stale within-tile artifacts (v1.x).
- Bundling a full airport database in the repo — duplicates `mcp_aviation_server`, second source of truth. (A trimmed offline fallback CSV is allowed, not a full DB.)
- Auto-fix on staleness — report commands are read-only; rebuild/cleanup is a separate explicit command.
- Resume / skip-already-built — deferred to v2+; must sit on a trusted staleness predicate first.
- Live progress dashboard — build-time console output (`O4_UI_Utils`) already covers this.
- GUI rewrite and build-pipeline algorithm changes — this milestone is orchestration + reporting only.

## Traceability

<!-- Filled by roadmap: REQ-ID → Phase -->

| REQ-ID | Phase |
|--------|-------|
| CLI-01 | Phase 1 |
| CLI-02 | Phase 1 |
| CLI-03 | Phase 1 |
| CLI-04 | Phase 1 |
| BUILD-01 | Phase 2 |
| BUILD-02 | Phase 3 |
| BUILD-03 | Phase 3 |
| BUILD-04 | Phase 3 |
| BUILD-05 | Phase 3 |
| RPT-01 | Phase 2 |
| RPT-02 | Phase 2 |
| RPT-03 | Phase 2 |

---
*Requirements for Ortho4XP CLI automation — v1 milestone*
