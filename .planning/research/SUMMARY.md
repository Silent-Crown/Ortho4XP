# Project Research Summary

**Project:** Ortho4XP CLI automation (argparse migration + ICAO-based batch build + terrain reporting)
**Domain:** CLI orchestration layer over an existing flat-module Python geospatial build tool
**Researched:** 2026-08-24
**Confidence:** HIGH

## Executive Summary

This milestone bolts a modern subcommand CLI, ICAO-based batch scenery building, and a read-only tile-inventory reporting layer onto Ortho4XP without touching its existing build pipeline. Research across stack, features, architecture, and pitfalls converges on the same shape: add four small `O4_*_Utils.py` modules (`CLI`, `ICAO`, `REPORT`, plus extensions to `GEO`) that orchestrate the *existing* `TILE.build_tile_list()` and `FNAMES` path authority rather than reimplementing any pipeline logic. Everything new is stdlib (`argparse`, `asyncio`, `csv`) plus one new dependency (`fastmcp`) to talk to the sibling `mcp_aviation_server` for ICAO→lat/lon resolution, with a bundled offline CSV as fallback.

The recommended approach: preserve the two frozen legacy invocations (`Ortho4XP.py` no-args → GUI, `Ortho4XP.py lat lon [provider zl]` → legacy build) by branching on raw `sys.argv` shape before argparse ever runs, then hand off everything else to a new subparser-based dispatcher. Reporting is built as a pure filesystem scan through `FNAMES` — no dependency on `CFG`/`GUI`/build-stage modules — so `report` works with zero network dependency and zero side effects from Ortho4XP's exec()-based config import machinery.

The dominant risk cluster is geodesy correctness, not technology choice: `int()` truncation instead of `floor()` silently breaks southern/western-hemisphere tiles, square-vs-circular radius definitions get conflated, and antimeridian wraparound near ±180° longitude is easy to miss in testing. All three are cheap to prevent with explicit unit tests (a southern-hemisphere ICAO, a near-dateline ICAO) but expensive to discover in the field since common test airports (EDDF, EGLL, KJFK) never exercise them. The second risk is external-service coupling: the MCP client must have a timeout and specific exception handling, and its import must stay lazy so `report`/`--help` never depend on network availability.

## Key Findings

### Recommended Stack

Everything new is either stdlib or already-adjacent to the ecosystem. `argparse` (stdlib) handles subcommands via `add_subparsers()`, but must not own the top-level dispatch for the two legacy invocation shapes. `fastmcp` (client only, v3.4.7) talks to `mcp_aviation_server`, which is itself FastMCP-based — confirmed by reading the server's source directly (`config.py`: `transport: str = "stdio"` default, tool is `get_airport_details(ident) -> str` JSON). `asyncio.run()` bridges the sync CLI to the async MCP client per invocation — no persistent event loop needed. The offline fallback is a trimmed OurAirports CSV (`ident,lat,lon` only, ~1-2MB) parsed with stdlib `csv.DictReader`, not pandas.

**Core technologies:**
- `argparse` (stdlib): subcommand CLI — zero new dependency, matches project's own constraint
- `fastmcp` (new dep, 3.4.7): MCP client to `mcp_aviation_server` — reuses the server's own framework instead of hand-rolling JSON-RPC
- `asyncio` (stdlib): one `asyncio.run()` per CLI invocation to bridge sync CLI ↔ async MCP client

### Expected Features

No direct precedent exists inside Ortho4XP itself (only the GUI's "Batch Build Tiles" dialog); feature judgment triangulates from the GUI, xOrganizer (3rd-party X-Plane inventory tool), and mature CLI patterns (terraform/ansible/rsync). Confidence MEDIUM — X-Plane-specific precedent is thin.

**Must have (table stakes):**
- Build a single tile by lat/lon (already exists — preserve verbatim)
- Build around an ICAO with configurable radius (containing tile via ICAO resolution)
- Batch ICAO build (comma-list args + list file)
- Tile inventory report (provider/zoom/date/size) — shared data layer for all reports
- Coverage-by-ICAO report — is this airport built?
- Health/staleness report (partial builds, missing DDS/DSF)
- Exit codes / machine-parseable failure signal (replaces "Crash!" pattern)

**Should have (competitive):**
- Dry-run mode on batch build (catches ICAO typos before multi-hour runs)
- Detail-zone report (surfaces existing per-tile zoom overrides, low cost)
- Disk overlap / redundant-artifact report (novel — no existing tool does this; scope precisely as "stale artifacts within a tile," NOT geometric overlap since tiles are a fixed non-overlapping grid)
- `--json` report output

**Defer (v2+):**
- Resume/skip-already-built — defer until the staleness predicate is proven, don't build resume on an unproven completeness check
- Auto-cleanup of stale artifacts as a distinct mutating command (never bundle into the read-only report)

**Anti-features to avoid:** radius in km/nm (tile-count is the natural unit), bundling a full ICAO database in Ortho4XP (duplicates `mcp_aviation_server`'s data — explicitly out of scope), auto-fix on staleness detection (reports must stay read-only), live progress dashboards (existing console output already covers this).

### Architecture Approach

Four new flat modules following the existing `O4_<Thing>_Utils.py` convention, each with a single responsibility and minimal cross-imports: `O4_CLI_Utils.py` (argparse dispatch only, no build/report logic), `O4_ICAO_Utils.py` (ICAO string → lat/lon via MCP, nothing else), `O4_Report_Utils.py` (read-only filesystem scan via `FNAMES`, explicitly never imports `CFG`/`GUI`/build-stage modules), and `O4_Geo_Utils.py` extended with `containing_tile()`/`tiles_in_radius()` pure math functions. `Ortho4XP.py`'s entry point gets exactly one new `elif` branch; existing GUI and legacy-positional branches are untouched.

**Major components:**
1. `O4_CLI_Utils.py` — thin argparse dispatcher, calls one handler per subcommand
2. `O4_ICAO_Utils.py` — MCP client adapter, async→sync bridge, isolated so a future local-fallback swap only touches this module
3. `O4_Report_Utils.py` — filesystem-scan inventory (`Tiles/` → `TileRecord` list), zero coupling to CFG/GUI/build pipeline
4. Existing `TILE.build_tile_list()` — reused as-is for any multi-tile build; new code never reimplements the 4-stage pipeline

**Suggested build order:** (1) CLI dispatch skeleton with just `build` as passthrough, validates compatibility pattern; (2) tile-inventory scanner + report subcommand — no external service risk, delivers value standalone; (3) ICAO resolver + radius math + batch build — highest-risk step (new async MCP dependency), sequence early to surface integration problems while there's roadmap room for fallback; (4) report refinements (detail-zone, overlap) — pure extensions, safe to defer. Steps 2 and 3 don't block each other.

### Critical Pitfalls

1. **`int()` truncation instead of `floor()` on negative coordinates** — silently picks the wrong tile for any southern-hemisphere or western-hemisphere ICAO (most of South America, Africa, Australia, the Americas). Use `math.floor()` everywhere raw decimal coords become tile indices; test with a southern-hemisphere ICAO (e.g. SBGR, FACT).
2. **Radius ambiguity (degrees vs. tiles vs. nautical miles)** — a naive square loop is latitude-naive and looks correct only near the equator. Pick tile-count (Chebyshev) radius as the explicit MVP definition, document it in `--help`, don't silently mix representations.
3. **Antimeridian/pole wraparound** — airports near ±180° longitude compute invalid tiles like `181` or produce duplicate string representations of the same tile. Normalize with `((lon + 180) % 360) - 180`, clamp latitude to `[-90, 89]`, add a Fiji/Kiribati-class test fixture.
4. **argparse migration silently breaking the two frozen legacy invocations** — `add_subparsers()` making a subcommand required intercepts before the "no args → GUI" branch ever runs. Branch on raw `sys.argv` shape before argparse, hand off to argparse only for new subcommands.
5. **MCP coupling without timeout/graceful degradation** — synchronous call with no timeout hangs indefinitely if `mcp_aviation_server` is down; bare `except:` (already a 173-occurrence anti-pattern in this codebase) would swallow the real error, directly contradicting this milestone's stated goal. Set explicit short timeout, catch specific failure modes, keep the MCP import lazy so `report`/`--help` never depend on network.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: CLI dispatch skeleton (argparse migration)
**Rationale:** Everything else plugs into this; it's the highest-compatibility-risk piece and should be validated first with the smallest possible surface area.
**Delivers:** `O4_CLI_Utils.py` with argparse subparsers, `Ortho4XP.py` gets one new `elif` branch, `build` subcommand is a thin passthrough to the existing single-tile legacy logic (refactored into one shared helper so both paths call it).
**Addresses:** `--help`/discoverable subcommands (table stakes), preserves legacy `lat lon [provider zl]` and no-arg GUI invocations.
**Avoids:** Pitfall 4 (argparse breaking frozen legacy invocations) — primary verification gate is a manual smoke test diffing old vs. new behavior for both frozen shapes.

### Phase 2: Tile-inventory report (coverage + health/staleness)
**Rationale:** Depends only on Phase 1 and `FNAMES`, no external service risk, delivers standalone user value even before ICAO resolution exists (coverage-by-ICAO can fall back to raw lat/lon input until Phase 3 lands).
**Delivers:** `O4_Report_Utils.py` (`scan_tiles()` → `TileRecord` list), `report` subcommand with coverage and health/staleness sub-views.
**Uses:** `FNAMES` path authority exclusively — deliberately zero coupling to `CFG`/`GUI`/build-stage modules.
**Avoids:** Pitfall 6 (hardcoded glob patterns bypassing FNAMES, OS-specific path assumptions) — verify on Windows path with mixed-case/nested dirs.

### Phase 3: ICAO resolution + radius build + batch build
**Rationale:** Independent of Phase 2; highest-risk step (new async MCP dependency, external service must be reachable) — sequence early enough that integration problems (transport, availability) surface while there's still roadmap room to lean on the documented fallback.
**Delivers:** `O4_ICAO_Utils.py` (MCP client, async→sync bridge, lazy import), `O4_Geo_Utils.py` extensions (`containing_tile()`, `tiles_in_radius()`), `build-icao` subcommand with `--radius`, batch build from `--icao` list or list file.
**Implements:** Architecture Pattern 2 (command handlers call `TILE.build_tile_list()`, never pipeline internals).
**Avoids:** Pitfalls 1, 2, 3 (floor() not int(), explicit tile-count radius definition, antimeridian normalization) and Pitfall 5 (MCP timeout + specific exception handling + lazy import).

### Phase 4: Report refinements (detail-zone, disk overlap) + polish
**Rationale:** Pure extensions of Phase 2's scanner/record shape, no new components or dependencies — safe to defer to the end.
**Delivers:** Detail-zone report (reads existing per-tile `.cfg` zoom overrides), disk-overlap/redundant-artifact report (scoped as stale artifacts within a tile, not geometric overlap), optional `--json` output, optional dry-run flag on batch build.

### Phase Ordering Rationale

- Phase 1 blocks everything — it's the compatibility contract every other phase depends on.
- Phases 2 and 3 do not block each other (could be parallelized) — sequenced 2-then-3 here because Phase 2 has zero external-service risk and validates the FNAMES-only reporting pattern before Phase 3's higher-risk MCP integration.
- Phase 4 is pure extension with no new dependencies, deferred by design per the feature research's "Add After Validation" tier.
- Resume/skip-already-built (v2+) and auto-cleanup are explicitly out of scope for this milestone's roadmap — the feature research's own MVP definition defers them until the staleness predicate is trusted.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (ICAO resolution + radius build):** Geodesy edge cases (antimeridian, floor() vs int(), radius unit definition) are well-documented here but implementation-specific test fixtures (exact ICAO codes, exact tile math) warrant a research-phase pass before planning.

Phases with standard patterns (skip research-phase):
- **Phase 1 (CLI dispatch):** Hybrid sys.argv-then-argparse dispatch is a well-established pattern, fully specified in ARCHITECTURE.md and PITFALLS.md already.
- **Phase 2 (tile inventory report):** Filesystem-scan-through-FNAMES pattern is fully specified; no external unknowns.
- **Phase 4 (report refinements):** Pure extension of Phase 2's established pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Primary-source reads of `mcp_aviation_server`'s own source (`server.py`, `config.py`), official FastMCP docs, PyPI registry checks |
| Features | MEDIUM | No direct in-ecosystem CLI competitor exists; triangulated from GUI precedent, one third-party tool (xOrganizer), and general CLI conventions (terraform/ansible/rsync) |
| Architecture | HIGH | Based on direct reading of `Ortho4XP.py`, `O4_File_Names.py`, `O4_Geo_Utils.py`, and `mcp_aviation_server` source, plus this repo's existing curated `.planning/codebase/` maps |
| Pitfalls | MEDIUM-HIGH | Geodesy/argparse patterns are well-established; MCP-coupling and artifact-scan findings are grounded directly in this codebase's own code and documented anti-patterns (bare-except count from CONCERNS.md) |

**Overall confidence:** HIGH

### Gaps to Address

- **Disk-overlap report scope:** "Overlap" must be precisely reinterpreted as stale/redundant artifacts within a single tile (old provider's DDS not cleaned after a rebuild), not geometric tile overlap (which cannot happen in Ortho4XP's fixed 1°×1° grid). Confirm this definition explicitly during Phase 4 planning before any implementation.
- **Batch-ICAO partial-failure behavior:** Research doesn't settle whether one failed ICAO in a batch list should abort the whole batch or skip-and-continue with a per-ICAO report. Flag this as an explicit design decision during Phase 3 planning (PITFALLS.md's "Looks Done But Isn't" checklist calls this out).
- **`build_tile_list`'s existing bare-`except:` behavior:** The CLI inherits this pipeline-level anti-pattern by design (fixing it is out of scope — pipeline change, not orchestration). Note as a known limitation, not a defect to silently work around.

## Sources

### Primary (HIGH confidence)
- `Ortho4XP.py`, `src/O4_File_Names.py`, `src/O4_Geo_Utils.py`, `src/O4_Tile_Utils.py` (this repo, read directly)
- `C:/Users/WillMcBurnett/dev/mcp_aviation_server/src/mcp_aviation/server.py` and `config.py` (read directly, same-org sibling repo)
- https://gofastmcp.com/clients/client — official FastMCP docs
- https://pypi.org/pypi/fastmcp/json — version 3.4.7, checked 2026-08-24
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md` (this repo's curated codebase maps)
- https://docs.python.org/3/howto/argparse-optparse.html

### Secondary (MEDIUM confidence)
- xOrganizer v3 review (X-PlaneReviews forum) — "Scenery Coverage" feature precedent
- Flusiboard GUI batch-build description
- General GIS/geodesy knowledge (degree-to-nm conversion, antimeridian bbox handling) cross-checked via web search
- General CLI convention knowledge (terraform/ansible/rsync dry-run/resume patterns)

### Tertiary (LOW confidence)
- OrthoForge community fork context — surfaced via search snippet only, not independently verified

---
*Research completed: 2026-08-24*
*Ready for roadmap: yes*
