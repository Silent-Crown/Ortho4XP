"""report tiles inventory: iter_tiles / read_tile_cfg / report_tiles (RPT-01)."""

import os

import O4_File_Names as FNAMES
import O4_Report_Utils as RPT


def _write_cfg(build_dir, lat, lon, provider, zl):
    path = os.path.join(build_dir, "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg")
    with open(path, "w") as f:
        f.write(f"# a comment\ndefault_website={provider}\ndefault_zl={zl}\n")


def test_iter_tiles(make_tile):
    make_tile(47, -122)
    make_tile(-9, 140)
    # a non-matching dir under Tiles/ must be ignored
    os.makedirs(os.path.join(FNAMES.Tile_dir, "not_a_tile"), exist_ok=True)
    got = sorted((lat, lon) for lat, lon, _ in RPT.iter_tiles())
    assert got == [(-9, 140), (47, -122)]


def test_read_tile_cfg(make_tile):
    build_dir = make_tile(47, -122)
    _write_cfg(build_dir, 47, -122, "BI", 17)
    provider, zoom = RPT.read_tile_cfg(build_dir, 47, -122)
    assert provider == "BI"
    assert zoom == "17"


def test_read_tile_cfg_missing(make_tile):
    build_dir = make_tile(47, -122)  # no cfg written
    provider, zoom = RPT.read_tile_cfg(build_dir, 47, -122)
    assert provider == "" and zoom == ""  # tolerated, not an error


def test_report_tiles_sorted(make_tile, capsys):
    for lat, lon, prov, zl in ((47, -122, "BI", 17), (-9, 140, "GO2", 16), (10, 10, "EOX", 18)):
        bd = make_tile(lat, lon)
        _write_cfg(bd, lat, lon, prov, zl)
    RPT.report_tiles()
    rows = [r for r in capsys.readouterr().out.splitlines() if r.strip()]
    data = [r for r in rows if "BI" in r or "GO2" in r or "EOX" in r]
    assert len(data) == 3
    # (lat,lon)-sorted: -9,140 then 10,10 then 47,-122
    assert data[0].index("GO2") >= 0
    assert "-09+140" in data[0] and "+10+010" in data[1] and "+47-122" in data[2]


def test_report_tiles_empty(make_tile, capsys):
    # make_tile creates an empty Tiles/ tree (no tiles built)
    make_tile(47, -122, with_dsf=False, with_textures=False)
    # remove the dir we just made so Tiles/ is empty
    import shutil
    shutil.rmtree(FNAMES.build_dir(47, -122, ""))
    RPT.report_tiles()
    out = capsys.readouterr().out.lower()
    assert "no tiles built" in out


def test_no_config_utils_import():
    src = os.path.join(os.path.dirname(RPT.__file__), "O4_Report_Utils.py")
    assert "import O4_Config_Utils" not in open(src).read()
