"""Read-only tile coverage reporting (RPT-01/RPT-02).

Reads the existing Tiles/ tree via FNAMES paths only; never imports
O4_Config_Utils (which runs exec()-based global mutation and drags in Tkinter)
and never writes anything to disk.
"""

import os

import O4_File_Names as FNAMES


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


def tile_status(lat, lon):
    """The D-05 predicate: ``missing`` / ``built`` / ``partial`` for one tile.

    ``built`` requires a non-empty DSF AND a non-empty ``textures/`` dir; a build
    dir that exists but fails either check is ``partial`` (never ``built``).
    """
    build_dir = FNAMES.build_dir(lat, lon, "")
    if not os.path.isdir(build_dir):
        return "missing"
    dsf = FNAMES.dsf_file(build_dir, lat, lon)
    tex = os.path.join(build_dir, "textures")
    dsf_ok = os.path.isfile(dsf) and os.path.getsize(dsf) > 0
    tex_ok = os.path.isdir(tex) and bool(os.listdir(tex))
    if dsf_ok and tex_ok:
        return "built"
    return "partial"


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


def report_coverage(icao):
    """Resolve an ICAO and print the built/partial/missing status of its 3x3 block.

    Reports the containing tile plus its 8 neighbors (D-11). The two resolver
    failures fail loud on a single stderr line with a non-zero exit (D-04) — no
    traceback, no coordinate, no tile rows.
    """
    import sys

    import O4_ICAO_Utils as ICAO

    ident = icao.strip().upper()
    try:
        lat_f, lon_f = ICAO.resolve_icao(ident, ICAO.get_server_url())
    except (ICAO.AviationServerUnreachable, ICAO.ICAONotFound) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    for lat, lon in coverage_tiles(lat_f, lon_f):
        print(f"{ident:<8} {FNAMES.short_latlon(lat, lon):<9} "
              f"{tile_status(lat, lon)}")


if __name__ == "__main__":
    assert read_cfg.__doc__  # trivially importable
    print("O4_Report_Utils self-check OK")
