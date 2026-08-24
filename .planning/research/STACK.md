# Stack Research

**Domain:** CLI automation layer for an existing Python 3.13 desktop app (argparse subcommands + MCP client integration + offline geodata fallback)
**Researched:** 2026-08-24
**Confidence:** HIGH

Scope note: this covers only the three additions the milestone needs — CLI parsing,
ICAO lookup client, offline fallback dataset. The existing build pipeline stack
(numpy/shapely/pyproj/gdal/Pillow/Rtree) is out of scope; see
`.planning/codebase/STACK.md`.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `argparse` (stdlib) | Python 3.13 bundled | Subcommand CLI (`build`, `report`, legacy positional) | Zero new dependency, matches the project's own constraint ("no new CLI framework"). `add_subparsers(dest=..., required=False)` plus a small argv-sniffing shim is the standard way real tools (pip, aws-cli-style dispatchers) add subcommands onto a legacy positional interface without breaking it. |
| `fastmcp` (client only) | 3.4.7 (PyPI, checked 2026-08-24) | Talk to `mcp_aviation_server` over MCP | `mcp_aviation_server` is itself built on FastMCP 2.0 (confirmed in its `pyproject.toml`/README). Using the same `fastmcp.Client` on the CLI side reuses one mental model and one dependency instead of hand-rolling JSON-RPC against the lower-level `mcp` SDK. `Client("path/to/server.py")` infers a stdio subprocess transport automatically — no separate transport wiring needed for the common case where the server repo is checked out locally. |
| `asyncio` (stdlib) | Python 3.13 bundled | Bridge the sync CLI to the async MCP client | `fastmcp.Client` and the underlying `mcp` SDK are async-only (JSON-RPC over stdio/HTTP needs an event loop for concurrent read/write). The 2025/2026-standard bridge is a single `asyncio.run(main())` call per CLI invocation — a short-lived loop for one lookup, not a long-running async CLI. No `trio`, no `anyio` wrapper needed for this use case. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `csv` | bundled | Parse the offline ICAO→lat/lon fallback file | Only if `mcp_aviation_server` is unreachable (subprocess launch fails, or configured URL times out). A dict keyed by `ident` built once at CLI startup from a bundled trimmed CSV — no pandas, no sqlite import needed for a ~3-column lookup table. |
| `requests` (already a dependency) | 2.33.1 (already pinned) | One-time refresh script to regenerate the bundled fallback CSV from OurAirports | Not shipped as a runtime dependency for the fallback itself — only used in a maintenance script (`scripts/refresh_icao_fallback.py` or similar) run occasionally by a maintainer, not by end users. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `python -m fastmcp dev` / MCP Inspector | Interactively test `mcp_aviation_server` tool calls (`get_airport_details`) while building the CLI client code | Confirmed present in `mcp_aviation_server`'s own README ("MCP Inspector Compatible"); use it to see the exact JSON shape returned before writing the parser for lat/lon extraction. |

## Installation

```bash
# Core — new runtime dependency for MCP integration
uv add fastmcp

# Nothing else new: argparse, asyncio, csv are stdlib;
# requests is already in requirements.txt for the fallback-refresh script only.
```

## Integration Findings (from reading `mcp_aviation_server` source directly)

Read `C:/Users/WillMcBurnett/dev/mcp_aviation_server/src/mcp_aviation/server.py` and
`config.py` directly rather than guessing — confidence HIGH, this is primary-source not
secondhand docs:

- **Transport defaults to `stdio`** (`config.py` line 121: `transport: str = "stdio"`),
  overridable to `http` via `MCP_TRANSPORT=http`. For a CLI that shells out per-invocation,
  stdio is the right default — no daemon to keep running, no port to manage.
- **Lookup is a `tool`, not a plain resource** despite the README's "resource-based"
  framing: `get_airport_details(ident: str) -> str` (server.py line 404) returns a JSON
  string with airport + runway + comms + approach data. The CLI needs one field
  (lat/lon) out of that payload — trivial `json.loads()` + key access, no schema library
  needed.
- **Default DB is a local SQLite file** (`sqlite:///data/aviation.sqlite`), swappable to
  Postgres/MySQL via `DATABASE_URL`. This is exactly why the milestone's own decision
  (go through the MCP server, not a direct DB connection) is correct — a direct
  `sqlite3` connection would silently break the day someone points the server at
  Postgres in production. Route through the MCP tool call, not the DB file.
- **Identifier validation already exists server-side**
  (`validate_airport_identifier`, max 10 chars, uppercased) — the CLI does not need to
  duplicate ICAO-format validation before calling the tool; let the server 400/error on
  garbage input and surface that message.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `fastmcp.Client` (stdio, subprocess-per-call) | Raw `mcp` SDK (`mcp.client.stdio.stdio_client` + `ClientSession`) | Only if you want zero dependency on the `fastmcp` package specifically and are fine with more boilerplate (manual `ClientSession.initialize()`, manual JSON-RPC envelope handling). Not worth it here — `fastmcp` is already the framework the target server is built on, so it's not really "extra" ecosystem surface. |
| `fastmcp.Client("path/to/server.py")` inferred stdio transport | `fastmcp.Client("http://host:port")` against an already-running HTTP server | Use HTTP transport if `mcp_aviation_server` is deployed as a long-lived Docker service reachable by URL (its README documents Docker + `http` transport support) rather than checked out as a sibling repo. Make the transport/URL configurable in `Ortho4XP.cfg`, default to stdio-subprocess-of-local-checkout for the common single-machine case. |
| Bundled trimmed OurAirports CSV (ident, lat, lon only) | Full `airports.csv` from OurAirports (12.7 MB, ~90 columns) | Never ship the full file — Ortho4XP only needs 3 columns for ~80k airports. Pre-filter to a ~1–2 MB CSV (or even a `.py`/`.json` dict) at build/maintenance time, not at runtime. |
| Bundled CSV fallback | A second live API (e.g. hitting OurAirports' site directly at runtime) | Rejected — defeats the point of "offline fallback." The fallback must work with no network at all, matching the existing app's `requests`-heavy build pipeline where network already can fail mid-build; the ICAO lookup path shouldn't be the first thing that requires connectivity. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `click` / `typer` / `Fire` for the CLI | Project explicitly constrains to stdlib `argparse`; adding a CLI framework for subcommands is unnecessary weight when argparse's `add_subparsers` already does this natively in stdlib, and it avoids a second parsing paradigm to reconcile with the existing `sys.argv[1:]` positional code. | `argparse.ArgumentParser` + `add_subparsers()` |
| Defining the legacy `lat lon [provider zl]` positional args directly on the *top-level* parser alongside subparsers | argparse resolves subcommands by consuming the first positional token as the subcommand name; a top-level optional positional (`nargs='?'`) collides with subcommand dispatch and produces confusing "invalid choice" errors when a user passes a float for latitude. This is a documented argparse rough edge, not a project-specific bug. | Pre-parse `sys.argv[1:]`: if `argv[0]` matches a known subcommand string, dispatch normally; otherwise (no args → GUI, or first token parses as a coordinate) route to a dedicated `legacy` handling path that reuses the *same* underlying build function the `build` subcommand calls. Keep the legacy path and the new `build` subcommand as two thin CLI entry points over one shared function — not two independent implementations. |
| Raw `mcp` SDK `ClientSession`/`stdio_client` for this integration | Lower-level, more boilerplate (manual initialize/handshake) for no benefit when the target server is already FastMCP-based and `fastmcp.Client` exists specifically to be the ergonomic client for FastMCP (and any MCP) servers. | `fastmcp.Client` |
| Persistent/long-running event loop or an async CLI framework (e.g. `asyncclick`) | The CLI only needs one or a handful of MCP round-trips per invocation (single ICAO or a batch list), not sustained concurrency; a persistent loop or async-first CLI framework adds architecture the workload doesn't need. | `asyncio.run(lookup_icaos(icao_list))` once per CLI invocation — batch the tool calls inside that one run, still synchronous from the caller's perspective. |
| Direct `sqlite3` connection to `mcp_aviation_server`'s `aviation.sqlite` file | Couples Ortho4XP to an implementation detail (SQLite specifically, and a specific file path) that the server itself treats as swappable (Postgres/MySQL supported). Breaks silently in any deployment where the aviation DB isn't local SQLite. Also directly contradicts the milestone's own stated decision to go through the shared server. | `fastmcp.Client(...).call_tool("get_airport_details", {"ident": icao})` |
| Full, unfiltered OurAirports `airports.csv` as the bundled fallback | 12.7 MB / ~90 columns for a 3-field lookup is dead weight shipped in every Ortho4XP checkout/executable, and PyInstaller bundling (already used for distribution per `Ortho4XP.spec`) would carry that weight into every build. | Pre-trim to `ident,latitude_deg,longitude_deg` at maintenance time; ships as a few hundred KB. |
| `pandas` to read the fallback CSV | Massive dependency (and a new one — not currently in `requirements.txt`) for parsing a 3-column CSV into a dict. | stdlib `csv.DictReader` → `dict[str, tuple[float, float]]`, built once, cached in memory for the process lifetime. |

## Stack Patterns by Variant

**If `mcp_aviation_server` is checked out as a sibling repo on the same machine (the common Silent-Crown dev setup):**
- Use `fastmcp.Client("<path>/mcp_aviation_server/src/mcp_aviation/server.py")` — stdio transport, auto-inferred, no server process to keep alive.
- Because this matches how the server's own default config runs (`transport: stdio`) and needs zero extra infrastructure.

**If `mcp_aviation_server` is deployed as a standing Docker/HTTP service (its README documents this):**
- Use `fastmcp.Client("http://<host>:<port>")`, URL sourced from an `Ortho4XP.cfg` setting (mirroring how `overpass_server_choice` and imagery provider URLs are already configurable).
- Because the milestone's own constraint calls for graceful degradation and configurability, not a hardcoded local path.

**If the MCP call fails (server unreachable, subprocess launch error, timeout):**
- Catch the specific `fastmcp`/connection exception, print a clear one-line error (not the existing bare "Crash!" pattern the milestone explicitly calls out for replacement), and fall back to the bundled OurAirports CSV lookup if present.
- Because PROJECT.md's own constraint requires "clear error, optional local fallback" rather than a hard dependency on network/subprocess availability.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `fastmcp` 3.4.7 | Python 3.13.5 (project's pinned runtime) | `fastmcp` targets modern Python (3.10+ per `mcp_aviation_server`'s own README); no conflict with 3.13. |
| `fastmcp` 3.4.7 (client) | `mcp_aviation_server`'s "FastMCP 2.0" (server) | FastMCP's client/server major versions are not required to match — the wire protocol is MCP itself, not the FastMCP package version. Verify against the server's actual installed version in its `uv.lock` if a specific tool schema mismatch ever appears, but no known breaking incompatibility for basic `call_tool`. |
| stdlib `argparse` | Python 3.13 | No version concerns — behavior used here (`add_subparsers`, `nargs='?'`) has been stable across 3.x for years. |

## Sources

- `C:/Users/WillMcBurnett/dev/mcp_aviation_server/src/mcp_aviation/server.py` (primary source, read directly) — confirmed tool name `get_airport_details`, transport default, validation behavior. Confidence: HIGH (primary source).
- `C:/Users/WillMcBurnett/dev/mcp_aviation_server/src/mcp_aviation/config.py` (primary source, read directly) — confirmed `transport: str = "stdio"` default and SQLite/Postgres/MySQL swappability. Confidence: HIGH.
- `C:/Users/WillMcBurnett/dev/mcp_aviation_server/README.md` — confirmed "FastMCP 2.0 Powered", Docker deployment, MCP Inspector support. Confidence: HIGH (primary source).
- https://pypi.org/pypi/fastmcp/json — current version 3.4.7, checked 2026-08-24. Confidence: HIGH (official registry).
- https://pypi.org/pypi/mcp/json — official MCP Python SDK at 2.0.0, checked 2026-08-24 (context only; not the recommended integration path here). Confidence: HIGH.
- https://gofastmcp.com/clients/client — confirmed `Client("server.py")` inferred stdio transport, `async with client: await client.call_tool(...)`, `asyncio.run(main())` bridging pattern. Confidence: HIGH (official docs).
- https://docs.python.org/3/howto/argparse-optparse.html and general argparse subcommand/positional-conflict discussion — confirmed the standard fix is keeping the top-level parser free of a competing positional and dispatching before/around `parse_args`. Confidence: MEDIUM (community pattern, not a single canonical stdlib doc page, but consistent across sources).
- https://github.com/davidmegginson/ourairports-data (mirror of https://ourairports.com/data/airports.csv, redirects there) — confirmed as the current canonical OurAirports download location and its `ident`/`latitude_deg`/`longitude_deg` columns. Confidence: HIGH.

---
*Stack research for: Ortho4XP CLI automation (argparse + MCP client + offline ICAO fallback)*
*Researched: 2026-08-24*
