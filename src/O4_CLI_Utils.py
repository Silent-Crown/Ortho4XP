import sys
import math
import traceback
import argparse

##############################################################################
def parse_and_floor_coord(value, *, lo, hi, name):
    """Parse a coordinate string, floor to the containing tile, range-check.

    Uses math.floor (toward negative infinity) so negative and decimal
    inputs map to the correct containing 1x1 degree tile, unlike int()
    truncation toward zero.

    :param value: raw coordinate string (e.g. "-0.5", "47.9")
    :param lo: inclusive lower bound for the floored value
    :param hi: inclusive upper bound for the floored value
    :param name: coordinate name for error messages ("lat"/"lon")
    :returns: floored integer coordinate
    :raises ValueError: if not a number or out of [lo, hi]
    """
    try:
        f = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a number, got {value!r}")
    n = math.floor(f)
    if not (lo <= n <= hi):
        raise ValueError(f"{name} {n} out of range [{lo}, {hi}]")
    return n


def parse_lat(value):
    return parse_and_floor_coord(value, lo=-90, hi=89, name="lat")


def parse_lon(value):
    return parse_and_floor_coord(value, lo=-180, hi=179, name="lon")


##############################################################################
def build_parser():
    """Build the argparse tree: one `build` subcommand with lat/lon + --provider/--zl."""
    parser = argparse.ArgumentParser(
        prog="Ortho4XP.py",
        description="Ortho4XP scenery generation tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser(
        "build", help="Build a single 1x1 degree tile"
    )
    build_p.add_argument("lat", help="SW corner latitude (integer or decimal)")
    build_p.add_argument("lon", help="SW corner longitude (integer or decimal)")
    build_p.add_argument("--provider", default=None, help="Imagery provider code")
    build_p.add_argument("--zl", type=int, default=None, help="Zoom level")

    return parser


##############################################################################
def run_build(lat, lon, provider=None, zl=None):
    """Floor/validate coordinates, construct the Tile, run the 4-stage pipeline.

    Build-module imports are done lazily here (not at module top) to preserve
    the CFG-imported-last constraint: importing O4_Config_Utils runs exec()-based
    mutation of other modules' globals, which must happen only after Ortho4XP.py's
    own top-level import block has already established that order.
    """
    import O4_Config_Utils as CFG
    import O4_Vector_Map as VMAP
    import O4_Mesh_Utils as MESH
    import O4_Mask_Utils as MASK
    import O4_Tile_Utils as TILE

    lat_f = parse_lat(lat)
    lon_f = parse_lon(lon)
    tile = CFG.Tile(lat_f, lon_f, '')
    if provider is not None:
        tile.default_website = provider
    if zl is not None:
        tile.default_zl = zl
    VMAP.build_poly_file(tile)
    MESH.build_mesh(tile)
    MASK.build_masks(tile)
    TILE.build_tile(tile)
    print("Bon vol!")


##############################################################################
def run_and_report(fn, *args, **kwargs):
    """Run fn, printing a real traceback to stderr and exiting 1 on failure.

    Replaces the old bare `except: print("Crash!")` catch-all. SystemExit
    (argparse usage errors, intentional exits) passes through unmodified.
    """
    try:
        fn(*args, **kwargs)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


##############################################################################
def dispatch(argv):
    """Top-level CLI entry: parse argv and route to the build subcommand."""
    args = build_parser().parse_args(argv)
    if args.command == "build":
        run_and_report(run_build, args.lat, args.lon, args.provider, args.zl)


##############################################################################
if __name__ == "__main__":
    assert parse_lat("-0.5") == -1
    assert parse_lon("47.5") == 47
    assert parse_lat("47.9") == 47
    assert parse_lon("-122.1") == -123
    try:
        parse_lat("999")
    except ValueError:
        pass
    else:
        raise AssertionError("parse_lat('999') should raise ValueError")
    try:
        parse_lon("not-a-number")
    except ValueError:
        pass
    else:
        raise AssertionError("parse_lon('not-a-number') should raise ValueError")
    print("O4_CLI_Utils self-check OK")
