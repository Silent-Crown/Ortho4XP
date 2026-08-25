# API Coverage — mcp_aviation_server

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Verified against `../mcp_aviation_server/src/mcp_aviation/server.py` (RESEARCH.md §API Coverage Decision).

Phase 2 integrates exactly one external API: `mcp_aviation_server` (streamable-HTTP MCP,
tools-only). BUILD-01 / RPT-02 need only ICAO→lat/lon, so `get_airport_details` is the one
tool integrated; every other tool is deferred to Phase 3+.

| capability | decision | reason |
|---|---|---|
| get_airport_details | INTEGRATE | The one call BUILD-01/RPT-02 need — exact-ident lookup returning `airport.coordinates.latitude/longitude`; raises a clean not-found (the precise D-04 signal). |
| search_airports | OPT-OUT | not needed this phase — fuzzy `LIKE` returns an ambiguous list; exact lookup preferred. Deferred to Phase 3+. |
| find_nearby_airports | OPT-OUT | not needed this phase — radius search is in nautical miles; Phase 3 `--radius` is whole tiles (different model). Deferred to Phase 3+. |
| get_airport_runways | OPT-OUT | not needed this phase — no runway data required for coordinate resolution. Deferred to Phase 3+. |
| get_airport_communications | OPT-OUT | not needed this phase — no comms data required. Deferred to Phase 3+. |
| get_airport_approaches | OPT-OUT | not needed this phase — no approach data required. Deferred to Phase 3+. |
| get_airport_parking | OPT-OUT | not needed this phase — no parking data required. Deferred to Phase 3+. |
| get_waypoint_info | OPT-OUT | not needed this phase — nav fixes out of scope. Deferred to Phase 3+. |
| get_navaid_info | OPT-OUT | not needed this phase — nav fixes out of scope. Deferred to Phase 3+. |
| get_approaches_with_transitions | OPT-OUT | not needed this phase — procedure detail out of scope. Deferred to Phase 3+. |
| get_approach_transitions_legs | OPT-OUT | not needed this phase — procedure detail out of scope. Deferred to Phase 3+. |
| get_approach | OPT-OUT | not needed this phase — procedure detail out of scope. Deferred to Phase 3+. |
| list_simulators | OPT-OUT | not needed this phase — multi-sim profile management is a server-side concern; default profile is fine. Deferred to Phase 3+. |
| get_active_simulator | OPT-OUT | not needed this phase — default sim profile is fine. Deferred to Phase 3+. |
| set_active_simulator | OPT-OUT | not needed this phase — read-only phase; never mutates server state. Deferred to Phase 3+. |
