# Phase 2: Report & ICAO Resolution - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a **read-only** reporting layer over the existing FNAMES tile inventory, plus
the ICAO→lat/lon resolver that Phase 3's builds will reuse (proven here first).
Delivers RPT-01, RPT-02, RPT-03, BUILD-01:

- BUILD-01: Resolve an ICAO to lat/lon via `mcp_aviation_server`; unreachable/unknown
  fails with a clear, specific error — never a silent wrong result.
- RPT-01: List built tiles with provider, zoom, build date, on-disk size — read through
  `O4_File_Names` (FNAMES), without importing the build/config side-effect modules.
- RPT-02: Coverage-by-ICAO — is a given airport's tile(s) already built?
- RPT-03: Health/staleness report flagging partial builds and crashed-run leftovers via
  one shared "is this tile complete" predicate.

All commands are read-only (no side effects). Actual ICAO-driven builds, `--radius`,
multi-ICAO, and list-file batch runs are Phase 3. `--json` / `--dry-run` are v1.x-deferred.

</domain>

<decisions>
## Implementation Decisions

### ICAO Resolver (BUILD-01)
- **D-01:** Resolve ICAO via an **HTTP call to `mcp_aviation_server`** (its primary
  Docker/HTTP deployment mode), not by reading `aviation.db` directly and not by spawning
  a STDIO subprocess. — **Reversibility:** costly — swapping the data source later means
  rewriting the resolver and its config; Phase 3 depends on this same resolver.
- **D-02:** **Minimal hand-rolled MCP-over-HTTP** client using `requests` (already a dep).
  No new MCP/FastMCP client dependency. The CLI performs the minimal JSON-RPC calls needed
  for the one airport-resource lookup against the server's streamable-HTTP endpoint.
- **D-03:** Server location is an **`Ortho4XP.cfg` setting** declared in `O4_Cfg_Vars.py`
  (not an env var, not a per-command flag). Read it without triggering config side-effect
  mutation where possible.
- **D-04:** **No local/offline fallback.** If the server is unreachable or the ICAO is
  unknown, fail with a clear, specific message and a **non-zero exit** — never a silent or
  wrong coordinate. (Rejects the trimmed-CSV option; keeps a single source of truth.)

### "Tile Complete" Predicate (shared by RPT-01 + RPT-03)
- **D-05:** A tile is **built** iff it has a valid **non-empty `.dsf`** under
  `Earth nav data/` **AND** a **non-empty `textures/`** directory. Missing either = partial.
  This single predicate is the shared backbone of the inventory, coverage, and health reports.
- **D-06:** Health/staleness is scoped to **structural problems only** — partial tiles and
  crashed-run leftovers. **No time-based staleness** (no age threshold, no source-newer
  comparison); avoids guessing a meaningful age.
- **D-07:** A **crashed-run leftover** = a `Tiles/zOrtho4XP_*` dir failing the D-05
  predicate, **plus** orphaned intermediates: leftover `tmp/` (FNAMES `Tmp_dir`) contents
  and `Data*.poly/.node/.ele/.mesh` files in a tile build dir with no resulting DSF.

### Report Command Surface (RPT-01/02/03)
- **D-08:** Nest reports under a single **`report`** subcommand:
  `report tiles`, `report coverage --icao <CODE>`, `report health`. Keeps `build` clean
  and leaves room to grow; matches Phase 1's nested-subparser dispatch in `O4_CLI_Utils.py`.
- **D-09:** Inventory facts derive from: **provider + zoom from the per-tile
  `zOrtho4XP_<latlon>.cfg`** (read as plain text — do NOT import `O4_Config_Utils`),
  **build-date from the DSF file mtime**, **on-disk size from summing the tile directory**.
- **D-10:** Output is a **human-readable aligned text table**. `--json` stays v1.x-deferred.

### Coverage-by-ICAO Semantics (RPT-02)
- **D-11:** Coverage checks the ICAO's **containing tile plus its 8 adjacent neighbors**
  (airports/approaches straddle tile edges), reporting each tile as
  **built / partial / missing** using the D-05 shared predicate for consistent vocabulary
  across all three reports.

### Claude's Discretion
- Exact table column layout/ordering for `report tiles` and `report coverage`.
- Error message wording (must be specific enough to distinguish "server unreachable" from
  "ICAO unknown" per D-04).
- Internal module organization within/alongside `O4_CLI_Utils.py` (e.g. whether the
  resolver and the tile-scan predicate live in new small helper modules).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase planning
- `.planning/ROADMAP.md` §"Phase 2: Report & ICAO Resolution" — goal + success criteria
- `.planning/REQUIREMENTS.md` — RPT-01/02/03, BUILD-01, and the v1.x/out-of-scope lines
  (offline CSV allowed but rejected here; `--json`/`--dry-run` deferred)
- `.planning/phases/01-cli-dispatch-compatibility/01-CONTEXT.md` — Phase 1 CLI decisions
  the report subcommands extend

### ICAO resolver
- `../mcp_aviation_server/README.md` — transport modes (streamable-HTTP default in prod),
  resource surface (`airport://{ident}`, radius search by lat/lon), config env vars
  (`MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`, `MCP_PATH`)
- `../mcp_aviation_server/CLAUDE.md` — "primary deployment is Docker image in HTTP mode;
  default mode Streaming-HTTP, not STDIO"

### Codebase (paths + conventions)
- `src/O4_File_Names.py` — FNAMES path authority: `Tile_dir`, `tile_dir()`, `build_dir()`,
  `dsf_file()`, `short_latlon()`, `long_latlon()`, `Tmp_dir` — use these, never hardcode paths
- `src/O4_CLI_Utils.py` — Phase 1 argparse dispatch + `run_and_report` error/exit wrapper to extend
- `src/O4_Cfg_Vars.py` — where the aviation-server-URL config var is declared
- `.planning/codebase/INTEGRATIONS.md` — existing external-service patterns (all use `requests`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `O4_CLI_Utils.build_parser()` — extend the subparser tree with a `report` subcommand.
- `O4_CLI_Utils.run_and_report()` — reuse verbatim as the error/traceback/non-zero-exit
  wrapper for the new report + resolve commands (satisfies BUILD-01's clear-error rule).
- `O4_CLI_Utils.parse_and_floor_coord()` — reuse to floor a resolved ICAO lat/lon to its
  containing tile (coverage) with correct negative-hemisphere handling.
- FNAMES: `Tile_dir`, `tile_dir(lat,lon)`, `build_dir()`, `dsf_file(build_dir,lat,lon)`,
  `Tmp_dir` — the tile-scan predicate and inventory walk build entirely on these.
- `requests` (existing dep, used in `O4_Imagery_Utils` / `O4_OSM_Utils`) for the HTTP resolver.

### Established Patterns
- Two-letter uppercase module aliases; a resolver/report helper would follow the `O4_*`
  naming and be imported by alias.
- **`O4_Config_Utils` (CFG) must remain imported last** — RPT-01 explicitly forbids
  importing the build/config side-effect modules for reads; parse per-tile `.cfg` as plain
  text (key=value, `#` comments) instead of via CFG.
- External services in this repo are all plain `requests` calls (Overpass, imagery, DEM) —
  the hand-rolled HTTP resolver matches that grain.

### Integration Points
- New commands hang off the argparse tree in `O4_CLI_Utils.dispatch()` / `build_parser()`.
- Aviation-server URL read from the global `Ortho4XP.cfg` via the var declared in `O4_Cfg_Vars`.
- Tile inventory reads the `Tiles/` directory tree through FNAMES path helpers.

</code_context>

<specifics>
## Specific Ideas

- Command shapes the user has in mind: `report tiles`, `report coverage --icao KJFK`,
  `report health`.
- Error wording must let a script distinguish "aviation server unreachable" from
  "ICAO unknown" (both non-zero exit, but different messages).
- The three reports must speak the same status vocabulary — built / partial / missing —
  because they share one predicate (D-05).

</specifics>

<deferred>
## Deferred Ideas

- `--radius N` neighbor builds, multi-ICAO, list-file batch — Phase 3 (BUILD-02..05).
- Trimmed offline ICAO CSV fallback — allowed by REQUIREMENTS but rejected here (D-04);
  revisit only if the HTTP integration proves unreliable for unattended runs.
- `--json` output and `--dry-run` — v1.x-deferred per REQUIREMENTS.md.
- Detail-zone report and disk-overlap/redundant-artifact report — v1.x-deferred.
- Time-based / source-newer staleness — explicitly out of scope for this phase (D-06);
  needs a trusted staleness predicate first (noted for v2+).

None outside milestone scope surfaced during discussion.

</deferred>

---

*Phase: 2-Report & ICAO Resolution*
*Context gathered: 2026-08-24*
