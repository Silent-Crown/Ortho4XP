"""Unit tests for the hand-rolled MCP-over-HTTP ICAO resolver (BUILD-01)."""

import math

import pytest
import requests

import O4_ICAO_Utils as ICAO
import conftest


def _fake_post_factory(response, session_id="sess-1"):
    """Return a Session.post replacement yielding `response` with a session id."""
    calls = []

    def _post(self, url, **kwargs):
        calls.append((url, kwargs))
        if isinstance(response, Exception):
            raise response
        return conftest.FakeResponse(
            response, headers={"Mcp-Session-Id": session_id}
        )

    _post.calls = calls
    return _post


def test_resolve_ok(monkeypatch):
    post = _fake_post_factory(conftest.SSE_SUCCESS)
    monkeypatch.setattr(requests.Session, "post", post)
    lat, lon = ICAO.resolve_icao("kjfk", "http://x/mcp")
    assert isinstance(lat, float) and isinstance(lon, float)
    assert lat == pytest.approx(conftest.JFK_LAT)
    assert lon == pytest.approx(conftest.JFK_LON)


def test_resolve_unreachable(monkeypatch):
    err = requests.exceptions.ConnectionError("refused")
    monkeypatch.setattr(requests.Session, "post", _fake_post_factory(err))
    with pytest.raises(ICAO.AviationServerUnreachable) as exc:
        ICAO.resolve_icao("KJFK", "http://host:8000/mcp")
    assert "http://host:8000/mcp" in str(exc.value)


def test_resolve_empty_ident(monkeypatch):
    def _boom(self, url, **kwargs):
        raise AssertionError("post must not be called for empty ident")

    monkeypatch.setattr(requests.Session, "post", _boom)
    with pytest.raises(ValueError):
        ICAO.resolve_icao("   ", "http://x/mcp")


def test_resolve_long_ident(monkeypatch):
    def _boom(self, url, **kwargs):
        raise AssertionError("post must not be called for over-long ident")

    monkeypatch.setattr(requests.Session, "post", _boom)
    with pytest.raises(ValueError):
        ICAO.resolve_icao("A" * 11, "http://x/mcp")


def test_parse_body_sse():
    sse = conftest.FakeResponse(conftest.SSE_SUCCESS)
    env = ICAO._parse_body(sse)
    assert env["result"]["content"][0]["type"] == "text"
    plain = conftest.FakeResponse(
        conftest.JSON_SUCCESS, content_type="application/json"
    )
    assert ICAO._parse_body(plain)["result"]["content"][0]["type"] == "text"


def test_resolve_not_found(monkeypatch):
    post = _fake_post_factory(conftest.SSE_NOT_FOUND)
    monkeypatch.setattr(requests.Session, "post", post)
    with pytest.raises(ICAO.ICAONotFound):
        ICAO.resolve_icao("ZZZZ", "http://x/mcp")


def test_resolve_coords_are_finite(monkeypatch):
    post = _fake_post_factory(conftest.SSE_SUCCESS)
    monkeypatch.setattr(requests.Session, "post", post)
    lat, lon = ICAO.resolve_icao("KJFK", "http://x/mcp")
    assert math.isfinite(lat) and math.isfinite(lon)
