# Architecture Research

**Domain:** CLI orchestration + read-only reporting layer over an existing flat-module Python build tool (Ortho4XP)
**Researched:** 2026-08-24
**Confidence:** HIGH — based on direct reading of `Ortho4XP.py`, `src/O4_File_Names.py`, `src/O4_Geo_Utils.py`, `src/O4_Tile_Utils.py` call shape, and the `mcp_aviation_server` source (Silent-Crown, local clone).

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Ortho4XP.py  (entry point, UNCHANGED shape)                         │
│  if no args        → GUI.Ortho4XP_GUI()               [unchanged]    │
│  elif argv[1] is int → legacy positional build          [unchanged]  │
│  else                → O4_CLI_Utils.main(argv[1:])      [NEW]        │
└───────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  O4_CLI_Utils.py  (CLI)  NEW  │
                  │  argparse subparsers:         │
                  │   build | build-icao | report │
                  │  — no build/report logic here │
                  │  — just parses + dispatches    │
                  └───────┬───────────────┬───────┘
                          │               │
              ┌───────────┘               └───────────┐
              ▼                                        ▼
  ┌─────────────────────────┐            ┌──────────────────────────┐
  │ O4_ICAO_Utils.py  NEW    │            │ O4_Report_Utils.py  NEW  │
  │ resolve_icao(icao)       │            │ scan_tiles() -> [record] │
  │  → MCP client call to    │            │  read-only, FNAMES only  │
  │    mcp_aviation_server   │            │  no CFG/VMAP/MESH/GUI    │
  └───────────┬──────────────┘            └────────────┬─────────────┘
              │ (lat, lon)                              │
              ▼                                         │
  ┌─────────────────────────┐                           │
  │ O4_Geo_Utils.py  EXT     │                           │
  │ + containing_tile()      │                           │
  │ + tiles_in_radius()  NEW │                           │
  └───────────┬──────────────┘                           │
              │ [(lat,lon), ...]                          │
              ▼                                           │
  ┌─────────────────────────────────────┐                 │
  │ Existing build pipeline (UNCHANGED)  │                 │
  │ CFG.Tile(...) → TILE.build_tile_list │                 │
  │  (VMAP → MESH → MASK → TILE per tile)│                 │
  └───────────────┬───────────────────────┘                │
                  ▼                                        ▼
       Tiles/zOrtho4XP_±lat±lon/  ◄─────── read by ─────────┘
       (DSF, textures/, cfg, node/poly/mesh)
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| `Ortho4XP.py` entry | Decide GUI vs legacy-positional vs new-CLI, nothing else | 3-way branch on `sys.argv`, unchanged import order (CFG last) |
| `O4_CLI_Utils.py` (CLI) | Build `argparse` parser + subparsers, validate args, call one handler function per subcommand, print/format nothing build-specific itself | Thin dispatcher module, mirrors how `Ortho4XP.py` is already a thin entry over `O4_*` modules |
| `O4_ICAO_Utils.py` (ICAO) | ICAO string → `(lat, lon)` via `mcp_aviation_server`; nothing else | Async MCP client call wrapped in a sync function (`asyncio.run`) |
| `O4_Geo_Utils.py` (GEO, extended) | Pure tile-grid math: which 1°×1° tile contains a coordinate, which tiles fall within a radius | Two new stdlib-only functions, no I/O |
| Existing `TILE.build_tile_list()` | Loop over resolved `(lat, lon)` list, run the 4-stage pipeline per tile | Already exists — reused, not reimplemented |
| `O4_Report_Utils.py` (REPORT) | Read-only inventory of `Tiles/` on disk: which tiles exist, DSF/DDS presence, mtimes, sizes | Filesystem walk + `FNAMES` path functions + tiny per-tile `.cfg` key=value parser (not `CFG.Tile`) |

## Recommended Project Structure

```
src/
├── O4_CLI_Utils.py       # NEW — argparse parser, subcommand dispatch table
├── O4_ICAO_Utils.py       # NEW — ICAO → (lat, lon) via mcp_aviation_server
├── O4_Report_Utils.py     # NEW — read-only tile inventory scan + record shape
├── O4_Geo_Utils.py        # EXTENDED — + containing_tile(), tiles_in_radius()
├── O4_File_Names.py        # UNCHANGED — path authority, both build & report read it
├── O4_Tile_Utils.py        # UNCHANGED — build_tile_list() reused as-is
├── O4_Config_Utils.py      # UNCHANGED — CFG.Tile still owns build-side config
└── ...existing O4_* modules unchanged
Ortho4XP.py                 # + one elif branch, existing branches untouched
```

### Structure Rationale

- **One new module per concern, following the existing `O4_<Thing>_Utils.py` naming and two-letter-alias convention** (`CLI`, `ICAO`, `REPORT`) — this is how every existing component in the codebase is organized; inventing a `cli/` or `commands/` package would break the flat-module pattern the whole repo uses and buys nothing at this size (23 modules today, 4 more is not a reason to nest).
- **`O4_Report_Utils.py` does not import `O4_Config_Utils` (CFG), `O4_GUI_Utils` (GUI), or any build-stage module.** CFG's import triggers `exec()`-based mutation of module-level variables in `IMG`, `MESH`, etc. (see codebase ARCHITECTURE.md, "Import Order Matters"). A read-only report command that just wants to list what's on disk has no business paying that cost or risking that side effect — it reads `.cfg` files itself with a few lines of key=value parsing, and reads paths through `FNAMES` only.
- **Radius/containing-tile math lives in `O4_Geo_Utils.py`, not in `O4_ICAO_Utils.py`.** It's generic 1°×1° tile-grid arithmetic, not ICAO-specific — the existing "Where to Add New Code" convention in CONVENTIONS.md already says general-purpose math that doesn't fit elsewhere goes there. Keeps `O4_ICAO_Utils.py` a single-purpose adapter: string in, coordinate out.
- **The legacy positional branch in `Ortho4XP.py` is not touched.** Compatibility is enforced by leaving that code byte-for-byte as-is and adding a new `elif` that only fires when `int(sys.argv[1])` fails — the same disambiguation signal the app already uses (lat is parsed with `int()`, so a subcommand name like `build-icao` naturally falls through).

## Architectural Patterns

### Pattern 1: Legacy-shim dispatch by parse-success, not by flag

**What:** `Ortho4XP.py` tries `int(sys.argv[1])` first (exactly what it does today). Success → existing legacy path, completely unchanged. Failure → hand the full `sys.argv[1:]` to `CLI.main()`, which owns its own `argparse.ArgumentParser(prog="Ortho4XP.py")` with subparsers.

**When to use:** Any time you're bolting a modern CLI onto a tool with an existing positional-args contract you must not break, and the old and new grammars are lexically distinguishable (here: int vs. word).

**Trade-offs:** Dead simple, zero risk to existing behavior, no new dependency. Downside: `--help` at the top level can't show both grammars in one `argparse` usage string — acceptable since the legacy form is being superseded, not advertised.

**Example:**
```python
# Ortho4XP.py — only new code, existing branches untouched
else:
    try:
        lat = int(sys.argv[1])
        # ... existing legacy branch, unchanged ...
    except ValueError:
        import O4_CLI_Utils as CLI
        sys.exit(CLI.main(sys.argv[1:]))
```

### Pattern 2: Command handlers call existing pipeline entry points, never pipeline internals

**What:** `build-icao` and any future batch subcommand resolve a list of `(lat, lon)` and hand it to `O4_Tile_Utils.build_tile_list(tile, list_lat_lon, do_osm, do_mesh, do_mask, do_dsf, do_ovl, override_cfg)` — the same function the GUI's batch-build button already calls. No subcommand handler calls `VMAP.build_poly_file` / `MESH.build_mesh` / etc. directly.

**When to use:** Whenever the new orchestration layer needs to build more than one tile. `build_tile_list` already owns per-tile config reload, stage sequencing, and error handling for batches.

**Trade-offs:** Means the CLI inherits `build_tile_list`'s existing bare-`except:` behavior on a bad tile (documented anti-pattern in codebase ARCHITECTURE.md) rather than getting cleaner per-tile error reporting for free. Fixing that is out of scope for this milestone (it's a pipeline change, not orchestration) — flag it as a known limitation, don't silently reimplement the loop just to get better errors.

**Example:**
```python
# O4_CLI_Utils.py — build-icao handler
def _handle_build_icao(args):
    lat, lon = ICAO.resolve_icao(args.icao)
    tiles = GEO.tiles_in_radius(*GEO.containing_tile(lat, lon), args.radius)
    tile = CFG.Tile(tiles[0][0], tiles[0][1], "")
    TILE.build_tile_list(tile, tiles, True, True, True, True, False, False)
```

### Pattern 3: Report records built from a filesystem scan, not from build-time state

**What:** `O4_Report_Utils.scan_tiles()` globs `Tiles/zOrtho4XP_*` under `FNAMES.Tile_dir`, reverses `short_latlon` to recover `(lat, lon)` per directory, then checks concrete artifacts through `FNAMES` functions (`dsf_file`, tile's `textures/` dir) with `os.path.exists` / `os.stat`. It never trusts an in-memory "did the last build succeed" flag — there isn't one that survives process exit, and the whole point of report commands is inspecting state days/weeks after a build ran.

**When to use:** Any "what's already built" question. This is the only pattern that's honest about the fact that Ortho4XP has no build database — the filesystem *is* the database.

**Trade-offs:** A partially-written tile (crashed mid-DSF-write) looks the same as "not started" unless the scanner also checks for the `.dsf.tmp` staging file `O4_Tile_Utils` uses before its atomic rename — worth checking for explicitly since it's a real, named intermediate state, not a hypothetical one.

## Data Flow

### Build Flow (ICAO → tiles on disk)

```
"KJFK" (CLI arg)
    ↓
ICAO.resolve_icao("KJFK")          → (40.64, -73.78)   [MCP call, async→sync bridge]
    ↓
GEO.containing_tile(lat, lon)      → (40, -73)          [floor(), matches SW-corner tile convention]
    ↓
GEO.tiles_in_radius(40, -73, r)    → [(40,-73), (40,-74), (41,-73), ...]   [pure grid math]
    ↓
CFG.Tile(lat0, lon0, '')           → seed Tile instance  [existing class, existing config load]
    ↓
TILE.build_tile_list(tile, [...]) → VMAP → MESH → MASK → TILE, per tile  [existing pipeline, untouched]
    ↓
Tiles/zOrtho4XP_±lat±lon/ (DSF + textures/)   [existing output layout, untouched]
```

### Report Flow (tile dirs → inventory)

```
Tiles/  (filesystem)
    ↓
REPORT.scan_tiles()
    ├─ os.listdir(FNAMES.Tile_dir), filter zOrtho4XP_* dirs
    ├─ parse ±lat±lon back out of each dir name
    ├─ FNAMES.dsf_file(build_dir, lat, lon) → exists? size? mtime?
    ├─ textures/ dir → *.dds count, total bytes
    └─ per-tile .cfg (if present) → provider, zl  [tiny local parse, not CFG.Tile]
    ↓
list[TileRecord]                    [plain dataclass/namedtuple, one per built tile dir]
    ↓
CLI report subcommand (coverage / health / detail-areas / overlap)
    ↓
formatted stdout (table / one-line-per-tile)
```

**Key coupling:** both flows depend on `FNAMES` for path construction and nothing else in common — this is intentional and is why they can be built and tested independently.

## Scaling Considerations

Not applicable in the traditional sense — this is a single-user local CLI tool, not a service. The only "scale" axis that matters:

| Scale | Consideration |
|-------|----------------|
| Few tiles (1–20) | `scan_tiles()` doing a full `os.listdir` + per-tile `stat` calls every invocation is fine, no caching needed |
| Whole-world batch (hundreds/thousands of tiles) | If `report` becomes slow at that scale, the fix is a `--filter` on ICAO/region before scanning, not a cache layer — don't build caching pre-emptively |

## Anti-Patterns

### Anti-Pattern 1: Report commands importing `O4_Config_Utils` for convenience

**What people do:** Instantiate `CFG.Tile(lat, lon, custom_build_dir)` inside a report handler because it's the "normal" way to get a tile's config values.

**Why it's wrong:** `CFG`'s module import runs `exec()` statements that mutate other modules' globals (documented in codebase ARCHITECTURE.md's "Import Order Matters" / "Module-Level State Mutation" anti-pattern) — importing it purely to read a report has side effects far beyond "read a file," and it also drags in the GUI import chain since `CFG` and `GUI` are mutually referenced in `Ortho4XP.py`'s import block.

**Do this instead:** Report code reads the per-tile `.cfg` file itself (it's `key=value` text, trivial to parse with a few lines) or just checks artifact presence without needing config values at all for most report questions (coverage, staleness, disk usage).

### Anti-Pattern 2: Reimplementing the 4-stage build loop in the CLI layer

**What people do:** Because `Ortho4XP.py`'s legacy branch calls `VMAP.build_poly_file` → `MESH.build_mesh` → `MASK.build_masks` → `TILE.build_tile` directly, it's tempting to copy that sequence into a new `build-icao` handler for "control."

**Why it's wrong:** Duplicates logic that already exists in `TILE.build_tile_list()` (used by the GUI's batch button), meaning any future fix to batch behavior (retry logic, stage flags, per-tile config reload) has to be made twice and will drift. This milestone is explicitly orchestration-only — see PROJECT.md Out of Scope: "Changing the build pipeline algorithms."

**Do this instead:** Always call `TILE.build_tile_list()` for anything building more than the single tile the legacy branch already handles.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| `mcp_aviation_server` (Silent-Crown) | MCP protocol tool call (`get_airport_details(ident)`), **not** a plain REST endpoint | The server only exposes `@mcp.tool()` async functions over stdio or HTTP+SSE MCP transport — confirmed by reading its `server.py` and README. There is no `/api/airports/{icao}` REST route; `/health` is the only plain HTTP endpoint. `O4_ICAO_Utils.resolve_icao()` must embed an actual MCP client (`mcp` SDK) and bridge async→sync with `asyncio.run()` since the rest of Ortho4XP is fully synchronous/thread-based, not asyncio. Wrap this behind the single `resolve_icao(icao) -> (lat, lon)` function so the PROJECT.md-flagged fallback (local dataset if the integration proves too heavy) only requires swapping this module's internals, not any caller. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `CLI` ↔ `ICAO` / `GEO` / `REPORT` | Direct function calls, plain Python types in/out (`str` → `(float, float)`, `int` → `list[tuple]`, `()` → `list[TileRecord]`) | No shared mutable state between them — each is independently testable with no monkeypatching of module globals |
| `CLI` ↔ existing pipeline (`CFG`, `TILE`) | Direct function calls, using the exact same objects/functions the GUI already uses | This is the "don't reimplement" boundary — treat `CFG.Tile` + `TILE.build_tile_list` as a stable API the CLI consumes, not something to reach past |
| `REPORT` ↔ `FNAMES` | Direct function calls only, no filesystem paths hardcoded in `REPORT` | Matches the existing codebase-wide rule that `FNAMES` is the single source of truth for paths |
| `REPORT` ↔ everything else (`CFG`, `GUI`, `VMAP`/`MESH`/`MASK`/`TILE`) | **None** | Deliberate — see Anti-Pattern 1 |

## Suggested Build Order

1. **CLI dispatch skeleton** (`O4_CLI_Utils.py` + the one new `elif` in `Ortho4XP.py`) — everything else plugs into this; ship it with just a `build` subcommand that's a thin passthrough to the existing single-tile legacy logic (refactored into one shared helper function so both the legacy branch and the new `build` subcommand call it — still zero change to behavior). Validates the dispatch/compatibility pattern before anything else depends on it.
2. **Tile-inventory scanner + `report` subcommand (coverage first)** — depends only on step 1 and `FNAMES`, nothing else new. No external service risk. Delivers standalone user value (coverage-by-ICAO, health/staleness) even if ICAO resolution isn't done yet, as long as coverage-by-ICAO's *lookup* falls back to "user passes lat/lon directly" until step 3 lands.
3. **ICAO resolver + radius math + `build-icao`/batch subcommand** — depends on step 1's dispatch and the existing `build_tile_list`; independent of step 2. This is the highest-risk step (new async MCP client dependency, external service must be reachable) — worth sequencing early relative to the *remaining* report refinements below, specifically to surface integration problems (auth, transport, availability) while there's still roadmap room to fall back to a local dataset per PROJECT.md's stated contingency.
4. **Report refinements** (detail areas, disk overlap) — pure extensions of step 2's scanner/record shape; no new components, no new external dependencies. Safe to defer to the end.

**Dependency summary:** step 1 blocks everything. Steps 2 and 3 do not block each other and could be parallelized across two workstreams if desired. Step 4 only extends step 2.

## Sources

- `Ortho4XP.py` (read directly) — confirms legacy dispatch is `int(sys.argv[1])`-gated, import order, GUI/CFG coupling. Confidence: HIGH (primary source).
- `src/O4_File_Names.py` (read directly) — confirms `FNAMES` functions are pure/stateless path builders; `dsf_file`, `tile_dir`, `short_latlon` usable without a `Tile`/`CFG` instance. Confidence: HIGH.
- `src/O4_Geo_Utils.py` (read directly, function list) — confirms no existing "containing 1°×1° tile" helper; nearest analog (`wgs84_to_gtile`) is web-mercator-ZL tile math, a different concept — new functions are additive, not duplicative. Confidence: HIGH.
- `C:/Users/WillMcBurnett/dev/mcp_aviation_server` (local clone, `README.md` + `src/mcp_aviation/server.py` read directly) — confirms MCP-protocol-only tool interface (`get_airport_details`, `find_nearby_airports`), stdio/HTTP+SSE transports, no REST data endpoint. Confidence: HIGH (primary source, same-org repo).
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md` (this repo's existing codebase maps) — component responsibilities, naming conventions, documented anti-patterns (module-level state mutation via `CFG` import, bare `except:`). Confidence: HIGH (curated first-party analysis of this exact codebase).

---
*Architecture research for: CLI orchestration + reporting layer, Ortho4XP*
*Researched: 2026-08-24*
