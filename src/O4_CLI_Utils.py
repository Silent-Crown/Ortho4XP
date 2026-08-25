import sys
import math
import traceback
import argparse

import O4_Report_Utils as RPT

cmd_line = "USAGE: Ortho4XP.py lat lon imagery zl (won't read a tile config)\n  OR:  Ortho4XP.py lat lon (with existing tile config file)"

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
    if not math.isfinite(f):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    n = math.floor(f)
    if not (lo <= n <= hi):
        raise ValueError(f"{name} {n} out of range [{lo}, {hi}]")
    return n


def parse_lat(value):
    return parse_and_floor_coord(value, lo=-90, hi=89, name="lat")


def parse_lon(value):
    return parse_and_floor_coord(value, lo=-180, hi=179, name="lon")


##############################################################################
def neighbor_tiles(lat, lon, radius=0):
    """Deduped, (lat,lon)-sorted Chebyshev square of tiles around (lat, lon).

    Floors the input to a base tile, then walks dlat/dlon over -radius..radius.
    Latitude never wraps: a neighbor past +/-90 is skipped (D-08). Longitude
    wraps across the antimeridian into [-180, 179] with modular arithmetic so a
    neighbor past the seam maps to the real far-side tile (D-07). radius 0
    yields just the containing tile.

    :returns: sorted list of unique ``(lat, lon)`` integer tile pairs.
    """
    base_lat = parse_lat(lat)
    base_lon = parse_lon(lon)
    tiles = set()
    for dlat in range(-radius, radius + 1):
        nlat = base_lat + dlat
        if not (-90 <= nlat <= 89):
            continue  # latitude never wraps past a pole (D-08)
        for dlon in range(-radius, radius + 1):
            nlon = ((base_lon + dlon + 180) % 360) - 180  # antimeridian wrap (D-07)
            tiles.add((nlat, nlon))
    return sorted(tiles)


##############################################################################
def parse_icao_args(icao, icao_file):
    """Resolve --icao / --icao-file into a list of ICAO idents.

    ``icao`` is comma-split, tokens stripped, empties dropped. ``icao_file`` is
    read one ident per line, skipping blank lines and lines whose first
    non-space char is ``#`` (D-03/BUILD-05). A missing/unreadable file or an
    empty ident list prints one clean stderr line and exits non-zero — never a
    traceback (T-03-01).
    """
    if icao_file is not None:
        try:
            with open(icao_file, "r") as f:
                lines = f.readlines()
        except OSError as e:
            print(f"cannot read ICAO file {icao_file!r}: {e.strerror or e}",
                  file=sys.stderr)
            sys.exit(1)
        idents = [
            s for s in (ln.strip() for ln in lines)
            if s and not s.startswith("#")
        ]
    else:
        idents = [s for s in (t.strip() for t in (icao or "").split(",")) if s]
    if not idents:
        print("no ICAOs to build", file=sys.stderr)
        sys.exit(1)
    return idents


##############################################################################
def run_batch_build(idents, radius, provider=None, zl=None):
    """Resolve every ICAO, assemble a unique sorted tile set, build each once.

    Resolves ALL idents before building any tile so an abort leaves no partial
    builds. ``ICAONotFound`` skips-and-summarizes the ident (D-10);
    ``AviationServerUnreachable`` aborts the whole batch immediately, before any
    build (D-11). Resolved coords expand through ``neighbor_tiles`` and dedupe
    into one set (D-15), built in (lat,lon)-sorted order (D-17). A tile that
    raises during build is logged and the next tile still builds (D-12). Exits 1
    if any ICAO failed to resolve OR any tile failed to build, else returns so
    the process exits 0 (D-13).
    """
    import O4_ICAO_Utils as ICAO

    url = ICAO.get_server_url()
    tiles = set()
    unresolved = []
    for ident in idents:
        try:
            lat, lon = ICAO.resolve_icao(ident, url)
        except ICAO.AviationServerUnreachable as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)  # D-11: abort before any build
        except (ICAO.ICAONotFound, ValueError) as e:
            print(f"skipping {ident}: {e}", file=sys.stderr)
            unresolved.append(ident)
            continue
        tiles.update(neighbor_tiles(lat, lon, radius))

    built = failed = 0
    for lat, lon in sorted(tiles):
        try:
            run_build(lat, lon, provider, zl)
            built += 1
        except Exception as e:  # D-12: log and continue to the next tile
            print(f"tile ({lat},{lon}) failed: {e}", file=sys.stderr)
            failed += 1

    print(f"batch: {len(idents) - len(unresolved)}/{len(idents)} ICAOs resolved, "
          f"{built} tiles built, {failed} failed")
    if unresolved or failed:
        sys.exit(1)  # D-13: binary exit


##############################################################################
def _validate_build(parser, args):
    """Cross-field usage validation for `build` (D-02/D-04); calls parser.error (exit 2)."""
    has_icao = args.icao is not None or args.icao_file is not None
    has_pos = args.lat is not None or args.lon is not None
    if has_icao and has_pos:
        parser.error("give either lat/lon or an ICAO source, not both")
    if not has_icao and not has_pos:
        parser.error("build needs lat/lon or --icao/--icao-file")
    if has_pos and (args.lat is None or args.lon is None):
        parser.error("positional build needs both lat and lon")
    if not has_icao and args.radius:
        parser.error("--radius requires an ICAO source")
    if args.radius < 0:
        parser.error("--radius must be >= 0")


##############################################################################
def build_parser():
    """Build the argparse tree: one `build` subcommand with lat/lon + --provider/--zl."""
    parser = argparse.ArgumentParser(
        prog="Ortho4XP.py",
        description="Ortho4XP scenery generation tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser(
        "build", help="Build 1x1 degree tiles by lat/lon or ICAO code(s)"
    )
    # lat/lon optional so an ICAO source can stand in for them (compat: a bare
    # `build lat lon` still works via _validate_build).
    build_p.add_argument("lat", nargs="?", default=None,
                         help="SW corner latitude (integer or decimal)")
    build_p.add_argument("lon", nargs="?", default=None,
                         help="SW corner longitude (integer or decimal)")
    icao_group = build_p.add_mutually_exclusive_group()
    icao_group.add_argument("--icao", default=None,
                            help="ICAO code or comma-separated list (e.g. KJFK,KLGA)")
    icao_group.add_argument("--icao-file", dest="icao_file", default=None,
                            help="Path to a file of ICAO codes, one per line")
    build_p.add_argument("--radius", type=int, default=0,
                         help="Chebyshev radius in whole tiles around each ICAO (default 0)")
    build_p.add_argument("--provider", default=None, help="Imagery provider code")
    build_p.add_argument("--zl", type=int, default=None, help="Zoom level")

    # D-08: nest all reports under one `report` subcommand.
    report_p = subparsers.add_parser(
        "report", help="Report on already-built tiles (read-only)"
    )
    report_sub = report_p.add_subparsers(dest="report_cmd", required=True)
    report_sub.add_parser("tiles", help="List built/partial/missing tiles")
    cov_p = report_sub.add_parser(
        "coverage", help="Report coverage of an ICAO's containing tile"
    )
    cov_p.add_argument("--icao", required=True, help="ICAO airport code")
    report_sub.add_parser("health", help="Report crashed-run leftovers")

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
def _is_number(s):
    """True if s parses as a float — used only to sniff legacy coordinate argv."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


##############################################################################
def run_legacy(argv):
    """Legacy `lat lon [provider zl]` compatibility path (pre-argparse shape).

    Matches the original inline block's argument-count tolerance: 2 tokens read
    an existing tile config; 4+ tokens override provider/zl (trailing tokens
    ignored). Usage errors now exit non-zero (was exit 0).
    """
    if len(argv) < 2:
        print(cmd_line)
        sys.exit(1)
    if len(argv) == 2:
        run_build(argv[0], argv[1])
        return
    try:
        provider = argv[2]
        zl = int(argv[3])
    except (IndexError, ValueError):
        print(cmd_line)
        sys.exit(1)
    run_build(argv[0], argv[1], provider=provider, zl=zl)


##############################################################################
def dispatch(argv):
    """Top-level CLI entry: raw-argv legacy sniff first, then argparse.

    The sniff must run before build_parser().parse_args() — argparse's
    required=True subparser calls sys.exit(2) on any unrecognized token, so a
    bare `lat lon` would never reach the legacy branch otherwise.
    """
    if len(argv) >= 2 and _is_number(argv[0]) and _is_number(argv[1]):
        run_and_report(run_legacy, argv)
        return
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        _validate_build(parser, args)
        if args.icao is not None or args.icao_file is not None:
            idents = parse_icao_args(args.icao, args.icao_file)
            run_and_report(run_batch_build, idents, args.radius,
                           args.provider, args.zl)
        else:
            run_and_report(run_build, args.lat, args.lon, args.provider, args.zl)
    elif args.command == "report":
        if args.report_cmd == "coverage":
            run_and_report(RPT.report_coverage, args.icao)
        elif args.report_cmd == "tiles":
            run_and_report(RPT.report_tiles)
        elif args.report_cmd == "health":
            run_and_report(RPT.report_health)


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
    assert _is_number("47") is True
    assert _is_number("-122.5") is True
    assert _is_number("build") is False
    _a = build_parser().parse_args(["build", "--icao", "KJFK"])
    assert _a.icao == "KJFK" and _a.radius == 0 and _a.lat is None
    assert neighbor_tiles(40.64, -73.78, 0) == [(40, -74)]
    assert len(neighbor_tiles(40.5, -73.5, 1)) == 9
    assert (0, -180) in neighbor_tiles(0.5, 179.5, 1)  # antimeridian wrap
    assert len(neighbor_tiles(89.5, 0.5, 1)) == 6  # pole skip
    assert parse_icao_args("KJFK, KLGA ,KEWR", None) == ["KJFK", "KLGA", "KEWR"]
    print("O4_CLI_Utils self-check OK")
