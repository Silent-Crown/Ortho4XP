# Phase 2: Report & ICAO Resolution - Pattern Map

**Mapped:** 2026-08-24
**Files analyzed:** 6 (2 modify, 2 create, 1 embedded parser, 1 test infra)
**Analogs found:** 5 / 6 (test infra has only a weak convention analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/O4_CLI_Utils.py` (MODIFY) | route / controller | request-response | `src/O4_CLI_Utils.py` (Phase 1 dispatch, same file) | exact (self) |
| `src/O4_ICAO_Utils.py` (CREATE) | service | request-response (HTTP JSON-RPC) | `src/O4_OSM_Utils.py::get_overpass_data` | role + data-flow match |
| `src/O4_Report_Utils.py` (CREATE) | service / utility | file-I/O (read-only fs scan) | `src/O4_Tile_Utils.py` (FNAMES consumer) + `src/O4_Config_Utils.py::read_from_config` (plain-text parse) | role match (two analogs) |
| `src/O4_Cfg_Vars.py` (MODIFY) | config | declaration | `src/O4_Cfg_Vars.py::cfg_app_vars` entries `http_timeout` / `custom_scenery_dir` (same file) | exact (self) |
| Per-tile `.cfg` plain-text read (inside `O4_Report_Utils`) | utility | file-I/O | `src/O4_Config_Utils.py::read_from_config` loop (lines 207-241) — copy the parse loop, DROP the `exec()` | role match, deliberate divergence |
| Test infra (`tests/` or `__main__` self-check) | test | — | `src/O4_CLI_Utils.py` `__main__` assert block (158-178) | convention-only (no test suite exists) |

---

## Pattern Assignments

### `src/O4_CLI_Utils.py` (route/controller, request-response) — MODIFY

**Analog:** itself. Phase 1 already established the whole dispatch shape; Phase 2 extends the same three functions (`build_parser`, `dispatch`, `__main__`). Do **not** invent a new dispatch layer.

**Nested subparser idiom** — `build_parser()` already owns the subparser tree (lines 44-60). Add a `report` parser with its own second-level subparsers right after the `build` block, mirroring D-08 / RESEARCH Pattern 6:

```python
# existing, lines 50-58 — the tree to extend
subparsers = parser.add_subparsers(dest="command", required=True)
build_p = subparsers.add_parser("build", help="Build a single 1x1 degree tile")
build_p.add_argument("lat", help="SW corner latitude (integer or decimal)")
build_p.add_argument("lon", help="SW corner longitude (integer or decimal)")
build_p.add_argument("--provider", default=None, help="Imagery provider code")
build_p.add_argument("--zl", type=int, default=None, help="Zoom level")
```

New block to add (nested `dest="report_cmd", required=True`; `--icao` only on `coverage`):
```python
report_p = subparsers.add_parser("report", help="Read-only terrain reports")
report_sub = report_p.add_subparsers(dest="report_cmd", required=True)
report_sub.add_parser("tiles", help="List built tiles")
cov = report_sub.add_parser("coverage", help="Is an ICAO's tile(s) built?")
cov.add_argument("--icao", required=True, help="Airport ICAO code")
report_sub.add_parser("health", help="Flag partial builds / crashed-run leftovers")
```

**Dispatch branch pattern** (existing, lines 152-154) — copy this `run_and_report`-wrapped shape verbatim for each report command:
```python
args = build_parser().parse_args(argv)
if args.command == "build":
    run_and_report(run_build, args.lat, args.lon, args.provider, args.zl)
# add:
elif args.command == "report":
    if args.report_cmd == "tiles":
        run_and_report(RPT.report_tiles)
    elif args.report_cmd == "coverage":
        run_and_report(RPT.report_coverage, args.icao)
    elif args.report_cmd == "health":
        run_and_report(RPT.report_health)
```

**Error/exit wrapper — REUSE VERBATIM, do not re-implement** (lines 93-105). This is the BUILD-01 "clear error, non-zero exit" mechanism. Report/resolve functions just raise; `run_and_report` prints the traceback and `sys.exit(1)`:
```python
def run_and_report(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
```
> Note for BUILD-01 wording (D-04): the *specific* message ("server unreachable" vs "ICAO not found") comes from the exception's own message string raised in `O4_ICAO_Utils`; `run_and_report` surfaces it via the traceback. If cleaner single-line stderr (no traceback) is wanted for the two known resolver failures, catch `AviationServerUnreachable`/`ICAONotFound` inside the coverage command and `print(..., file=sys.stderr); sys.exit(1)` before falling through to `run_and_report` — planner's call.

**Coordinate floor — REUSE** `parse_lat` / `parse_lon` (lines 35-40, wrapping `parse_and_floor_coord` 9-32) to floor a resolved ICAO lat/lon to its containing tile. `math.floor` is correct for negatives; `int()` is the CLI-04 bug — do not re-derive.

**Lazy-import rule for report helpers:** import `O4_Report_Utils` / `O4_ICAO_Utils` at module top of `O4_CLI_Utils` is safe (they pull only FNAMES/requests/stdlib). Do **not** import them the way `run_build` lazily imports the build modules — that lazy pattern (lines 72-76) exists solely because `O4_Config_Utils` mutates globals; the report helpers have no such side effect.

---

### `src/O4_ICAO_Utils.py` (service, request-response HTTP JSON-RPC) — CREATE

**Analog:** `src/O4_OSM_Utils.py::get_overpass_data` (lines 513-560) — the repo's canonical "plain `requests.Session` to an external service with explicit timeout" pattern. Match its grain; do not add an MCP SDK (D-02).

**Session + timeout pattern to mirror** (O4_OSM_Utils.py:518-520, 558-559):
```python
s = requests.Session()
s.headers.update({"User-Agent": f"Ortho4XP/{O4XP_VERSION} (...)"})
...
r = s.get(url, timeout=60)          # <-- every request carries an explicit timeout
```
Apply the same shape: one `requests.Session()`, `POST` with explicit `timeout=` on every call (default from `http_timeout`, see below), headers set once. The full JSON-RPC handshake skeleton (initialize → notifications/initialized → tools/call, SSE parse, 3-way error classification) is already written in RESEARCH §"Code Examples" lines 561-620 — copy it as the module body. Key deviations the planner must honor:
- Method is `tools/call` → `get_airport_details`, NOT `resources/read airport://{ident}` (RESEARCH correction, server is tools-only).
- Coordinates at `payload["airport"]["coordinates"]["latitude"|"longitude"]`.
- Do NOT trust `isError`; branch on inner `code` (`AIRPORT_DETAILS_ERROR` → not-found, `SIM_DB_UNAVAILABLE`/other → unavailable).
- Two exception classes (`AviationServerUnreachable`, `ICAONotFound`) carry the D-04 distinct messages.

**Timeout source:** reuse the existing `http_timeout` app var (default `10.0`, `O4_Cfg_Vars.py:69-74`) rather than a new one — it already means "delay before an HTTP request is timed out."

**Input validation (ASVS V5, RESEARCH Security):** `ident = ident.strip().upper()` and reject length > 10 before sending; validate resolved lat/lon are finite and in `[-90,90]/[-180,180]` before returning.

---

### `src/O4_Report_Utils.py` (service/utility, read-only filesystem scan) — CREATE

**Analog A — FNAMES path construction:** `src/O4_Tile_Utils.py` (lines 160-183, 244-250) is the reference FNAMES consumer. It shows the exact tile layout the predicate inspects:
```python
# textures dir — literally build_dir/"textures"  (O4_Tile_Utils.py:167-168)
if not os.path.isdir(os.path.join(tile.build_dir, "textures")):
    os.makedirs(os.path.join(tile.build_dir, "textures"))
# DSF is activated by rename from .tmp  (O4_Tile_Utils.py:244-250)
dsf_file_name = os.path.join(
    tile.build_dir, "Earth nav data",
    FNAMES.long_latlon(tile.lat, tile.lon) + ".dsf")
os.replace(dsf_file_name + ".tmp", dsf_file_name)   # <- a leftover .dsf.tmp == crash signal (D-07)
```
Use FNAMES helpers, never hardcode: `FNAMES.Tile_dir`, `FNAMES.build_dir(lat, lon, "")`, `FNAMES.dsf_file(build_dir, lat, lon)`, `FNAMES.short_latlon`, `FNAMES.Tmp_dir`. Verified path facts:
- `build_dir(lat, lon, "")` → `os.path.join(Tile_dir, tile_dir(lat, lon))` (O4_File_Names.py:71-77)
- `tile_dir` → `"zOrtho4XP_" + short_latlon(lat, lon)` (O4_File_Names.py:67-68)
- `dsf_file` → `os.path.join(build_dir, "Earth nav data", long_latlon(lat, lon) + ".dsf")` (O4_File_Names.py:205-208); note the nested `<round>/<latlon>.dsf` from `long_latlon` (O4_File_Names.py:47-52)
- `short_latlon` format `"{:+.0f}".zfill(3/4)` e.g. `+47-122` (O4_File_Names.py:35-38) — drives the dir-name regex `^zOrtho4XP_([+-]\d{2,})([+-]\d{3,})$`
- `Tile_dir = resource_path("Tiles")` (O4_File_Names.py:30), `Tmp_dir = resource_path("tmp")` (O4_File_Names.py:31)

The `is_tile_built()` predicate (D-05), `iter_tiles()` walk, inventory facts (D-9), coverage 3×3 (D-11), and leftover scan (D-07) are all spelled out as copy-ready skeletons in RESEARCH Patterns 1-5 (lines 313-430) — mirror those.

**Analog B — plain-text `.cfg` parse (D-09), the deliberate-divergence pattern:** `src/O4_Config_Utils.py::read_from_config` loop (lines 207-241) is the format authority. Copy its line handling, **DROP the `exec()`**:
```python
# O4_Config_Utils.py:209-229 — COPY the parse shape, NOT the exec
for line in f.readlines():
    line = line.strip()
    if not line: continue
    if line[0] == "#": continue
    (var, value) = line.split("=", 1)   # <- keep: strip / skip-blank / skip-# / split("=",1)
    ...
    exec(cmd)                            # <- DO NOT COPY: this is the RPT-01-forbidden side effect
```
Replace `exec` with `out[var.strip()] = value.strip()`. Same format works for the global `Ortho4XP.cfg` (verified `key=value` head).

**CRITICAL filename fact (RESEARCH correction of D-09):** the per-tile config is `Ortho4XP_<latlon>.cfg` — NO leading `z`. Confirmed by the writer `O4_Config_Utils.py:262-264`:
```python
config_file = os.path.join(
    self.build_dir, "Ortho4XP_" + FNAMES.short_latlon(self.lat, self.lon) + ".cfg")
```
The `z` is only on the *directory* (`zOrtho4XP_<latlon>/`). Read `default_website` (provider) and `default_zl` (zoom) from it — both are in `list_tile_vars` (O4_Cfg_Vars.py:441-448) and written verbatim.

**Inventory facts (D-09):** provider = `default_website`, zoom = `default_zl` (from the plain-text parse); build date = `os.path.getmtime(FNAMES.dsf_file(...))`; on-disk size = `os.walk(build_dir)` + `os.path.getsize`. Output = aligned text table (D-10) — plain `print`/`str.ljust`; `--json` deferred.

---

### `src/O4_Cfg_Vars.py` (config declaration) — MODIFY

**Analog:** existing `cfg_app_vars` string entries `custom_scenery_dir` (lines 99-103) and `http_timeout` (69-74) — same file. Add the aviation-server URL as a plain `str` app var:
```python
"mcp_aviation_server_url": {
    "type": str,
    "default": "http://127.0.0.1:8000/mcp",
    "hint": "Base URL of the mcp_aviation_server streamable-HTTP endpoint used to resolve ICAO codes to coordinates.",
},
```
Verified default endpoint `http://127.0.0.1:8000/mcp` (RESEARCH §Endpoint). No `"module"` key needed (it stays a local module global, like `custom_scenery_dir`).

**GUI-coupling gotcha — planner must decide (RESEARCH lines 456-482):** `gui_app_vars_long = list_app_vars[-3:]` (O4_Cfg_Vars.py:384) picks the *last three* `list_app_vars` entries for folder-picker GUI rows. Two options:
- **(b) RECOMMENDED — smaller diff:** add to `cfg_app_vars` **only**, NOT to `list_app_vars`. The var is declared, has a default, and is read via the plain-text parser (`FNAMES.resource_path("Ortho4XP.cfg")`) with default-on-absence. Not shown/persisted in GUI — fine for a CLI-only setting.
- (a) add to both, but insert **before** the last three of `list_app_vars` to avoid shifting which vars get folder pickers.

**Reading the URL without CFG side effects (D-03):** importing `O4_Cfg_Vars` for the default is safe (it only builds dicts + imports `O4_OSM_Utils`); importing `O4_Config_Utils` is NOT (see Shared Patterns). Read the operator override from `Ortho4XP.cfg` with the same plain-text parser as the per-tile config, falling back to the declared default when the key is absent (existing configs predate the var).

---

### Test infrastructure — CREATE (weak analog)

**No test suite, no pytest, no `pyproject.toml` exist** (verified: `tests/` absent, `pyproject.toml` absent). The only in-repo test idiom is the `__main__` assert self-check block:

**Analog — `src/O4_CLI_Utils.py` lines 158-178:**
```python
if __name__ == "__main__":
    assert parse_lat("-0.5") == -1
    assert parse_lon("47.5") == 47
    ...
    try:
        parse_lat("999")
    except ValueError:
        pass
    else:
        raise AssertionError("parse_lat('999') should raise ValueError")
    print("O4_CLI_Utils self-check OK")
```
Two valid targets (planner picks; global rules prefer pytest+uv, repo convention is the self-check):
- **pytest** (`uv add --dev pytest`, `tests/` dir, mock `requests.Session.post` with canned SSE bodies + `tmp_path` fixture tile dirs) — the full test map is in RESEARCH §Validation lines 676-704.
- **fallback:** extend each new module with a `__main__` assert self-check mirroring the block above (zero deps, matches repo, runnable via `python src/O4_Report_Utils.py`).

---

## Shared Patterns

### CFG-imported-last / no-side-effect-import rule
**Source:** `Ortho4XP.py:20-28` (import order) + `O4_Config_Utils.py:96-102` (the `exec()` mutation at import time).
**Apply to:** every new module. `O4_Config_Utils` runs, at import, `exec(target + "=cfg_vars[...]['default']")` over other modules' globals — importing it from a read-only report path violates RPT-01 and drags in Tkinter/IMG/DEM.
```python
# Ortho4XP.py:26-28
import O4_Tile_Utils as TILE
import O4_GUI_Utils as GUI
import O4_Config_Utils as CFG  # CFG imported last because it can modify other modules variables
```
```python
# O4_Config_Utils.py:96-102 — the side effect to avoid triggering
for var in cfg_vars:
    target = cfg_vars[var]["module"] + "." + var if "module" in cfg_vars[var] else var
    exec(target + "=cfg_vars['" + var + "']['default']")
```
**Rule:** new report/resolver modules import only `os`/`re`/`json`/`requests`/`math` (stdlib+dep), `O4_File_Names` (FNAMES), optionally `O4_UI_Utils` (UI) and `O4_Cfg_Vars`. Never `O4_Config_Utils`.

### Module aliasing convention
**Source:** `Ortho4XP.py:20-28`, `.claude/CLAUDE.md`.
**Apply to:** all new modules. Name `O4_<Domain>_Utils.py`; import by two-letter-ish uppercase alias — suggested `import O4_Report_Utils as RPT`, `import O4_ICAO_Utils as ICAO`, consistent with `IMG`/`VMAP`/`MESH`/`MASK`/`TILE`/`CFG`/`OSM`/`FNAMES`/`UI`.

### External-service HTTP call
**Source:** `O4_OSM_Utils.py:518-559`, `O4_DEM_Utils.py:805`, `O4_Imagery_Utils.py:1084/1342/1463` — every external caller uses a plain `requests.Session` with an explicit `timeout=`.
**Apply to:** `O4_ICAO_Utils`. Session + explicit timeout on every POST; no async, no new dep (D-02). Timeout default from `http_timeout` (10.0).

### FNAMES as the sole path authority
**Source:** `O4_File_Names.py` (whole module), consumed by `O4_Tile_Utils.py`.
**Apply to:** `O4_Report_Utils`. Never hardcode `Tiles/…/Earth nav data/…`; the nested `<round>/<latlon>.dsf` layout comes from `long_latlon` and is non-obvious. Use `Tile_dir`, `build_dir`, `dsf_file`, `short_latlon`, `long_latlon`, `Tmp_dir`.

### Error → clear message → non-zero exit
**Source:** `O4_CLI_Utils.py::run_and_report` (93-105).
**Apply to:** all new commands. Raise typed exceptions with specific messages; wrap the command in `run_and_report`. `SystemExit` passes through so argparse usage errors keep exit code 2.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Test infra (`tests/` + pytest) | test | — | No test suite, framework, or `pyproject.toml` exists in the repo. Only convention: `__main__` assert self-check (`O4_CLI_Utils.py:158-178`). Planner chooses pytest (per global rules) or the self-check idiom (per repo). |
| MCP-over-HTTP JSON-RPC handshake | service | request-response | The `requests.Session` grain matches `O4_OSM_Utils`, but the MCP streamable-HTTP handshake (initialize/initialized/tools-call, SSE framing, `Mcp-Session-Id`) has **no in-repo precedent** — it is the one genuinely new ~40-line block. Copy the skeleton from RESEARCH §Code Examples (561-620), verify the exact SSE envelope with one live curl in Wave 0 (Assumptions A1-A3). |

---

## Metadata

**Analog search scope:** `src/*.py` (all 24 `O4_*` modules), `Ortho4XP.py`, `Ortho4XP.cfg`, repo root (`tests/`, `pyproject.toml`).
**Files scanned in depth:** `O4_CLI_Utils.py` (full), `O4_File_Names.py` (full), `O4_Cfg_Vars.py` (1-120, 355-455), `O4_OSM_Utils.py` (505-565), `O4_Tile_Utils.py` (158-198, 242-255), `O4_Config_Utils.py` (90-104, 200-294), `Ortho4XP.py` (import block + dispatch).
**Pattern extraction date:** 2026-08-24
