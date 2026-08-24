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


def report_coverage(icao):
    """Resolve an ICAO and print the built/partial/missing status of its tile.

    Containing tile only (this plan); full 3x3 coverage lands in Plan 02.
    """
    import O4_ICAO_Utils as ICAO
    import O4_CLI_Utils as CLI

    lat_f, lon_f = ICAO.resolve_icao(icao, ICAO.get_server_url())
    lat = CLI.parse_lat(lat_f)
    lon = CLI.parse_lon(lon_f)
    print(f"{icao.strip().upper():<8} {FNAMES.short_latlon(lat, lon):<9} "
          f"{tile_status(lat, lon)}")


if __name__ == "__main__":
    assert read_cfg.__doc__  # trivially importable
    print("O4_Report_Utils self-check OK")
