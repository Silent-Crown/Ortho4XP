"""Shared pytest fixtures for the Ortho4XP CLI report/ICAO tests.

Puts repo ``src/`` on ``sys.path`` so tests import the bare ``O4_*`` modules,
provides a tmp-tree tile-dir factory (``make_tile``), and exposes canned
mcp_aviation_server response bodies (SSE- and plain-JSON-framed) so the resolver
can be tested with a monkeypatched ``requests.Session.post`` and no live server.
"""

import json
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# --------------------------------------------------------------------------- #
# Canned mcp_aviation_server response bodies
# --------------------------------------------------------------------------- #
# The tool return value is a JSON *string* nested at result.content[0].text
# (server returns model_dump_json()). Coordinates live at
# airport.coordinates.latitude/longitude.

# Fixture airport: KJFK-ish coordinates (containing tile +40-074).
JFK_LAT = 40.6398
JFK_LON = -73.7789

_SUCCESS_INNER = {
    "airport": {
        "ident": "KJFK",
        "coordinates": {"latitude": JFK_LAT, "longitude": JFK_LON},
    },
    "runways": [],
    "communications": [],
    "approaches": [],
}
_NOT_FOUND_INNER = {
    "error": "Airport not found: ZZZZ",
    "code": "AIRPORT_DETAILS_ERROR",
    "details": None,
}
_DB_DOWN_INNER = {
    "error": "Simulator database unavailable",
    "code": "SIM_DB_UNAVAILABLE",
    "details": None,
}


def _envelope(inner):
    """Wrap an inner tool payload in a JSON-RPC tools/call result envelope."""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [{"type": "text", "text": json.dumps(inner)}],
            "isError": False,
        },
    }


def _sse(inner):
    """Frame an envelope as an SSE ``event: message`` / ``data:`` body."""
    return "event: message\ndata: " + json.dumps(_envelope(inner)) + "\n\n"


def _json(inner):
    """The plain application/json variant (JSON-response-mode deploys)."""
    return json.dumps(_envelope(inner))


# SSE-framed bodies
SSE_SUCCESS = _sse(_SUCCESS_INNER)
SSE_NOT_FOUND = _sse(_NOT_FOUND_INNER)
SSE_DB_DOWN = _sse(_DB_DOWN_INNER)
# plain-JSON-framed bodies
JSON_SUCCESS = _json(_SUCCESS_INNER)
JSON_NOT_FOUND = _json(_NOT_FOUND_INNER)


class FakeResponse:
    """Minimal stand-in for requests.Response for monkeypatched Session.post."""

    def __init__(self, text, content_type="text/event-stream",
                 headers=None, status_code=200):
        self.text = text
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        if headers:
            self.headers.update(headers)

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(f"{self.status_code}")

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def make_tile(tmp_path, monkeypatch):
    """Factory: create a Tiles/ tree for one tile under tmp_path.

    Monkeypatches ``O4_File_Names.Tile_dir`` / ``Tmp_dir`` at the tmp tree so the
    report predicate reads the fixture instead of the real repo. Returns the
    tile's ``build_dir`` path.

    Switches:
      with_dsf     — write a non-empty <latlon>.dsf (default True)
      with_textures— create textures/ (default True)
      empty_textures — leave textures/ empty (default False; else drops a file)
      dsf_tmp      — also leave a <latlon>.dsf.tmp leftover (default False)
      data_leftover— also leave a Data<latlon>.poly leftover (default False)
    """
    import O4_File_Names as FNAMES

    tiles = tmp_path / "Tiles"
    tmp = tmp_path / "tmp"
    tiles.mkdir()
    tmp.mkdir()
    monkeypatch.setattr(FNAMES, "Tile_dir", str(tiles))
    monkeypatch.setattr(FNAMES, "Tmp_dir", str(tmp))

    def _make(lat, lon, *, with_dsf=True, with_textures=True,
              empty_textures=False, dsf_tmp=False, data_leftover=False):
        build_dir = FNAMES.build_dir(lat, lon, "")
        os.makedirs(build_dir, exist_ok=True)
        dsf = FNAMES.dsf_file(build_dir, lat, lon)
        os.makedirs(os.path.dirname(dsf), exist_ok=True)
        if with_dsf:
            with open(dsf, "wb") as f:
                f.write(b"DSF fixture payload")
        if dsf_tmp:
            with open(dsf + ".tmp", "wb") as f:
                f.write(b"partial")
        if with_textures:
            tex = os.path.join(build_dir, "textures")
            os.makedirs(tex, exist_ok=True)
            if not empty_textures:
                with open(os.path.join(tex, "0_0_x16.dds"), "wb") as f:
                    f.write(b"dds")
        if data_leftover:
            short = FNAMES.short_latlon(lat, lon)
            with open(os.path.join(build_dir, "Data" + short + ".poly"), "w") as f:
                f.write("poly")
        return build_dir

    return _make
