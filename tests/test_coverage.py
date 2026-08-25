"""End-to-end coverage report over a fixture tile (RPT-02, tracer slice)."""

import O4_ICAO_Utils as ICAO
import O4_Report_Utils as RPT
import O4_CLI_Utils as CLI


def test_parser_surface():
    args = CLI.build_parser().parse_args(["report", "coverage", "--icao", "KJFK"])
    assert args.command == "report"
    assert args.report_cmd == "coverage"
    assert args.icao == "KJFK"


def test_coverage_containing_tile_built(make_tile, monkeypatch, capsys):
    make_tile(40, -74)  # built tile +40-074
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")
    monkeypatch.setattr(ICAO, "resolve_icao", lambda icao, url: (40.6398, -73.7789))
    RPT.report_coverage("KJFK")
    out = capsys.readouterr().out
    assert "built" in out


def test_coverage_containing_tile_missing(make_tile, monkeypatch, capsys):
    make_tile(40, -74)  # exists, but resolver points elsewhere
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")
    monkeypatch.setattr(ICAO, "resolve_icao", lambda icao, url: (10.5, 10.5))
    RPT.report_coverage("XXXX")
    out = capsys.readouterr().out
    assert "missing" in out


def test_tile_status_partial(make_tile):
    # dsf present but textures empty -> partial, never built (edge RPT-01/shared predicate)
    make_tile(40, -74, empty_textures=True)
    assert RPT.tile_status(40, -74) == "partial"


def test_tile_status_built_and_missing(make_tile):
    make_tile(40, -74)
    assert RPT.tile_status(40, -74) == "built"
    assert RPT.tile_status(10, 10) == "missing"


def test_coverage_block(make_tile, monkeypatch, capsys):
    # Containing tile +40-074 built, one neighbor +41-074 partial, rest missing.
    make_tile(40, -74)
    make_tile(41, -74, empty_textures=True)  # partial
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")
    monkeypatch.setattr(ICAO, "resolve_icao", lambda icao, url: (40.6398, -73.7789))
    RPT.report_coverage("KJFK")
    out = capsys.readouterr().out
    rows = [r for r in out.splitlines() if r.strip()]
    assert len(rows) == 9  # full 3x3 block, none off-grid
    assert sum(r.endswith("built") for r in rows) == 1
    assert sum(r.endswith("partial") for r in rows) == 1
    assert sum(r.endswith("missing") for r in rows) == 7


def test_coverage_unreachable_exit(monkeypatch, capsys):
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")

    def _boom(icao, url):
        raise ICAO.AviationServerUnreachable("aviation server unreachable at http://x/mcp")

    monkeypatch.setattr(ICAO, "resolve_icao", _boom)
    import pytest
    with pytest.raises(SystemExit) as exc:
        RPT.report_coverage("KJFK")
    assert exc.value.code != 0
    cap = capsys.readouterr()
    assert "unreachable" in cap.err
    assert cap.out == ""  # no tile rows, no coordinate


def test_coverage_unknown_exit(monkeypatch, capsys):
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")

    def _boom(icao, url):
        raise ICAO.ICAONotFound("ICAO ZZZZ not found")

    monkeypatch.setattr(ICAO, "resolve_icao", _boom)
    import pytest
    with pytest.raises(SystemExit) as exc:
        RPT.report_coverage("ZZZZ")
    assert exc.value.code != 0
    cap = capsys.readouterr()
    assert "not found" in cap.err.lower()
    assert cap.out == ""


def test_coverage_skips_offgrid(make_tile, monkeypatch, capsys):
    # Near the NE grid corner: neighbors at lat 90 / lon 180 must be skipped.
    make_tile(89, 179)
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")
    monkeypatch.setattr(ICAO, "resolve_icao", lambda icao, url: (89.5, 179.5))
    RPT.report_coverage("XXXX")  # must not raise
    rows = [r for r in capsys.readouterr().out.splitlines() if r.strip()]
    assert 0 < len(rows) < 9  # off-grid neighbors dropped


def test_coverage_tiles_block():
    tiles = list(RPT.coverage_tiles(40.5, -73.5))
    assert len(tiles) == 9
    assert (40, -74) in tiles
    assert (41, -73) in tiles and (39, -75) in tiles


def test_read_cfg_plain_text(tmp_path):
    p = tmp_path / "Ortho4XP.cfg"
    p.write_text("# comment\nmcp_aviation_server_url=http://h:9/mcp\n\nverbosity=2\n")
    d = RPT.read_cfg(str(p))
    assert d["mcp_aviation_server_url"] == "http://h:9/mcp"
    assert d["verbosity"] == "2"
