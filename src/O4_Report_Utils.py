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

# Texture name is FNAMES.dds_file_name_from_attributes: {y}_{x}_{provider}{zl}.dds.
# The zoom level is the trailing 2 digits before .dds; the greedy provider group
# backtracks so a provider code ending in a digit (e.g. GO2) still parses right.
_TEX_RE = re.compile(r"^\d+_\d+_(.+)(\d{2})\.dds$", re.IGNORECASE)


def zoom_breakdown(build_dir):
    """Per-zoom-level texture tally for a built tile (read-only).

    Scans ``build_dir/textures`` and buckets each ``.dds`` by the zoom level
    encoded in its filename. Non-texture files (e.g. water_transition.png) are
    ignored. Returns a ``(zl)``-sorted list of ``(zl, count, bytes)`` — empty
    when there is no textures dir or no parseable tiles.
    """
    tex = os.path.join(build_dir, "textures")
    if not os.path.isdir(tex):
        return []
    counts, sizes = {}, {}
    for name in os.listdir(tex):
        m = _TEX_RE.match(name)
        if not m:
            continue
        zl = int(m.group(2))
        counts[zl] = counts.get(zl, 0) + 1
        try:
            sizes[zl] = sizes.get(zl, 0) + os.path.getsize(os.path.join(tex, name))
        except OSError:
            pass
    return [(zl, counts[zl], sizes.get(zl, 0)) for zl in sorted(counts)]


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
    root = store.rstrip("/\\") if store else FNAMES.Tile_dir
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


def report_tiles(store="", show_zoom=False):
    """Print an aligned inventory of built tiles: latlon, provider, zoom, date, size.

    Rows are (lat, lon)-sorted (deterministic). An absent/empty store prints a
    single clean "no tiles built" line. Read-only (D-06). When ``show_zoom`` is
    set, each tile is followed by indented per-zoom-level lines (count + size)
    so custom higher-detail zones (ZL17/18/19) are visible, not just the base zl.
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
        if show_zoom:
            for zl, count, nbytes in zoom_breakdown(path):
                print(f"    ZL{zl:<3} {count:6d} tex {_human_size(nbytes):>9}")


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
    import tempfile

    # zoom_breakdown: buckets textures by trailing-2-digit ZL, skips non-tiles,
    # and parses provider codes that end in a digit (GO2 vs zl 18).
    with tempfile.TemporaryDirectory() as d:
        tex = os.path.join(d, "textures")
        os.makedirs(tex)
        for n in ("100_200_BI16.dds", "101_200_BI16.dds", "100_201_BI18.dds",
                  "50_60_GO218.dds", "water_transition.png"):
            with open(os.path.join(tex, n), "wb") as f:
                f.write(b"x")
        bd = zoom_breakdown(d)
        assert bd == [(16, 2, 2), (18, 2, 2)], bd  # GO218 -> zl 18, not 218
    assert zoom_breakdown(tempfile.gettempdir() + os.sep + "no_such_tile_dir") == []
    print("O4_Report_Utils self-check OK")
