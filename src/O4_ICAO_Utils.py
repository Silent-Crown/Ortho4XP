"""Hand-rolled MCP-over-HTTP client resolving an ICAO code to (lat, lon).

Talks streamable-HTTP JSON-RPC to mcp_aviation_server with plain ``requests``
(D-02: no MCP SDK, no new runtime dep). Handshake: initialize -> capture
Mcp-Session-Id -> notifications/initialized -> tools/call get_airport_details.
Fails loud (never returns a coordinate on any failure path, D-04).
"""

import json

import requests


class AviationServerUnreachable(Exception):
    """Transport failure, JSON-RPC error, or DB-unavailable (D-04)."""


class ICAONotFound(Exception):
    """The server answered but the ICAO is unknown (D-04)."""


_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
_MAX_IDENT_LEN = 10


def _parse_body(resp):
    """Return the JSON-RPC envelope from an SSE or plain-JSON response body."""
    ctype = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ctype:
        chunks = [
            ln[5:].strip()
            for ln in resp.text.splitlines()
            if ln.startswith("data:")
        ]
        return json.loads("\n".join(chunks))
    return resp.json()


def resolve_icao(ident, base_url, timeout=10.0):
    """Resolve an ICAO ident to ``(latitude, longitude)`` floats.

    :param ident: ICAO code (case-insensitive, whitespace-trimmed).
    :param base_url: streamable-HTTP endpoint of mcp_aviation_server.
    :raises ValueError: empty / over-long ident (before any HTTP call).
    :raises AviationServerUnreachable: transport error, JSON-RPC error, DB down.
    :raises ICAONotFound: server up but ICAO unknown.
    """
    ident = ident.strip().upper()
    if not ident:
        raise ValueError("ICAO code must not be empty")
    if len(ident) > _MAX_IDENT_LEN:
        raise ValueError(
            f"ICAO code too long ({len(ident)} > {_MAX_IDENT_LEN}): {ident!r}"
        )

    session = requests.Session()
    try:
        init = session.post(base_url, headers=_HEADERS, timeout=timeout, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "Ortho4XP", "version": "1.0"}}})
        init.raise_for_status()
        sid = init.headers.get("Mcp-Session-Id")
        hdr = dict(_HEADERS, **{"MCP-Protocol-Version": "2025-06-18"})
        if sid:
            hdr["Mcp-Session-Id"] = sid
            session.post(base_url, headers=hdr, timeout=timeout,
                         json={"jsonrpc": "2.0",
                               "method": "notifications/initialized"})
        resp = session.post(base_url, headers=hdr, timeout=timeout, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "get_airport_details",
                       "arguments": {"ident": ident}}})
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise AviationServerUnreachable(
            f"aviation server unreachable at {base_url}: {e}"
        )

    env = _parse_body(resp)
    if "error" in env:  # JSON-RPC transport-level error
        raise AviationServerUnreachable(f"aviation server error: {env['error']}")
    try:
        payload = json.loads(env["result"]["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise AviationServerUnreachable(
            f"aviation server returned an unparseable response: {e}"
        )
    if payload.get("airport"):
        try:
            coords = payload["airport"]["coordinates"]
            lat = float(coords["latitude"])
            lon = float(coords["longitude"])
        except (KeyError, TypeError, ValueError) as e:
            raise AviationServerUnreachable(
                f"aviation server returned malformed coordinates: {e}"
            )
        if not _valid(lat, -90, 90) or not _valid(lon, -180, 180):
            raise AviationServerUnreachable(
                f"aviation server returned invalid coordinates: {lat}, {lon}"
            )
        return lat, lon
    code = payload.get("code")
    # Real mcp_aviation_server returns AIRPORT_NOT_FOUND for an unknown ICAO
    # (G-03-7); AIRPORT_DETAILS_ERROR kept in case both are live server codes.
    if code in ("AIRPORT_NOT_FOUND", "AIRPORT_DETAILS_ERROR"):
        raise ICAONotFound(f"ICAO {ident} not found")
    # SIM_DB_UNAVAILABLE and any other server-side code -> unreachable family.
    raise AviationServerUnreachable(
        f"aviation server could not answer ({code}): {payload.get('error')}"
    )


def _valid(x, lo, hi):
    import math
    return math.isfinite(x) and lo <= x <= hi


def get_server_url():
    """Read ``mcp_aviation_server_url`` from Ortho4XP.cfg, or the declared default.

    Lazy imports avoid pulling O4_Config_Utils / Tkinter into the resolver.
    """
    import O4_Report_Utils as RPT
    import O4_Cfg_Vars as CFG_VARS
    import O4_File_Names as FNAMES

    default = CFG_VARS.cfg_app_vars["mcp_aviation_server_url"]["default"]
    try:
        cfg = RPT.read_cfg(FNAMES.resource_path("Ortho4XP.cfg"))
    except OSError:
        return default
    return cfg.get("mcp_aviation_server_url") or default


if __name__ == "__main__":
    # ponytail: offline self-check — SSE parse + ident guards, no live server.
    class _R:
        headers = {"Content-Type": "text/event-stream"}
        text = ('event: message\ndata: {"jsonrpc":"2.0","id":2,'
                '"result":{"content":[{"type":"text","text":"{}"}]}}\n\n')
    assert _parse_body(_R())["result"]["content"][0]["text"] == "{}"
    for bad in ("", "   ", "A" * 11):
        try:
            resolve_icao(bad, "http://x/mcp")
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")
    print("O4_ICAO_Utils self-check OK")
