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


def test_read_cfg_plain_text(tmp_path):
    p = tmp_path / "Ortho4XP.cfg"
    p.write_text("# comment\nmcp_aviation_server_url=http://h:9/mcp\n\nverbosity=2\n")
    d = RPT.read_cfg(str(p))
    assert d["mcp_aviation_server_url"] == "http://h:9/mcp"
    assert d["verbosity"] == "2"
