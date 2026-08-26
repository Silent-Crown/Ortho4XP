"""ICAO-driven batch build: parser surface, dispatch wiring, radius, batch policy.

All tests monkeypatch ``ICAO.resolve_icao``/``get_server_url`` and ``CLI.run_build``
so no real pipeline or aviation server is touched (mirrors test_coverage.py).
"""

import pytest

import O4_ICAO_Utils as ICAO
import O4_CLI_Utils as CLI


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _recorder(monkeypatch):
    """Monkeypatch CLI.run_build to record (lat, lon) calls; return the list."""
    calls = []
    monkeypatch.setattr(CLI, "run_build",
                        lambda lat, lon, provider=None, zl=None: calls.append((lat, lon)))
    return calls


def _resolver(monkeypatch, mapping):
    """Monkeypatch the resolver: mapping is ident -> (lat, lon) or an Exception."""
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")

    def _resolve(ident, url):
        val = mapping[ident.strip().upper()]
        if isinstance(val, Exception):
            raise val
        return val

    monkeypatch.setattr(ICAO, "resolve_icao", _resolve)


# --------------------------------------------------------------------------- #
# Task 1: parser surface + single-ICAO dispatch + legacy compatibility
# --------------------------------------------------------------------------- #
def test_build_parser_icao_surface():
    args = CLI.build_parser().parse_args(["build", "--icao", "KJFK"])
    assert args.command == "build"
    assert args.icao == "KJFK"
    assert args.icao_file is None
    assert args.radius == 0
    assert args.lat is None and args.lon is None


def test_dispatch_single_icao_builds_containing_tile(monkeypatch):
    calls = _recorder(monkeypatch)
    _resolver(monkeypatch, {"KJFK": (40.6398, -73.7789)})
    CLI.dispatch(["build", "--icao", "KJFK"])
    assert calls == [(40, -74)]


def test_dispatch_legacy_positional_still_builds(monkeypatch):
    # Legacy path forwards raw positional strings; run_build floors them itself.
    calls = _recorder(monkeypatch)
    CLI.dispatch(["build", "40", "-74"])
    assert calls == [("40", "-74")]


def test_dispatch_positional_plus_icao_is_usage_error(monkeypatch):
    _recorder(monkeypatch)
    _resolver(monkeypatch, {"KJFK": (40.6398, -73.7789)})
    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "40", "-74", "--icao", "KJFK"])
    assert exc.value.code == 2


# --------------------------------------------------------------------------- #
# Task 2: neighbor_tiles Chebyshev square, antimeridian wrap, pole skip
# --------------------------------------------------------------------------- #
def test_neighbor_radius_zero_is_containing_tile():
    assert CLI.neighbor_tiles(40.64, -73.78, 0) == [(40, -74)]


def test_neighbor_radius_one_is_sorted_3x3():
    tiles = CLI.neighbor_tiles(40.5, -73.5, 1)
    assert len(tiles) == 9
    assert tiles == sorted(tiles)
    for t in [(40, -74), (41, -73), (39, -75)]:
        assert t in tiles


def test_neighbor_antimeridian_wrap_both_directions():
    assert (0, -180) in CLI.neighbor_tiles(0.5, 179.5, 1)
    assert (0, 179) in CLI.neighbor_tiles(0.5, -179.5, 1)


def test_neighbor_pole_skip():
    tiles = CLI.neighbor_tiles(89.5, 0.5, 1)
    assert len(tiles) == 6
    assert all(lat <= 89 for lat, _ in tiles)


def test_radius_without_icao_source_is_usage_error(monkeypatch):
    _recorder(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "40", "-74", "--radius", "1"])
    assert exc.value.code == 2


# --------------------------------------------------------------------------- #
# Task 3: parse_icao_args + multi-ICAO batch failure policy
# --------------------------------------------------------------------------- #
def test_parse_icao_args_comma_list():
    assert CLI.parse_icao_args("KJFK, KLGA ,KEWR", None) == ["KJFK", "KLGA", "KEWR"]


def test_parse_icao_args_file_skips_comments_and_blanks(tmp_path):
    p = tmp_path / "airports.txt"
    p.write_text("# header note\n\nKJFK\n  # indented comment\nKLGA\n\n")
    assert CLI.parse_icao_args(None, str(p)) == ["KJFK", "KLGA"]


def test_parse_icao_args_missing_file_exits_clean(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        CLI.parse_icao_args(None, str(tmp_path / "does_not_exist.txt"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "does_not_exist.txt" in err
    assert "Traceback" not in err


def test_parse_icao_args_empty_file_exits_clean(tmp_path, capsys):
    p = tmp_path / "empty.txt"
    p.write_text("# only comments\n\n")
    with pytest.raises(SystemExit) as exc:
        CLI.parse_icao_args(None, str(p))
    assert exc.value.code != 0
    assert "Traceback" not in capsys.readouterr().err


def test_batch_dedupes_overlapping_radius_sets(monkeypatch):
    calls = _recorder(monkeypatch)
    # Two ICAOs two tiles apart on lon; radius-1 squares overlap in one column.
    # AAAA -> tile (40,-74) block cols {-75,-74,-73}; BBBB -> (40,-72) block cols
    # {-73,-72,-71}. Shared column -73 (3 tiles) -> 9+9-3 = 15 unique tiles.
    _resolver(monkeypatch, {"AAAA": (40.5, -73.5), "BBBB": (40.5, -71.5)})
    # all resolve + all build -> clean exit (no SystemExit)
    CLI.dispatch(["build", "--icao", "AAAA,BBBB", "--radius", "1"])
    assert len(calls) == len(set(calls)) == 15
    assert calls == sorted(calls)


def test_batch_unknown_icao_skipped_others_build(monkeypatch):
    calls = _recorder(monkeypatch)
    _resolver(monkeypatch, {
        "GOOD": (40.5, -73.5),
        "ZZZZ": ICAO.ICAONotFound("ICAO ZZZZ not found"),
    })
    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "--icao", "GOOD,ZZZZ"])
    assert exc.value.code == 1
    assert calls == [(40, -74)]


def test_batch_server_unreachable_aborts_before_any_build(monkeypatch, capsys):
    calls = _recorder(monkeypatch)
    _resolver(monkeypatch, {
        "GOOD": (40.5, -73.5),
        "DEAD": ICAO.AviationServerUnreachable("aviation server unreachable at http://x/mcp"),
    })
    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "--icao", "DEAD,GOOD"])
    assert exc.value.code == 1
    assert calls == []  # no partial builds
    assert "unreachable" in capsys.readouterr().err


def test_batch_tile_build_failure_continues(monkeypatch):
    built = []

    def _run(lat, lon, provider=None, zl=None):
        if (lat, lon) == (40, -74):
            raise RuntimeError("boom")
        built.append((lat, lon))

    monkeypatch.setattr(CLI, "run_build", _run)
    _resolver(monkeypatch, {"KJFK": (40.5, -73.5)})
    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "--icao", "KJFK", "--radius", "1"])
    assert exc.value.code == 1
    assert (40, -74) not in built
    assert len(built) == 8  # the other 8 of the 3x3 still built


def test_batch_all_success_exits_zero(monkeypatch):
    calls = _recorder(monkeypatch)
    _resolver(monkeypatch, {"KJFK": (40.5, -73.5)})
    # exit 0 == clean return, no SystemExit
    CLI.dispatch(["build", "--icao", "KJFK"])
    assert calls == [(40, -74)]


# --------------------------------------------------------------------------- #
# G-03-7: end-to-end batch skip through the REAL resolver (no ICAO.resolve_icao
# monkeypatch) — proves the real server not-found code reaches the skip branch.
# --------------------------------------------------------------------------- #
def test_batch_unknown_icao_real_resolver_skips_and_summarizes(
        monkeypatch, capsys):
    import requests
    import conftest

    def _fake_post(self, url, headers=None, timeout=None, json=None):
        body = json or {}
        if body.get("method") == "tools/call":
            ident = body["params"]["arguments"]["ident"]
            text = conftest.SSE_SUCCESS if ident == "KJFK" else conftest.SSE_NOT_FOUND
            return conftest.FakeResponse(text)
        # initialize handshake: hand back a session id, minimal valid envelope
        return conftest.FakeResponse(
            conftest.SSE_SUCCESS, headers={"Mcp-Session-Id": "sid-1"})

    monkeypatch.setattr(requests.Session, "post", _fake_post)
    monkeypatch.setattr(ICAO, "get_server_url", lambda: "http://x/mcp")
    calls = _recorder(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        CLI.dispatch(["build", "--icao", "ZZZZ,KJFK"])
    assert exc.value.code == 1
    assert calls == [(40, -74)]  # KJFK still built, ZZZZ skipped
    assert "1/2 ICAOs resolved" in capsys.readouterr().out
