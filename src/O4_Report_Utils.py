"""Read-only tile coverage reporting (RPT-01/RPT-02).

Reads the existing Tiles/ tree via FNAMES paths only; never imports
O4_Config_Utils (which runs exec()-based global mutation and drags in Tkinter)
and never writes anything to disk.
"""

import os
import re

import O4_File_Names as FNAMES

# Strict tile-dir matcher (D-05/T-02-04): zOrtho4XP_<slat><slon>, ints only.
_TILE_RE = re.compile(r"^zOrtho4XP_([+-]\d{2,})([+-]\d{3,})$")


def read_cfg(path):
    """Parse a plain-text ``key=value`` Ortho4XP config into a dict.

    Mirrors the O4_Config_Utils reader shape (strip, skip blank, skip ``#``,
    ``split("=", 1)``) with the exec/eval branch DROPPED — values stay strings.
    """
    result = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] == "#" or "=" not in line:
                continue
            var, value = line.split("=", 1)
            result[var.strip()] = value.strip()
    return result


def _store_root(store):
    """Normalize a tile-store root: empty stays empty (default ./Tiles); a
    non-empty root gets a trailing separator so FNAMES.build_dir nests each
    tile under it instead of treating it as one literal per-tile dir."""
    if store and not store.endswith(("/", "\\")):
        return store + "/"
    return store


def tile_status(lat, lon, store=""):
    """The D-05 predicate: ``missing`` / ``built`` / ``partial`` for one tile.

    ``built`` requires a non-empty DSF AND a non-empty ``textures/`` dir; a build
    dir that exists but fails either check is ``partial`` (never ``built``).
    ``store`` selects the tile store (empty = default ./Tiles).
    """
    build_dir = FNAMES.build_dir(lat, lon, _store_root(store))
    if not os.path.isdir(build_dir):
        return "missing"
    dsf = FNAMES.dsf_file(build_dir, lat, lon)
    tex = os.path.join(build_dir, "textures")
    dsf_ok = os.path.isfile(dsf) and os.path.getsize(dsf) > 0
    tex_ok = os.path.isdir(tex) and bool(os.listdir(tex))
    if dsf_ok and tex_ok:
        return "built"
    return "partial"


def iter_tiles(store=""):
    """Yield ``(lat, lon, path)`` for every ``zOrtho4XP_<latlon>`` dir in the store.

    lat/lon are ints recovered from the strict regex; non-matching directory
    names are ignored. ``store`` selects the tile store (empty = default
    ./Tiles). Yields nothing when the store dir is absent.
    """
    root = _store_root(store).rstrip("/\\") if store else FNAMES.Tile_dir
    if not os.path.isdir(root):
        return
    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        m = _TILE_RE.match(entry.name)
        if m:
            yield int(m.group(1)), int(m.group(2)), entry.path


def read_tile_cfg(build_dir, lat, lon):
    """Read provider/zoom from ``Ortho4XP_<latlon>.cfg`` (NO leading z; D-09).

    Returns ``(default_website, default_zl)`` as strings; a missing file yields
    ``("", "")`` rather than raising.
    """
    path = os.path.join(build_dir, "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg")
    if not os.path.isfile(path):
        return "", ""
    d = read_cfg(path)
    return d.get("default_website", ""), d.get("default_zl", "")


def _dir_size(path):
    """Sum of file sizes under path (os.walk + getsize), read-only."""
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _human_size(n):
    """Compact human size (B/K/M/G) — display only."""
    size = float(n)
    for unit in ("B", "K", "M", "G"):
        if size < 1024 or unit == "G":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024


def report_tiles(store=""):
    """Print an aligned inventory of built tiles: latlon, provider, zoom, date, size.

    Rows are (lat, lon)-sorted (deterministic). An absent/empty store prints a
    single clean "no tiles built" line. Read-only (D-06).
    """
    import time

    tiles = sorted(iter_tiles(store), key=lambda t: (t[0], t[1]))
    if not tiles:
        print("no tiles built")
        return
    header = f"{'tile':<9} {'provider':<10} {'zoom':<5} {'built':<19} {'size':>9}"
    print(header)
    for lat, lon, path in tiles:
        provider, zoom = read_tile_cfg(path, lat, lon)
        dsf = FNAMES.dsf_file(path, lat, lon)
        if os.path.isfile(dsf):
            built = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(dsf)))
        else:
            built = "-"
        size = _human_size(_dir_size(path))
        print(f"{FNAMES.short_latlon(lat, lon):<9} {provider or '-':<10} "
              f"{zoom or '-':<5} {built:<19} {size:>9}")


# Data* intermediate extensions a crashed run leaves behind (D-07).
_DATA_EXTS = (".poly", ".node", ".ele", ".mesh", ".alt", ".apt", ".weight")


def tile_leftovers(build_dir, lat, lon):
    """Named orphan classes present in a partial tile (read-only, D-07).

    Returns a list of short labels: ``.dsf.tmp`` (a temp DSF beside a missing
    final one), ``Data*`` (triangulation intermediates with no resulting DSF),
    ``empty-textures/`` (an existing but empty textures dir).
    """
    classes = []
    dsf = FNAMES.dsf_file(build_dir, lat, lon)
    dsf_final = os.path.isfile(dsf) and os.path.getsize(dsf) > 0
    if not dsf_final and os.path.isfile(dsf + ".tmp"):
        classes.append(".dsf.tmp")
    if not dsf_final:
        short = FNAMES.short_latlon(lat, lon)
        if any(os.path.isfile(os.path.join(build_dir, "Data" + short + ext))
               for ext in _DATA_EXTS):
            classes.append("Data*")
    tex = os.path.join(build_dir, "textures")
    if os.path.isdir(tex) and not os.listdir(tex):
        classes.append("empty-textures/")
    return classes


def report_health(store=""):
    """Flag partial tiles + their orphan classes and a global tmp/ leftover.

    Reuses the D-05 ``tile_status`` predicate; no time-based staleness (D-06).
    Read-only — deletes/moves nothing. Prints a clean "no issues" line when
    nothing is flagged. ``store`` selects the tile store (empty = default ./Tiles).
    """
    flagged = []
    for lat, lon, path in sorted(iter_tiles(store), key=lambda t: (t[0], t[1])):
        if tile_status(lat, lon, store) != "partial":
            continue
        classes = tile_leftovers(path, lat, lon) or ["partial"]
        flagged.append((lat, lon, classes))

    tmp_dirty = os.path.isdir(FNAMES.Tmp_dir) and bool(os.listdir(FNAMES.Tmp_dir))

    if not flagged and not tmp_dirty:
        print("no issues")
        return
    if flagged:
        print(f"{'tile':<9} {'status':<8} orphans")
        for lat, lon, classes in flagged:
            print(f"{FNAMES.short_latlon(lat, lon):<9} {'partial':<8} "
                  f"{', '.join(classes)}")
    if tmp_dirty:
        print(f"global: non-empty {FNAMES.Tmp_dir} (crashed-run leftover)")


def coverage_tiles(lat, lon):
    """Yield the containing tile + its 8 neighbors as floored ``(lat, lon)`` pairs.

    Floors the resolved coordinate with ``parse_lat``/``parse_lon`` (D-11 3x3
    block). A neighbor that floors outside the valid grid is skipped, not raised
    (planner_assumptions: antimeridian/pole wraparound is a v1.x decision).
    """
    import O4_CLI_Utils as CLI

    base_lat = CLI.parse_lat(lat)
    base_lon = CLI.parse_lon(lon)
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            try:
                nlat = CLI.parse_lat(base_lat + dlat)
                nlon = CLI.parse_lon(base_lon + dlon)
            except ValueError:
                continue  # off-grid neighbor (pole/antimeridian): skip, don't crash
            yield nlat, nlon


def report_coverage(icao, store=""):
    """Resolve an ICAO and print the built/partial/missing status of its 3x3 block.

    Reports the containing tile plus its 8 neighbors (D-11). The two resolver
    failures fail loud on a single stderr line with a non-zero exit (D-04) — no
    traceback, no coordinate, no tile rows. ``store`` selects the tile store
    (empty = default ./Tiles).
    """
    import sys

    import O4_ICAO_Utils as ICAO

    ident = icao.strip().upper()
    try:
        lat_f, lon_f = ICAO.resolve_icao(ident, ICAO.get_server_url())
    except (ICAO.AviationServerUnreachable, ICAO.ICAONotFound, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    for lat, lon in coverage_tiles(lat_f, lon_f):
        print(f"{ident:<8} {FNAMES.short_latlon(lat, lon):<9} "
              f"{tile_status(lat, lon, store)}")


if __name__ == "__main__":
    assert read_cfg.__doc__  # trivially importable
    print("O4_Report_Utils self-check OK")
