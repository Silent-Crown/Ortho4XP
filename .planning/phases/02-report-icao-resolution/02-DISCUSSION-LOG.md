# Phase 2: Report & ICAO Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 2-Report & ICAO Resolution
**Areas discussed:** ICAO resolver transport, "Tile complete" predicate, Report command surface, Coverage-by-ICAO semantics

---

## ICAO Resolver Transport

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP call to the server | Talk to mcp_aviation_server over HTTP (its primary Docker/HTTP mode) | ✓ |
| Read aviation.db directly | Open the SQLite file with stdlib sqlite3 | |
| Spawn STDIO subprocess | Launch the server as a stdio MCP subprocess | |

**User's choice:** HTTP call to the server
**Notes:** Cleanest decoupling; matches the server's stated primary deployment.

| Option | Description | Selected |
|--------|-------------|----------|
| Trimmed offline CSV | Ship a small ICAO→lat/lon CSV as fallback | |
| No fallback, clear error | Fail specific + non-zero on unreachable/unknown | ✓ |
| You decide | Defer to research | |

**User's choice:** No fallback, clear error
**Notes:** Single source of truth; never a silent wrong result.

| Option | Description | Selected |
|--------|-------------|----------|
| Official MCP/FastMCP client | Add the mcp/fastmcp client SDK dependency | |
| Minimal hand-rolled HTTP | Minimal JSON-RPC over the /mcp endpoint using requests | ✓ |
| You decide | Defer to research | |

**User's choice:** Minimal hand-rolled HTTP
**Notes:** No new runtime dependency; matches the repo's plain-requests grain.

| Option | Description | Selected |
|--------|-------------|----------|
| Env var + default | ORTHO4XP_AVIATION_URL with localhost default | |
| Ortho4XP.cfg setting | Config var via O4_Cfg_Vars | ✓ |
| CLI flag | --aviation-url per invocation | |

**User's choice:** Ortho4XP.cfg setting

---

## "Tile Complete" Predicate

| Option | Description | Selected |
|--------|-------------|----------|
| DSF exists + non-empty | Present non-zero DSF is the marker | |
| DSF + textures present | Require valid DSF AND non-empty textures/ | ✓ |
| You decide | Defer to research | |

**User's choice:** DSF + textures present

| Option | Description | Selected |
|--------|-------------|----------|
| Just flag partial/leftovers | Structural problems only, no time-based staleness | ✓ |
| Partial + age threshold | Also flag DSF older than N days | |
| Partial + source-newer | Flag when .cfg/source newer than DSF | |

**User's choice:** Just flag partial/leftovers

| Option | Description | Selected |
|--------|-------------|----------|
| Tile dir, no valid DSF | Reuse the predicate only | |
| Also scan tmp/ + Data files | Additionally flag orphaned tmp/ and Data* intermediates | ✓ |
| You decide | Defer to research | |

**User's choice:** Also scan tmp/ + Data files

---

## Report Command Surface

| Option | Description | Selected |
|--------|-------------|----------|
| One `report` + subcommands | report tiles / coverage / health under one namespace | ✓ |
| Three top-level commands | report-tiles / report-coverage / report-health | |
| You decide | Defer to planning | |

**User's choice:** One `report` + subcommands

| Option | Description | Selected |
|--------|-------------|----------|
| Per-tile .cfg + DSF mtime | provider/zoom from cfg, build-date from DSF mtime, size from dir sum | ✓ |
| Parse DDS filenames + mtime | derive provider/zoom from DDS filenames | |
| You decide | Defer to research | |

**User's choice:** Per-tile .cfg + DSF mtime
**Notes:** Read the cfg as plain text — do not import the config side-effect module (RPT-01).

---

## Coverage-by-ICAO Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Containing tile only | Report the single floored containing tile | |
| Containing + 8 neighbors | Report containing tile plus 8 adjacent tiles | ✓ |
| You decide | Defer to planning | |

**User's choice:** Containing + 8 neighbors
**Notes:** Airports/approaches straddle tile edges.

| Option | Description | Selected |
|--------|-------------|----------|
| built / partial / missing | Reuse the shared predicate's vocabulary | ✓ |
| Built / not-built (binary) | Simple yes/no | |
| You decide | Defer to planning | |

**User's choice:** built / partial / missing

---

## Claude's Discretion

- Exact table column layout/ordering for report tiles and report coverage.
- Error message wording (distinguish "server unreachable" vs "ICAO unknown").
- Internal module organization for the resolver and tile-scan predicate helpers.

## Deferred Ideas

- `--radius N`, multi-ICAO, list-file batch — Phase 3.
- Trimmed offline CSV fallback — rejected here; revisit only if HTTP proves unreliable.
- `--json` / `--dry-run` — v1.x.
- Detail-zone report, disk-overlap report — v1.x.
- Time-based / source-newer staleness — v2+.
