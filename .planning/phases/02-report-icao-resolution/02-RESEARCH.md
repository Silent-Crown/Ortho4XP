# Phase 2: Report & ICAO Resolution - Research

**Researched:** 2026-08-24
**Domain:** Read-only CLI reporting over the FNAMES tile inventory + a hand-rolled MCP-over-HTTP (JSON-RPC / streamable-HTTP) ICAO resolver against `mcp_aviation_server`
**Confidence:** HIGH (all wire-protocol, tool, and path facts verified against source read this session)

## Summary

Phase 2 adds three read-only `report` subcommands and one ICAO→lat/lon resolver, all
built on code that already exists in the repo. The tile inventory, coverage, and health
reports share one "is this tile built" predicate over FNAMES paths; no build/config
side-effect modules are imported. The resolver is a minimal `requests`-based MCP client —
no new dependency — that speaks JSON-RPC to the aviation server's streamable-HTTP endpoint.

**The single most important correction to the locked context:** `mcp_aviation_server`
exposes **MCP tools, not resources**. There is **no `airport://{ident}` resource** anywhere
in the server (`grep` for `@mcp.resource` returns nothing; every airport lookup is an
`@mcp.tool()` function). CONTEXT D-01/D-02 describe resolving "via the `airport://{ident}`
resource" — that resource does not exist. The correct wire call is
`tools/call` → `get_airport_details(ident=...)`, whose response carries the coordinates.
The *decision* (hand-rolled `requests` client, HTTP transport, one lookup) still holds
verbatim; only the JSON-RPC method changes from `resources/read` to `tools/call`.

**A second correction:** the per-tile config file is named **`Ortho4XP_<latlon>.cfg`**, not
`zOrtho4XP_<latlon>.cfg`. The `z` prefix is on the tile *directory* (`zOrtho4XP_<latlon>/`);
the config file inside it drops the `z`. D-09 names the wrong file — the planner must use
`Ortho4XP_<latlon>.cfg`.

**Primary recommendation:** Add a small `O4_Report_Utils` (tile scan + predicate + table
formatting) and `O4_ICAO_Utils` (hand-rolled MCP client + resolver), hang a `report`
subparser and (optionally) the resolver call off `O4_CLI_Utils.build_parser()`, and wrap
every new command in the existing `run_and_report()`. No new pip packages.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Resolve ICAO via an **HTTP call to `mcp_aviation_server`** (its primary Docker/HTTP
  deployment mode), not by reading `aviation.db` directly and not by spawning a STDIO
  subprocess. Reversibility: costly — Phase 3 depends on this same resolver.
- **D-02:** **Minimal hand-rolled MCP-over-HTTP** client using `requests` (already a dep). No
  new MCP/FastMCP client dependency. The CLI performs the minimal JSON-RPC calls needed for
  one airport lookup against the server's streamable-HTTP endpoint.
- **D-03:** Server location is an **`Ortho4XP.cfg` setting** declared in `O4_Cfg_Vars.py` (not
  an env var, not a per-command flag). Read it without triggering config side-effect mutation
  where possible.
- **D-04:** **No local/offline fallback.** Server unreachable OR ICAO unknown → clear,
  specific message + **non-zero exit**; never a silent or wrong coordinate.
- **D-05:** A tile is **built** iff it has a valid **non-empty `.dsf`** under `Earth nav data/`
  **AND** a **non-empty `textures/`** directory. Missing either = partial. This single
  predicate is the shared backbone of inventory, coverage, and health.
- **D-06:** Health/staleness is **structural problems only** — partial tiles and crashed-run
  leftovers. **No time-based staleness.**
- **D-07:** A **crashed-run leftover** = a `Tiles/zOrtho4XP_*` dir failing the D-05 predicate,
  **plus** orphaned intermediates: leftover `tmp/` (FNAMES `Tmp_dir`) contents and
  `Data*.poly/.node/.ele/.mesh` files in a tile build dir with no resulting DSF.
- **D-08:** Nest reports under a single **`report`** subcommand: `report tiles`,
  `report coverage --icao <CODE>`, `report health`.
- **D-09:** Inventory facts derive from: **provider + zoom from the per-tile config**
  (read as plain text — do NOT import `O4_Config_Utils`), **build-date from the DSF file
  mtime**, **on-disk size from summing the tile directory**.
- **D-10:** Output is a **human-readable aligned text table**. `--json` stays v1.x-deferred.
- **D-11:** Coverage checks the ICAO's **containing tile plus its 8 adjacent neighbors**,
  reporting each as **built / partial / missing** using the D-05 predicate.

### Claude's Discretion
- Exact table column layout/ordering for `report tiles` and `report coverage`.
- Error message wording (must distinguish "server unreachable" from "ICAO unknown" per D-04).
- Internal module organization within/alongside `O4_CLI_Utils.py` (whether resolver and
  tile-scan predicate live in new small helper modules).

### Deferred Ideas (OUT OF SCOPE)
- `--radius N` neighbor builds, multi-ICAO, list-file batch — Phase 3 (BUILD-02..05).
- Trimmed offline ICAO CSV fallback — allowed by REQUIREMENTS but rejected here (D-04).
- `--json` output and `--dry-run` — v1.x-deferred.
- Detail-zone report and disk-overlap/redundant-artifact report — v1.x-deferred.
- Time-based / source-newer staleness — explicitly out of scope (D-06).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUILD-01 | Resolve an ICAO to lat/lon via `mcp_aviation_server`; unreachable/unknown fails with a clear message, never a silent wrong result | Wire protocol + `get_airport_details` tool + 3-way error classification (§ICAO Resolver). Coordinates at `response.airport.coordinates.latitude/longitude` `[VERIFIED: mcp_aviation_server/src/mcp_aviation/models.py:68-71]` |
| RPT-01 | List built tiles with provider, zoom, build date, on-disk size — via FNAMES, no build/config side-effect imports | Tile scan of `Tiles/zOrtho4XP_*` + plain-text parse of `Ortho4XP_<latlon>.cfg` (§Tile Inventory) |
| RPT-02 | Coverage-by-ICAO — is a given airport's tile(s) already built? | Resolver → floor to tile via `parse_and_floor_coord` → D-05 predicate over the 3×3 tile block (§Coverage) |
| RPT-03 | Health/staleness report flagging partial builds + crashed-run leftovers via one shared predicate | Shared `is_tile_built()` predicate + leftover scan (§Health) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Argparse `report` subtree + dispatch | CLI entry (`O4_CLI_Utils`) | — | Phase 1 owns dispatch; extend its parser tree `[VERIFIED: src/O4_CLI_Utils.py:44-60]` |
| Error/traceback/non-zero-exit wrapping | CLI entry (`O4_CLI_Utils.run_and_report`) | — | Reuse verbatim; satisfies BUILD-01 + CLI-03 `[VERIFIED: src/O4_CLI_Utils.py:93-105]` |
| Tile inventory / D-05 predicate / health scan | New helper (`O4_Report_Utils`) | FNAMES (paths) | Pure filesystem read over FNAMES; no build modules |
| Per-tile provider/zoom read | New helper | plain-text `.cfg` parse | RPT-01 forbids importing `O4_Config_Utils` |
| ICAO → lat/lon resolution | New helper (`O4_ICAO_Utils`) | `requests` (HTTP), aviation server (data) | Data owned by external service; client is a thin transport |
| Path/naming authority | FNAMES (`O4_File_Names`) | — | Single source of truth; never hardcode paths |
| Aviation-server URL setting | Config declaration (`O4_Cfg_Vars`) | plain-text `Ortho4XP.cfg` read | D-03: declared centrally, read without CFG side effects |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib (3.13) | `report` subparser + dispatch | Locked by `.claude/CLAUDE.md` ("stdlib argparse, no new CLI framework"); Phase 1 already uses it `[VERIFIED: src/O4_CLI_Utils.py:4]` |
| `requests` | 2.33.1 | Hand-rolled MCP-over-HTTP client | Already a pinned dep `[VERIFIED: requirements.txt:4]`; every external service in-repo uses it `[CITED: .planning/codebase/INTEGRATIONS.md]` |
| `json` | stdlib | JSON-RPC encode + parse tool response | stdlib |
| `os` / `os.path` / `os.scandir` | stdlib | Tile-dir walk, mtime, size sum | stdlib; FNAMES already builds on `os.path` `[VERIFIED: src/O4_File_Names.py:1-3]` |
| `math.floor` | stdlib (via `parse_and_floor_coord`) | Floor resolved lat/lon to containing tile | Reuse Phase 1 helper `[VERIFIED: src/O4_CLI_Utils.py:9-32]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `O4_File_Names` (FNAMES) | in-repo | All tile/DSF/tmp path construction | Every path — inventory, predicate, coverage, health |
| `O4_UI_Utils` (UI) | in-repo | `vprint`/`lvprint` messaging consistent with repo | Optional; report output can also use plain `print` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `requests` JSON-RPC | `fastmcp` / `mcp` client SDK | Rejected by D-02 (no new dep). SDK would also pull async + pydantic transitive weight for one blocking call. |
| `get_airport_details` tool | `search_airports` tool | `search_airports` is fuzzy `LIKE` and returns a list (ambiguous); `get_airport_details` is an exact-ident lookup that raises a clean "not found" — the precise signal D-04 needs `[VERIFIED: mcp_aviation_server/src/mcp_aviation/server.py:404-420]` |
| Plain-text `.cfg` parse | `O4_Config_Utils.Tile.read_from_config` | Rejected by RPT-01 (side-effect import forbidden; CFG mutates module globals via `exec` at import `[VERIFIED: src/O4_Config_Utils.py:96-102]`) |

**Installation:** None. No new packages. (`requests==2.33.1` already present.)

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** All code uses the Python
standard library plus the already-pinned `requests==2.33.1`. No `pip install` / `uv add`
step is required or permitted (D-02). No legitimacy check needed.

## The ICAO Resolver (BUILD-01) — Wire Protocol

### What the server actually exposes

`mcp_aviation_server` is a **FastMCP 2.x/3.x server exposing tools only**. Verified facts:

- `grep -r "@mcp.resource|resources/read|add_resource"` over `src/` → **no matches**. There
  is **no `airport://{ident}` resource**. `[VERIFIED: mcp_aviation_server/src — grep this session]`
- The airport lookup is a tool: `async def get_airport_details(ident: str) -> str`
  `[VERIFIED: mcp_aviation_server/src/mcp_aviation/server.py:404]`
- Installed transport stack: `fastmcp==3.1.0`, `mcp==1.26.0`
  `[VERIFIED: mcp_aviation_server/.venv — dist-info this session]`
- Default deployment is **HTTP / streamable-HTTP**, not STDIO
  `[CITED: mcp_aviation_server/CLAUDE.md:10-13]` and docker-compose runs `MCP_TRANSPORT=http`
  `[VERIFIED: mcp_aviation_server/docker/docker-compose.yml:17]`

### Endpoint & config defaults

`[VERIFIED: mcp_aviation_server/src/mcp_aviation/config.py:115-124]` — `MCPConfig` defaults,
quoted verbatim:

```
transport: str = "stdio"   # overridden to "http" in prod
host: str = "127.0.0.1"
port: int = 8000
path: str = "/mcp"
```

Env overrides (aliases) `[VERIFIED: config.py:207-210]`: `MCP_TRANSPORT`, `MCP_HOST`,
`MCP_PORT`, `MCP_PATH`. Docker default `[VERIFIED: docker-compose.yml:18-20]`:
`MCP_HOST=0.0.0.0`, `MCP_PORT=8000`, `MCP_PATH=/mcp`.

**Default resolver URL to recommend:** `http://127.0.0.1:8000/mcp`. (This is the value the
`Ortho4XP.cfg` setting from D-03 should default to.)

> Trailing-slash note: the streamable-HTTP ASGI app mounts at the path; a POST to `/mcp`
> (no trailing slash) can 307-redirect to `/mcp/`. `requests` follows 307 preserving method,
> body, and headers by default, so either form works. Keep `allow_redirects=True` (default).

### Protocol versions

`[VERIFIED: mcp_aviation_server/.venv/.../mcp/types.py:27,35]`:
```
LATEST_PROTOCOL_VERSION = "2025-11-25"
DEFAULT_NEGOTIATED_VERSION = "2025-03-26"
```
Send `"protocolVersion": "2025-06-18"` (a stable, widely-supported value ≤ latest) in
`initialize`; the server negotiates and echoes its chosen version. Use whatever it returns
in the `MCP-Protocol-Version` header on subsequent requests (or just echo `2025-06-18`).

### The minimal JSON-RPC call sequence (streamable-HTTP, stateful)

Streamable-HTTP requires a 3-step handshake before the tool call. All POSTs go to the same
URL. Required headers on every POST: `Content-Type: application/json` and
`Accept: application/json, text/event-stream` (the client MUST advertise both — the server
replies with an SSE stream by default).

1. **initialize** — establishes the session; the response carries `Mcp-Session-Id`.
   ```json
   {"jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{"protocolVersion":"2025-06-18","capabilities":{},
              "clientInfo":{"name":"Ortho4XP","version":"1.0"}}}
   ```
   Capture the `Mcp-Session-Id` **response header**. (Response body is SSE; its content can
   be ignored beyond confirming HTTP 200.)

2. **notifications/initialized** — a notification (no `id`); server returns `202 Accepted`,
   empty body. Include the `Mcp-Session-Id` header.
   ```json
   {"jsonrpc":"2.0","method":"notifications/initialized"}
   ```

3. **tools/call** — the actual lookup. Include `Mcp-Session-Id` and
   `MCP-Protocol-Version` headers.
   ```json
   {"jsonrpc":"2.0","id":2,"method":"tools/call",
    "params":{"name":"get_airport_details","arguments":{"ident":"KJFK"}}}
   ```

> **Robustness:** if `initialize` returns no `Mcp-Session-Id` (stateless mode), skip step 2
> and omit the header — proceed straight to `tools/call`. Capturing-if-present handles both
> modes with one code path.

### Parsing the streamable-HTTP (SSE) response

The `tools/call` response `Content-Type` is `text/event-stream`. Body looks like:
```
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"<JSON string>"}],"isError":false}}

```
Parse: iterate `resp.text` lines, take those starting with `data:`, strip the prefix,
`json.loads`. (Handle `Content-Type: application/json` too — some deploys enable JSON-response
mode — by parsing `resp.text` directly when it is not `text/event-stream`.)

The tool's return value is a **JSON string** nested at `result.content[0].text`
`[VERIFIED: server.py:404-439 returns `response.model_dump_json()`]`. `json.loads` that inner
string to get the airport payload.

### Success payload shape

On success the inner JSON is an `AirportDetailsResponse`
`[VERIFIED: mcp_aviation_server/src/mcp_aviation/models.py:1086-1096]` — keys verbatim:
`airport`, `runways`, `communications`, `approaches`. Coordinates live at
`airport.coordinates.latitude` / `airport.coordinates.longitude`
`[VERIFIED: models.py:68-71, 134-137]` (DB columns `laty`→`latitude`, `lonx`→`longitude`).

Minimal extraction: `data["airport"]["coordinates"]["latitude"]`,
`data["airport"]["coordinates"]["longitude"]`.

### Distinguishing the failure modes (D-04)

The tool **never raises to the MCP layer** — it catches everything and returns an
`ErrorResponse` JSON string with HTTP 200 and `isError: false`
`[VERIFIED: server.py:441-453]`. So the CLI **cannot** rely on `isError`; it must inspect the
inner payload. `ErrorResponse` keys verbatim `[VERIFIED: models.py:1485-1490]`: `error`,
`code`, `details`.

Three cases the resolver must separate:

| Case | Wire signal | Detect by | D-04 action |
|------|-------------|-----------|-------------|
| **Server unreachable** | `requests.exceptions.ConnectionError` / `Timeout` (connection refused, DNS fail, timeout); or non-200 / non-MCP HTTP; or top-level JSON-RPC `error` object | Exception at transport, or `"error"` key in the JSON-RPC envelope | "aviation server unreachable at `<url>`" + exit non-zero |
| **Server up but DB unavailable** | inner payload `code == "SIM_DB_UNAVAILABLE"` `[VERIFIED: server.py:391,447]` | inner `code` field | same "unreachable/unavailable" family, distinct wording (include reason) + exit non-zero |
| **ICAO unknown** | inner payload `code == "AIRPORT_DETAILS_ERROR"`, `error == "Airport not found: <IDENT>"` `[VERIFIED: server.py:420,451]` | inner `code`/`error` fields | "ICAO `<CODE>` not found" + exit non-zero |
| **Success** | inner payload has non-null `airport` with `coordinates` | `"airport" in data and data["airport"]` | return `(lat, lon)` |

This is exactly the "distinguish unreachable from unknown, both non-zero exit, different
messages" behavior the CONTEXT requires.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────────────────┐
  CLI argv  ──▶ dispatch(argv)  [O4_CLI_Utils]                          │
                        │  legacy-sniff first, then argparse             │
                        ├── build ───────────────▶ (Phase 1, unchanged) │
                        │                                                │
                        ├── report tiles ─────┐                         │
                        ├── report coverage   │   run_and_report(fn)     │
                        │        --icao KJFK  │   (traceback+exit1)      │
                        └── report health ────┘                         │
                        └──────────────────────────────────────────────┘
                                 │                          │
             ┌───────────────────┘                          └────────────────┐
             ▼                                                                 ▼
   ┌──────────────────────────┐                              ┌──────────────────────────────┐
   │ O4_Report_Utils          │                              │ O4_ICAO_Utils                 │
   │  scan Tiles/zOrtho4XP_*   │◀── FNAMES paths ──▶          │  read server URL (plain-text  │
   │  is_tile_built()  (D-05)  │    (O4_File_Names)           │   Ortho4XP.cfg)               │
   │  parse Ortho4XP_<ll>.cfg  │                              │  requests: initialize →       │
   │   (provider/zoom, D-09)   │                              │   initialized → tools/call    │
   │  dsf mtime + dir size     │                              │  parse SSE → classify errors  │
   │  leftover scan (D-07)     │                              └───────────────┬──────────────┘
   └───────────┬──────────────┘                                              │ HTTP JSON-RPC
               │ filesystem (read-only)                                       ▼
               ▼                                              ┌──────────────────────────────┐
   Tiles/zOrtho4XP_<latlon>/                                  │ mcp_aviation_server (Docker)  │
     ├── Earth nav data/<round>/<latlon>.dsf                  │  streamable-HTTP /mcp :8000    │
     ├── textures/                                            │  tool get_airport_details     │
     ├── terrain/                                             └──────────────────────────────┘
     └── Ortho4XP_<latlon>.cfg
```

`report coverage` uses **both** helpers: resolver → `parse_and_floor_coord` → 3×3 tile block
→ `is_tile_built()` for each.

### Recommended Project Structure
```
src/
├── O4_CLI_Utils.py      # extend build_parser() + dispatch() with `report` subtree
├── O4_Report_Utils.py   # NEW: tile scan, is_tile_built() predicate, table format, health
├── O4_ICAO_Utils.py     # NEW: hand-rolled MCP client + resolve_icao() + error classes
└── O4_Cfg_Vars.py       # add aviation-server-URL app var (D-03)
```
Splitting resolver and report into two small modules keeps the HTTP/JSON concern away from
the filesystem concern and matches the repo's one-domain-per-`O4_*`-module convention. (This
is Claude's discretion per CONTEXT; a single `O4_Report_Utils` holding both is also valid but
mixes concerns.)

### Pattern 1: Shared "is tile built" predicate (D-05)
**What:** One function every report calls; returns a status in a fixed vocabulary.
**When to use:** inventory, coverage, health — all three.
**Example:**
```python
# built / partial / missing — the shared vocabulary (D-05, D-11)
import os
import O4_File_Names as FNAMES

def tile_status(lat, lon):
    build_dir = FNAMES.build_dir(lat, lon, "")          # Tiles/zOrtho4XP_<latlon>
    if not os.path.isdir(build_dir):
        return "missing"
    dsf = FNAMES.dsf_file(build_dir, lat, lon)          # .../Earth nav data/<round>/<latlon>.dsf
    tex = os.path.join(build_dir, "textures")
    dsf_ok = os.path.isfile(dsf) and os.path.getsize(dsf) > 0
    tex_ok = os.path.isdir(tex) and any(os.scandir(tex))
    return "built" if (dsf_ok and tex_ok) else "partial"
```
Path facts verified: `build_dir` → `os.path.join(Tile_dir, tile_dir(lat, lon))`
`[VERIFIED: src/O4_File_Names.py:71-77]`; `tile_dir` → `"zOrtho4XP_" + short_latlon(lat, lon)`
`[VERIFIED: src/O4_File_Names.py:67-68]`; `dsf_file` →
`os.path.join(build_dir, "Earth nav data", long_latlon(lat, lon) + ".dsf")`
`[VERIFIED: src/O4_File_Names.py:205-208]`; the `textures` dir is literally
`os.path.join(tile.build_dir, "textures")` created at build
`[VERIFIED: src/O4_Tile_Utils.py:167-168]`.

### Pattern 2: Enumerate built tiles from the directory names
**What:** Walk `Tiles/`, match `zOrtho4XP_<latlon>`, recover `(lat, lon)` from the suffix.
**Example:**
```python
import os, re
import O4_File_Names as FNAMES

# short_latlon(lat, lon) = "{:+.0f}".format(lat).zfill(3) + "{:+.0f}".format(lon).zfill(4)
#   e.g. lat=47, lon=-122 -> "+47-122" -> dir "zOrtho4XP_+47-122"
_TILE_RE = re.compile(r"^zOrtho4XP_([+-]\d{2,})([+-]\d{3,})$")

def iter_tiles():
    if not os.path.isdir(FNAMES.Tile_dir):
        return
    for entry in os.scandir(FNAMES.Tile_dir):
        m = _TILE_RE.match(entry.name)
        if entry.is_dir() and m:
            yield int(m.group(1)), int(m.group(2)), entry.path
```
`Tile_dir = resource_path("Tiles")` `[VERIFIED: src/O4_File_Names.py:30]`. `short_latlon`
format verified `[VERIFIED: src/O4_File_Names.py:35-38]`.

### Pattern 3: Plain-text per-tile config read (D-09) — provider + zoom
**What:** Read `default_website` (provider) and `default_zl` (zoom) from the per-tile config
**as plain text**, never via `O4_Config_Utils`.
**Critical file-name fact:** the file is **`Ortho4XP_<latlon>.cfg`** (no leading `z`), inside
the `zOrtho4XP_<latlon>/` directory `[VERIFIED: src/O4_Config_Utils.py:192-195, 1060-1063]`.
D-09 says `zOrtho4XP_<latlon>.cfg` — that is wrong; use `Ortho4XP_<latlon>.cfg`.
**Example:**
```python
import os

def read_tile_cfg(build_dir, lat, lon):
    # matches CFG's own reader: strip, skip blanks, skip '#', split on first '='
    path = os.path.join(build_dir, "Ortho4XP_" + short_latlon(lat, lon) + ".cfg")
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line[0] == "#":
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return out  # out.get("default_website"), out.get("default_zl")
```
The per-tile config contains `default_website` and `default_zl` because both are in
`list_tile_vars` and written verbatim by `write_to_config`
`[VERIFIED: src/O4_Cfg_Vars.py:441-448; src/O4_Config_Utils.py:272-289]`. The plain-text
line format (`key=value`, `#` comments, `split("=", 1)`) mirrors CFG's own loop
`[VERIFIED: src/O4_Config_Utils.py:207-229]` and the global `Ortho4XP.cfg`
`[VERIFIED: Ortho4XP.cfg:1-57]`.

### Pattern 4: Inventory facts (D-09)
- **provider** = `default_website`, **zoom** = `default_zl` (Pattern 3).
- **build date** = DSF file mtime: `os.path.getmtime(FNAMES.dsf_file(build_dir, lat, lon))`.
- **on-disk size** = sum of file sizes walked under `build_dir` (`os.walk` + `getsize`).

### Pattern 5: Coverage 3×3 block (D-11)
```python
import O4_CLI_Utils as CLI  # parse_and_floor_coord for hemisphere-correct floor

def coverage_tiles(lat_f, lon_f):
    base_lat = CLI.parse_lat(str(lat_f))     # floor to containing tile
    base_lon = CLI.parse_lon(str(lon_f))
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            yield base_lat + dlat, base_lon + dlon   # containing + 8 neighbors
```
`parse_lat`/`parse_lon`/`parse_and_floor_coord` verified
`[VERIFIED: src/O4_CLI_Utils.py:9-40]`. (Antimeridian/pole clamping is a v1.x concern; Phase 2
coverage over a real airport's neighbors is safe — note it as an Open Question if a tile falls
outside `[-90,89]×[-180,179]`.)

### Pattern 6: Extend the argparse tree (D-08)
`build_parser()` already creates `subparsers = parser.add_subparsers(dest="command", required=True)`
`[VERIFIED: src/O4_CLI_Utils.py:50]`. Add a `report` parser with its own nested subparsers:
```python
report_p = subparsers.add_parser("report", help="Read-only terrain reports")
report_sub = report_p.add_subparsers(dest="report_cmd", required=True)
report_sub.add_parser("tiles", help="List built tiles")
cov = report_sub.add_parser("coverage", help="Is an ICAO's tile(s) built?")
cov.add_argument("--icao", required=True, help="Airport ICAO code")
report_sub.add_parser("health", help="Flag partial builds / crashed-run leftovers")
```
Then in `dispatch()`, after `args = build_parser().parse_args(argv)`, branch on
`args.command == "report"` and `args.report_cmd`, each wrapped in
`run_and_report(...)` `[VERIFIED: src/O4_CLI_Utils.py:142-154]`.

### Anti-Patterns to Avoid
- **Importing `O4_Config_Utils` (CFG) to read a tile config.** Its module body runs
  `exec()`-based mutation of other modules at import `[VERIFIED: src/O4_Config_Utils.py:96-102]`
  and it pulls in Tkinter, IMG, DEM, TILE, etc. — forbidden by RPT-01. Parse plain text.
- **Relying on `result.isError` to detect unknown ICAO.** The server returns `isError:false`
  even for "not found" `[VERIFIED: server.py:441-453]`. Parse the inner payload.
- **Assuming an `airport://{ident}` resource.** It does not exist; use `tools/call`.
- **Hardcoding tile paths.** Always go through FNAMES.
- **Adding a new pip dependency for MCP.** D-02 forbids it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hemisphere-correct floor of resolved lat/lon to tile | Custom `int()`/rounding | `O4_CLI_Utils.parse_and_floor_coord` | Already correct for negatives via `math.floor` `[VERIFIED: src/O4_CLI_Utils.py:9-32]`; `int()` truncates toward zero (the CLI-04 bug) |
| Error → traceback → non-zero exit | New try/except per command | `O4_CLI_Utils.run_and_report` | Reuse verbatim `[VERIFIED: src/O4_CLI_Utils.py:93-105]`; passes `SystemExit` through so argparse usage errors stay intact |
| Tile/DSF/tmp path strings | String concatenation | FNAMES helpers | Single source of truth; nested `Earth nav data/<round>/` layout is non-obvious `[VERIFIED: src/O4_File_Names.py:47-52,205-208]` |
| HTTP client | Async MCP SDK | `requests` (blocking, one call) | D-02; one lookup does not justify async + a new dep |
| Config value type coercion for the URL | Custom parser | plain `str` (URL is a string) | The URL is a `str` app var; no coercion needed |

**Key insight:** Nearly everything Phase 2 needs already exists (parser tree, error wrapper,
coord floor, path authority). The only genuinely new logic is (a) ~40 lines of MCP-over-HTTP
client and (b) the D-05 predicate + directory walk. Keep both minimal.

## Config Declaration (D-03)

Declare the URL as an app var in `O4_Cfg_Vars.cfg_app_vars`
`[VERIFIED: src/O4_Cfg_Vars.py:16-116]`, e.g.:
```python
"mcp_aviation_server_url": {
    "type": str,
    "default": "http://127.0.0.1:8000/mcp",
    "hint": "Base URL of the mcp_aviation_server streamable-HTTP endpoint used to resolve ICAO codes to coordinates.",
},
```
**Reading without CFG side effects (D-03):** the value lands in `Ortho4XP.cfg` as a plain
`mcp_aviation_server_url=...` line. The resolver reads it with the same plain-text parser used
for per-tile configs (`FNAMES.resource_path("Ortho4XP.cfg")`), falling back to the default
when the key is absent (existing `Ortho4XP.cfg` files predate the var). Importing
`O4_Cfg_Vars` for the default value is safe (it only declares dicts + imports `O4_OSM_Utils`);
importing `O4_Config_Utils` is not.

**GUI-coupling gotcha (flag for planner):** the Application Config tab renders vars from
`list_app_vars`, and `gui_app_vars_long = list_app_vars[-3:]` picks the *last three* for
folder-picker rows `[VERIFIED: src/O4_Cfg_Vars.py:363-384]`. Appending the URL to
`list_app_vars` would shift which three get folder pickers and add a text row to the GUI.
Two options: (a) add to both `cfg_app_vars` and `list_app_vars` (URL appears in GUI, is
persisted by "Save App Config", but must be inserted *before* the last three to avoid the
folder-picker shift), or (b) add only to `cfg_app_vars` (declared + has a default + readable,
but not shown/persisted by the GUI). Option (b) is the smaller, lower-risk change for a
CLI-only setting; the plain-text reader + default covers persistence. Planner decides.

## Runtime State Inventory

Phase 2 is **additive, read-only, greenfield** — it renames nothing and migrates no data.
The categories are answered for completeness:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — reports only read the existing `Tiles/` tree; nothing is written or migrated. | None |
| Live service config | The aviation server is an external dependency, not managed by Ortho4XP. Its URL becomes a new `Ortho4XP.cfg` key (created on next global-config write; absent keys fall back to the default). | None (default handles absence) |
| OS-registered state | None — no scheduled tasks, services, or daemons introduced. | None |
| Secrets/env vars | None — aviation server needs no auth `[CITED: mcp_aviation_server/README.md:668 "read-only access"]`; the URL is not a secret. | None |
| Build artifacts | None produced by this phase. It *reads* build artifacts (DSF, textures, `Data*` intermediates) but creates none. | None |

## Crashed-Run Leftover Detection (D-07)

A crashed run leaves identifiable orphans. Verified intermediate artifacts:

- **DSF activation is a rename from `.tmp`:** `os.replace(dsf_file_name + ".tmp", dsf_file_name)`
  `[VERIFIED: src/O4_Tile_Utils.py:250]`. A crash mid-build can leave
  `Earth nav data/<round>/<latlon>.dsf.tmp` with no final `.dsf` → strong crash signal.
- **`Data*` intermediates in the build dir** `[VERIFIED: src/O4_File_Names.py:92-202]`,
  extensions verbatim: `.poly`, `.node`, `.ele`, `.mesh`, `.alt`, `.apt`, `.weight`, prefixed
  `Data` + `short_latlon`. Present with no resulting DSF ⇒ leftover.
- **`tmp/` contents** — `Tmp_dir = resource_path("tmp")` `[VERIFIED: src/O4_File_Names.py:31]`;
  a top-level project dir, not per-tile. Non-empty `tmp/` is a global leftover signal.
- **`textures/` / `terrain/` dirs** created early in the tile step
  `[VERIFIED: src/O4_Tile_Utils.py:167-183]`; an empty `textures/` beside a missing DSF ⇒
  partial/crashed.

Health = for every `Tiles/zOrtho4XP_*`: run the D-05 predicate; if `partial`, additionally
report which orphan classes are present (`.dsf.tmp`, `Data*`, empty `textures/`). Report
non-empty `Tmp_dir` once, globally.

## Common Pitfalls

### Pitfall 1: Expecting an MCP resource
**What goes wrong:** Building `resources/read` with `uri: airport://KJFK` — returns a
JSON-RPC error; the server has no resources.
**Why:** CONTEXT D-02 wording; the server is tools-only.
**How to avoid:** Use `tools/call` → `get_airport_details`.
**Warning signs:** JSON-RPC error `-32602` / "Unknown resource" / empty resource list.

### Pitfall 2: Wrong per-tile config filename
**What goes wrong:** Opening `zOrtho4XP_<latlon>.cfg` → `FileNotFoundError`; provider/zoom
show blank.
**Why:** The `z` is on the directory, not the file. File is `Ortho4XP_<latlon>.cfg`.
**How to avoid:** `os.path.join(build_dir, "Ortho4XP_" + short_latlon(lat,lon) + ".cfg")`.
**Warning signs:** every tile reports "unknown provider" despite a valid build.

### Pitfall 3: Trusting `isError` for unknown ICAO
**What goes wrong:** Treating a "not found" response as success because `isError == false`.
**Why:** The tool catches its own `ValueError` and returns an `ErrorResponse` string normally.
**How to avoid:** `json.loads` the inner `content[0].text`; branch on its `error`/`code` keys.
**Warning signs:** unknown ICAOs silently resolve to `None`/garbage coordinates.

### Pitfall 4: Missing the streamable-HTTP handshake / headers
**What goes wrong:** POSTing `tools/call` directly → 400 "Missing session ID" or "Received
request before initialization complete"; or 406 for a missing `Accept: text/event-stream`.
**Why:** Streamable-HTTP is session-based and content-negotiated.
**How to avoid:** Do `initialize` → capture `Mcp-Session-Id` → `notifications/initialized` →
`tools/call`, all with `Accept: application/json, text/event-stream`.
**Warning signs:** HTTP 400/406 before any airport data.

### Pitfall 5: Forgetting to parse SSE framing
**What goes wrong:** `json.loads(resp.text)` fails because the body is
`event: message\ndata: {...}\n\n`, not raw JSON.
**How to avoid:** extract `data:` lines when `Content-Type` is `text/event-stream`.
**Warning signs:** `json.JSONDecodeError: Expecting value: line 1`.

### Pitfall 6: Importing a build/config module and triggering side effects
**What goes wrong:** `import O4_Config_Utils` mutates module globals via `exec` and drags in
Tkinter — violates RPT-01 and can crash headless.
**How to avoid:** plain-text parse; only import FNAMES, UI, and (optionally) O4_Cfg_Vars.

## Code Examples

### Minimal hand-rolled resolver (skeleton)
```python
# O4_ICAO_Utils.py  — hand-rolled MCP-over-HTTP client (D-02). No new deps.
import json
import requests

class AviationServerUnreachable(Exception): pass   # -> "server unreachable" (D-04)
class ICAONotFound(Exception): pass                 # -> "ICAO unknown"       (D-04)

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

def _parse_body(resp):
    ctype = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ctype:
        chunks = [ln[5:].strip() for ln in resp.text.splitlines()
                  if ln.startswith("data:")]
        return json.loads("".join(chunks))
    return resp.json()

def resolve_icao(ident, base_url, timeout=10.0):
    ident = ident.strip().upper()
    s = requests.Session()
    try:
        # 1. initialize
        init = s.post(base_url, headers=_HEADERS, timeout=timeout, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "Ortho4XP", "version": "1.0"}}})
        init.raise_for_status()
        sid = init.headers.get("Mcp-Session-Id")
        hdr = dict(_HEADERS, **{"MCP-Protocol-Version": "2025-06-18"})
        if sid:
            hdr["Mcp-Session-Id"] = sid
            # 2. initialized notification
            s.post(base_url, headers=hdr, timeout=timeout,
                   json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        # 3. tools/call
        r = s.post(base_url, headers=hdr, timeout=timeout, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "get_airport_details", "arguments": {"ident": ident}}})
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise AviationServerUnreachable(f"aviation server unreachable at {base_url}: {e}")

    env = _parse_body(r)
    if "error" in env:                                     # JSON-RPC transport error
        raise AviationServerUnreachable(f"aviation server error: {env['error']}")
    payload = json.loads(env["result"]["content"][0]["text"])
    if payload.get("airport"):
        c = payload["airport"]["coordinates"]
        return c["latitude"], c["longitude"]
    code = payload.get("code")
    if code == "AIRPORT_DETAILS_ERROR":
        raise ICAONotFound(f"ICAO {ident} not found")
    # SIM_DB_UNAVAILABLE and any other server-side code -> unreachable/unavailable family
    raise AviationServerUnreachable(
        f"aviation server could not answer ({code}): {payload.get('error')}")
```
Source-grounded: tool name/args + coordinate path `[VERIFIED: server.py:404-439; models.py:68-71]`;
error codes `[VERIFIED: server.py:420,447,451]`; header/handshake `[CITED: MCP streamable-HTTP
transport spec]` cross-checked with installed `mcp==1.26.0` / `fastmcp==3.1.0`.

The caller wraps this in `run_and_report`, converting each exception into a specific stderr
message + `sys.exit(1)`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MCP HTTP+SSE (two endpoints: `/sse` + `/messages`) | Streamable-HTTP (single endpoint, `Mcp-Session-Id`, SSE responses) | MCP spec 2025-03-26 | README still mentions the old `/mcp/sse` Inspector URL `[CITED: mcp_aviation_server/README.md:440]`; the *server* runs streamable-HTTP. Client must target `/mcp`, not `/mcp/sse`. |
| `resources/read airport://{ident}` (assumed) | `tools/call get_airport_details` | n/a — server never had the resource | Resolver method changes from the CONTEXT assumption. |

**Deprecated/outdated:** the README's SSE-transport Inspector instructions (`.../mcp/sse`,
"Transport: SSE") describe legacy MCP transport, superseded by streamable-HTTP per the repo's
own CLAUDE.md `[CITED: mcp_aviation_server/CLAUDE.md:10-13]`.

## API Coverage Decision (api_coverage_gate active)

The resolver integrates an external API, so the plan needs an INTEGRATE/OPT-OUT decision over
the server's capability surface. Full tool inventory
`[VERIFIED: mcp_aviation_server/src/mcp_aviation/server.py]`:

| Tool | Purpose | Phase 2 decision |
|------|---------|------------------|
| `get_airport_details(ident)` | Airport incl. coordinates | **INTEGRATE** — the one call BUILD-01 needs |
| `search_airports(query, limit)` | Fuzzy name/ident/city search | OPT-OUT (ambiguous; exact lookup preferred) |
| `find_nearby_airports(lat, lon, radius)` | Radius search (nm) | OPT-OUT (Phase 3 `--radius` is *whole tiles*, not nm; different model) |
| `get_airport_runways` / `_communications` / `_approaches` / `_parking` | Airport detail sub-queries | OPT-OUT (not needed for coord resolution) |
| `get_waypoint_info` / `get_navaid_info` | Nav fixes | OPT-OUT |
| `get_approaches_with_transitions` / `get_approach_transitions_legs` / `get_approach` | Procedure detail | OPT-OUT |
| `list_simulators` / `get_active_simulator` / `set_active_simulator` | Multi-sim profile mgmt | OPT-OUT (server-side concern; default profile is fine) |

**Recommendation: INTEGRATE `get_airport_details` only; OPT-OUT the rest.** Document the
OPT-OUT so the planner records a deliberate coverage decision rather than an accidental gap.

## Validation Architecture

nyquist_validation is enabled `[VERIFIED: .planning/config.json workflow.nyquist_validation:true]`.
**There is no existing test suite, framework, or config in Ortho4XP** — the repo runs from
source (`.claude/CLAUDE.md`: "There is no test suite, linter config, or build step"). The
only in-repo test idiom is `assert`-based `if __name__ == "__main__"` self-checks
`[VERIFIED: src/O4_CLI_Utils.py:158-178]`. Global rules mandate `uv` + venv + `pytest`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (per global Python rules) — **none installed yet; Wave 0 must add it** (`uv add --dev pytest`) |
| Config file | none — add `[tool.pytest.ini_options]` or a `tests/` dir |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |
| Fallback (no pytest) | extend the existing `__main__` `assert` self-checks in each new module (matches repo idiom, zero deps) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RPT-01 | `is_tile_built` returns built/partial/missing over fixture tile dirs | unit | `pytest tests/test_report_utils.py -x` | ❌ Wave 0 |
| RPT-01 | provider/zoom parsed from `Ortho4XP_<latlon>.cfg` plain text | unit | `pytest tests/test_report_utils.py::test_read_tile_cfg -x` | ❌ Wave 0 |
| RPT-01 | dir-name → (lat,lon) recovery incl. negatives (`zOrtho4XP_+47-122`) | unit | `pytest tests/test_report_utils.py::test_iter_tiles -x` | ❌ Wave 0 |
| RPT-02 | resolver→floor→3×3 block statuses over fixtures (mocked resolver) | unit | `pytest tests/test_coverage.py -x` | ❌ Wave 0 |
| RPT-03 | leftover detection flags `.dsf.tmp` / `Data*` / empty `textures/` | unit | `pytest tests/test_health.py -x` | ❌ Wave 0 |
| BUILD-01 | success path returns (lat,lon) from mocked SSE `tools/call` body | unit | `pytest tests/test_icao.py::test_resolve_ok -x` | ❌ Wave 0 |
| BUILD-01 | ConnectionError/Timeout → `AviationServerUnreachable` | unit | `pytest tests/test_icao.py::test_unreachable -x` | ❌ Wave 0 |
| BUILD-01 | inner `AIRPORT_DETAILS_ERROR` → `ICAONotFound` | unit | `pytest tests/test_icao.py::test_unknown_icao -x` | ❌ Wave 0 |
| BUILD-01 | SSE framing parsed from `data:` lines | unit | `pytest tests/test_icao.py::test_parse_sse -x` | ❌ Wave 0 |

Mock strategy: use `unittest.mock`/`responses`-style monkeypatch of `requests.Session.post`
to return canned SSE/JSON bodies — no live server needed. Fixture tile dirs: `tmp_path`
pytest fixture creating `Tiles/zOrtho4XP_+47-122/Earth nav data/+40-130/+47-122.dsf` +
`textures/` (built), and variants missing each (partial), and `.dsf.tmp`/`Data*` (leftover).

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (all new tests run in <1s; no I/O beyond tmp).
- **Per wave merge:** `pytest tests/`.
- **Phase gate:** full suite green + each new module's `__main__` self-check runs clean
  (`python src/O4_Report_Utils.py`, `python src/O4_ICAO_Utils.py`) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `uv add --dev pytest` (+ optional `pytest`-mock) — no test framework installed
- [ ] `tests/` dir + `tests/conftest.py` — shared fixture tile-dir factory + canned SSE bodies
- [ ] `tests/test_report_utils.py`, `tests/test_coverage.py`, `tests/test_health.py`,
      `tests/test_icao.py`
- [ ] (fallback if pytest is rejected) add `__main__` `assert` self-checks to both new modules

## Security Domain

security_enforcement enabled, ASVS level 1 `[VERIFIED: .planning/config.json]`.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Aviation server is unauthenticated read-only `[CITED: mcp_aviation_server/README.md:668]` |
| V3 Session Management | no | MCP `Mcp-Session-Id` is transport bookkeeping, not a user session |
| V4 Access Control | no | Reports are local, read-only |
| V5 Input Validation | yes | Validate/normalise the ICAO argument (`strip().upper()`, length ≤ 10) before sending; validate resolved lat/lon are finite and in range before flooring |
| V6 Cryptography | no | No secrets, no crypto; URL is not sensitive |
| V7 Error Handling & Logging | yes | Specific-but-not-leaky error messages (D-04); don't dump full tracebacks to users beyond `run_and_report`'s stderr |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via a user-controlled server URL | Tampering / Info-disclosure | URL comes from `Ortho4XP.cfg` (operator-set), not per-command input; document that it must point at a trusted local/LAN server. Low risk (no per-request URL override in Phase 2). |
| Untrusted response payload (server compromised/typo'd URL) | Tampering | Treat the aviation payload as untrusted input: check `airport`/`coordinates` keys exist and lat/lon are finite numbers in range before use; never `eval`. |
| DoS via unbounded/hung HTTP | DoS | Explicit `timeout=` on every `requests` call (repo default `http_timeout=10.0` `[VERIFIED: src/O4_Cfg_Vars.py:69-74]`); one attempt, fail fast per D-04. |
| Path traversal from tile dir names | Tampering | Tile names are matched by a strict `^zOrtho4XP_[+-]\d+[+-]\d+$` regex before use; `(lat,lon)` are ints; paths built via FNAMES. |
| Untrusted `.cfg` content on disk | Tampering | Read config as plain text with `split("=", 1)` — no `exec`/`eval`/`ast.literal_eval` on provider/zoom strings. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.13.5 | — |
| `requests` | ICAO resolver | ✓ | 2.33.1 `[VERIFIED: requirements.txt:4]` | — |
| `mcp_aviation_server` (running, HTTP) | BUILD-01 / RPT-02 at *runtime* | ✗ (not confirmed running) | server code `1.1.0`, `fastmcp 3.1.0` | **None by design** — D-04 says fail loud, no offline fallback. Tests mock it; the live server is a runtime, not build-time, dependency. |
| `pytest` | Nyquist validation | ✗ | — | `__main__` `assert` self-checks (repo idiom) |
| `docker` / `docker-compose` | to *run* the aviation server locally | unknown | — | Server can also run via `uv run mcp-aviation-server` with `MCP_TRANSPORT=http` `[CITED: mcp_aviation_server/README.md:60-63]` |

**Missing dependencies with no fallback (runtime, not build-time):**
- A reachable aviation server for live ICAO resolution / coverage. This does **not** block
  implementing or unit-testing Phase 2 (all tests mock HTTP); it only affects live use. UAT of
  RPT-02/BUILD-01 needs the server up (`docker-compose --profile http up -d`).

**Missing dependencies with fallback:**
- `pytest` → `__main__` self-checks if the team declines a dev dependency.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `notifications/initialized` is required before `tools/call` on this server | Wire Protocol | Low — sending it is harmless if optional; skeleton also degrades gracefully if no session id is returned. |
| A2 | `tools/call` response comes back as `text/event-stream` (SSE), inner text at `result.content[0].text` | Wire Protocol | Medium — the skeleton handles both SSE and `application/json`; if FastMCP 3.x changes envelope shape, adjust the `content[0].text` access. Verify with one live curl during Wave 0. |
| A3 | `protocolVersion "2025-06-18"` is accepted (server latest `2025-11-25`, default-negotiated `2025-03-26`) | Wire Protocol | Low — server negotiates down; any value ≤ latest is safe. |
| A4 | Sending the URL default `http://127.0.0.1:8000/mcp` matches the operator's deployment | Config | Low — it is the documented default; operator overrides via `Ortho4XP.cfg`. |
| A5 | Coverage over a real airport's 8 neighbors never crosses the antimeridian/poles in practice | Coverage | Low for v1; clamp or skip out-of-range tiles (Open Question). |

**These `[ASSUMED]` items should be confirmed by one live `curl`/smoke call against a running
container early in execution (a Wave-0 spike), since they concern the exact envelope shape.**

## Open Questions

1. **Exact FastMCP 3.1 `tools/call` envelope for a `str`-returning tool.**
   - What we know: the tool returns `model_dump_json()` (a JSON string); MCP wraps tool
     output in `result.content[].text`; FastMCP may also populate `result.structuredContent`.
   - What's unclear: whether `structuredContent` wraps the string under a `"result"` key and
     whether that path is more stable than `content[0].text`.
   - Recommendation: parse `content[0].text` (universal across MCP versions); verify with one
     live `curl` in a Wave-0 smoke test and pin the access path.

2. **Coverage tiles outside `[-90,89] × [-180,179]`.**
   - What we know: `parse_and_floor_coord` range-checks and raises `[VERIFIED: src/O4_CLI_Utils.py:30-31]`.
   - What's unclear: desired behavior for an airport whose neighbor tile falls off-grid.
   - Recommendation: skip (don't report) out-of-range neighbor tiles rather than raising;
     note in output. Small edge case; confirm wording with user if it matters.

3. **GUI persistence of the new URL var (Option a vs b in Config Declaration).**
   - Recommendation: Option (b) — declare in `cfg_app_vars` only, read plain-text with a
     default — unless the user wants it editable in the GUI Application Config tab.

## Sources

### Primary (HIGH confidence — read this session)
- `mcp_aviation_server/src/mcp_aviation/server.py` — tools (no resources), `get_airport_details`,
  error codes `AIRPORT_DETAILS_ERROR` / `SIM_DB_UNAVAILABLE`, `/health` route
- `mcp_aviation_server/src/mcp_aviation/models.py` — `AirportDetailsResponse`, `Coordinates`,
  `ErrorResponse` shapes
- `mcp_aviation_server/src/mcp_aviation/config.py` — `MCPConfig` defaults + env aliases
- `mcp_aviation_server/docker/docker-compose.yml` — prod HTTP profile env
- `mcp_aviation_server/pyproject.toml` + `.venv` dist-info — `fastmcp 3.1.0`, `mcp 1.26.0`
- `mcp_aviation_server/.venv/.../mcp/types.py` — protocol-version constants
- `src/O4_File_Names.py`, `src/O4_CLI_Utils.py`, `src/O4_Cfg_Vars.py`, `src/O4_Config_Utils.py`,
  `src/O4_Tile_Utils.py` — path authority, parser, config declaration/format, tile layout
- `Ortho4XP.cfg` — global config plain-text format
- `.planning/config.json` — workflow toggles (nyquist, security, api_coverage_gate)

### Secondary (MEDIUM confidence)
- `mcp_aviation_server/README.md`, `mcp_aviation_server/CLAUDE.md` — transport intent (SSE
  Inspector text is stale vs streamable-HTTP)
- `.planning/codebase/INTEGRATIONS.md` — repo-wide `requests` usage + timeout defaults

### Tertiary (LOW confidence — cross-check in Wave 0)
- MCP streamable-HTTP transport spec (handshake headers, SSE framing) — training knowledge,
  cross-checked against installed `mcp 1.26.0`; confirm exact envelope with a live curl.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + already-pinned `requests`; verified in `requirements.txt`.
- Wire protocol (tools, endpoint, payload, error codes): HIGH — read server source + installed
  package versions this session.
- Wire protocol (exact SSE envelope path for a str-returning tool): MEDIUM — spec-level; one
  live smoke call recommended (Assumptions A1–A3).
- Tile layout / D-05 predicate / leftovers: HIGH — verified against FNAMES + `O4_Tile_Utils`
  with line refs and verbatim quotes.
- Config filename correction / GUI coupling: HIGH — verified in `O4_Config_Utils` / `O4_Cfg_Vars`.

**Research date:** 2026-08-24
**Valid until:** ~2026-09-23 for the codebase facts (stable repo); re-verify the aviation
server envelope if `mcp_aviation_server` bumps `fastmcp`/`mcp` (fast-moving — ~7 days).
