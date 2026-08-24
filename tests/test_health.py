"""report health: partial tiles + crashed-run leftovers, read-only (RPT-03/D-07)."""

import hashlib
import os

import O4_File_Names as FNAMES
import O4_Report_Utils as RPT


def _tree_digest(root):
    """A stable digest of every file path + size under root (mutation detector)."""
    h = hashlib.sha256()
    for dirpath, _dirs, files in sorted(os.walk(root)):
        for name in sorted(files):
            p = os.path.join(dirpath, name)
            h.update(p.encode())
            h.update(str(os.path.getsize(p)).encode())
    return h.hexdigest()


def test_health_partial_dsftmp(make_tile, capsys):
    make_tile(40, -74, with_dsf=False, dsf_tmp=True)
    RPT.report_health()
    out = capsys.readouterr().out
    assert "+40-074" in out and ".dsf.tmp" in out


def test_health_partial_data_intermediates(make_tile, capsys):
    make_tile(40, -74, with_dsf=False, data_leftover=True)
    RPT.report_health()
    out = capsys.readouterr().out
    assert "+40-074" in out and "Data" in out


def test_health_empty_textures(make_tile, capsys):
    make_tile(40, -74, empty_textures=True)  # dsf present, textures/ empty
    RPT.report_health()
    out = capsys.readouterr().out
    assert "+40-074" in out and "textures" in out


def test_health_clean(make_tile, capsys):
    make_tile(40, -74)  # fully built
    RPT.report_health()
    out = capsys.readouterr().out
    assert "+40-074" not in out
    assert "no issues" in out.lower()


def test_health_global_tmp(make_tile, capsys):
    make_tile(40, -74)  # fully built, no per-tile issue
    with open(os.path.join(FNAMES.Tmp_dir, "leftover.bin"), "wb") as f:
        f.write(b"junk")
    RPT.report_health()
    out = capsys.readouterr().out.lower()
    assert "tmp" in out


def test_health_read_only(make_tile):
    bd = make_tile(40, -74, with_dsf=False, dsf_tmp=True, data_leftover=True)
    with open(os.path.join(FNAMES.Tmp_dir, "leftover.bin"), "wb") as f:
        f.write(b"junk")
    root = os.path.dirname(bd)  # Tiles/
    before = _tree_digest(FNAMES.Tile_dir) + _tree_digest(FNAMES.Tmp_dir)
    RPT.report_health()
    after = _tree_digest(FNAMES.Tile_dir) + _tree_digest(FNAMES.Tmp_dir)
    assert before == after  # nothing deleted, moved, or added
