# Phase 3: ICAO-Driven Build - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver ICAO-driven, unattended tile builds by spending the Phase 2 resolver.
Delivers BUILD-02..05:

- BUILD-02: Build the 1°×1° tile containing a given ICAO with a single command.
- BUILD-03: `--radius N` also builds neighboring tiles within N whole tiles
  (Chebyshev square), handling negative coords and antimeridian wraparound.
- BUILD-04: Build for multiple ICAOs in one invocation (`--icao KJFK,KLGA,KEWR`).
- BUILD-05: Build from a list file of ICAOs (one per line, `#` comments ignored)
  for unattended/scheduled runs.

This phase is build orchestration only. It reuses the existing resolver
(`O4_ICAO_Utils`) and the shared `run_build` pipeline from Phase 1 — it does not
change build-pipeline algorithms, the resolver, or report commands. `--dry-run`
and `--json` stay v1.x-deferred. Skip-already-built stays v2-deferred.

</domain>

<decisions>
## Implementation Decisions

### Command Surface & Flags (BUILD-02/04/05)
- **D-01:** Add `--icao` and `--icao-file` to the **existing `build` subcommand**
  (not a new `build-icao` subcommand). One build entry point, reuses `run_build`.
  — **Reversibility:** reversible — flags on the existing parser.
- **D-02:** Positional `lat lon`, `--icao`, and `--icao-file` are **mutually
  exclusive — exactly one source per invocation**. Passing two is an argparse
  usage error (exit 2). Implement as an argparse mutually-exclusive group.
- **D-03:** `--icao` takes a **comma-separated list** (`--icao KJFK,KLGA,KEWR`).
  `--icao-file PATH` reads a list file: one ICAO per line, blank lines and
  `#` comments ignored (matches REQUIREMENTS BUILD-05 wording).
- **D-04:** `--radius N` is **valid only with `--icao`/`--icao-file`**, not with
  positional `lat lon`. Using `--radius` with a positional build is a usage error.
- **D-05:** `--provider` / `--zl` are **reused unchanged** and applied uniformly
  to every resolved/neighbor tile. Omitted → per-tile config / global defaults,
  exactly like today's positional `build`.

### Radius & Neighbor Generation (BUILD-03)
- **D-06:** `--radius N` = **Chebyshev square**, the `(2N+1)×(2N+1)` block of whole
  tiles centered on the containing tile. `radius 0` = just the containing tile.
  Generalizes Phase 2's 3×3 `coverage_tiles`.
- **D-07:** **Longitude wraps at the antimeridian** (mod 360): a neighbor of
  lon 179 includes lon −180. A radius near the dateline builds the real
  neighboring tiles rather than silently omitting them.
- **D-08:** **Latitude does NOT wrap.** Neighbors that fall outside [−90, 89]
  (past the poles) are skipped — no tile exists past the grid edge.
- **D-09:** Build a **new radius/neighbor generator** (with the D-07 wrap) for the
  build path. **Leave Phase 2 `O4_Report_Utils.coverage_tiles()` as-is** — its
  off-grid *skip* is a documented report-side v1.x decision; do NOT retrofit the
  report's antimeridian behavior in this phase. — **Reversibility:** costly —
  unifying the two later touches both build and report call sites.

### Batch Failure Policy (BUILD-04/05 — unattended runs)
- **D-10:** **Unknown ICAO → skip and continue.** A single bad/typo'd code does not
  abandon the batch; it is recorded and reported in the end-of-run summary.
- **D-11:** **Server-unreachable → abort the whole batch immediately** with a clear
  message. Distinguishes `ICAONotFound` (skip) from `AviationServerUnreachable`
  (abort) — the two exception types already exist in `O4_ICAO_Utils`. A dead
  server should not drive N doomed lookups.
- **D-12:** **Tile-build crash → log and continue** to the next tile. One failed
  tile does not waste the rest of an overnight run.
- **D-13:** **Exit code is binary: 0 iff every ICAO resolved AND every tile built;
  1 if anything failed.** Matches Phase 1's `1 = runtime failure` scheme; details
  live in the summary, not the exit code.
- **D-14:** Print a **per-ICAO / per-tile summary** at end of run (resolved/failed,
  built/failed).

### Tile Set Assembly (BUILD-04 + radius overlap)
- **D-15:** **Dedupe to a unique tile set** before building. All `(lat, lon)` tiles
  from every ICAO + its radius collapse into a set; each unique tile builds once
  (KJFK/KLGA/KEWR → shared NYC tiles built once). Summary may note which ICAOs
  mapped to each tile.
- **D-16:** **Always rebuild** every tile in the set, regardless of existing
  on-disk artifacts. Skip-already-built stays v2-deferred (needs a trusted
  staleness predicate first, per REQUIREMENTS).
- **D-17:** Build the deduped set in **deterministic order, sorted by (lat, lon)**,
  for reproducible runs and predictable log output.

### Claude's Discretion
- Exact end-of-run summary format/columns (D-14) and per-tile progress wording.
- Whether the radius/neighbor generator, the ICAO-list/file parser, and the batch
  orchestrator live in `O4_CLI_Utils.py` or small new helper module(s) following
  the `O4_*` naming convention.
- Resolve-then-build sequencing (e.g. resolve each ICAO lazily vs. resolve the
  whole list first) — as long as D-10/D-11/D-15 semantics hold. Note: D-11's
  server-unreachable abort is easiest if resolution failures are detected as they
  occur.
- Error-message wording (must stay specific enough to distinguish the two
  resolver failure modes, per Phase 2 D-04).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase planning
- `.planning/ROADMAP.md` §"Phase 3: ICAO-Driven Build" — goal + 4 success criteria
- `.planning/REQUIREMENTS.md` — BUILD-02..05, plus Out-of-Scope lines (radius in
  whole tiles not km; skip-already-built deferred to v2; `--dry-run`/`--json` v1.x)
- `.planning/phases/02-report-icao-resolution/02-CONTEXT.md` — resolver decisions
  (D-01..D-04) and the D-11 3×3 `coverage_tiles` behavior this phase generalizes
- `.planning/phases/01-cli-dispatch-compatibility/01-CONTEXT.md` — CLI dispatch,
  `run_build`, `run_and_report`, floor-parse decisions this phase extends

### Codebase (paths + reusable code)
- `src/O4_CLI_Utils.py` — argparse tree (`build_parser`), `run_build`,
  `run_and_report`, `parse_lat`/`parse_lon`, `dispatch`; extend the `build`
  subparser and dispatch here
- `src/O4_ICAO_Utils.py` — `resolve_icao(ident, base_url, timeout)`,
  `get_server_url()`, exception types `AviationServerUnreachable` / `ICAONotFound`
  (drives D-10/D-11)
- `src/O4_Report_Utils.py` §`coverage_tiles` — the existing 3×3 Chebyshev
  neighbor generator (radius 1, skips off-grid) that D-06/D-09 generalize; leave unchanged
- `src/O4_File_Names.py` — FNAMES path authority (`short_latlon`, `tile_dir`,
  `dsf_file`, etc.); never hardcode paths
- `.planning/codebase/INTEGRATIONS.md` — external-service pattern (all `requests`)

### ICAO resolver service
- `../mcp_aviation_server/README.md` / `CLAUDE.md` — transport modes + resource
  surface (already integrated in Phase 2; referenced only if resolver behavior needs review)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `O4_CLI_Utils.run_build(lat, lon, provider, zl)` — the single-tile build call;
  the batch orchestrator loops it over the deduped tile set (D-15/D-17).
- `O4_CLI_Utils.parse_lat` / `parse_lon` — floor + range-check each generated
  neighbor tile (D-08 pole skip = catch their `ValueError`).
- `O4_ICAO_Utils.resolve_icao` + `get_server_url` — resolve each ICAO to lat/lon;
  its two exception types are the D-10 (skip) vs D-11 (abort) branch.
- `O4_CLI_Utils.run_and_report` — traceback/non-zero-exit wrapper; the batch path
  needs its own summary+exit logic (D-13/D-14) rather than the fail-first wrapper
  used for single commands.
- `O4_Report_Utils.coverage_tiles` — reference implementation of Chebyshev
  neighbor iteration to generalize into a radius-N generator (do not import; the
  build generator wraps the antimeridian where this one skips).

### Established Patterns
- Two-letter uppercase module aliases; any new helper follows `O4_*` naming and
  is imported by alias.
- `O4_Config_Utils` (CFG) must remain imported **last** — `run_build` already
  imports build modules lazily inside the function to preserve this; the batch
  orchestrator must not import CFG/build modules at module top either.
- Single-tile resolver failures print one stderr line + `sys.exit(1)` (Phase 2
  D-04). Batch mode changes this to accumulate-and-summarize (D-10/D-13/D-14),
  except server-unreachable which still aborts (D-11).

### Integration Points
- New flags hang off the `build` subparser in `O4_CLI_Utils.build_parser()`;
  new dispatch branch in `O4_CLI_Utils.dispatch()`.
- Aviation-server URL read via `O4_ICAO_Utils.get_server_url()` (config var from
  Phase 2), reused unchanged.
- Tile builds write through FNAMES paths via the existing `run_build` pipeline.

</code_context>

<specifics>
## Specific Ideas

- Command shapes the user has in mind:
  `build --icao KJFK`, `build --icao KJFK,KLGA,KEWR --radius 1`,
  `build --icao-file airports.txt`.
- List-file format: one ICAO per line, blank lines and `#` comments ignored.
- Overlapping ICAOs (KJFK/KLGA/KEWR) must build shared tiles once, not 3×.
- A dead aviation server must fail fast (abort), not grind through the whole list.

</specifics>

<deferred>
## Deferred Ideas

- Skip-already-built / resume — v2-deferred (needs a trusted staleness predicate).
- `--dry-run` (resolve ICAOs → print the tile list without building) — v1.x-deferred.
- `--json` machine-readable output on build/report — v1.x-deferred.
- Distinct exit codes per failure type — considered and rejected for v1 (D-13
  keeps a binary 0/1); revisit if scripts need to branch on failure kind.
- Unifying the build radius generator with report `coverage_tiles()` antimeridian
  behavior — deferred (D-09); would touch both build and report call sites.
- Radius in km / nautical miles — out of scope per REQUIREMENTS (whole tiles only).

None outside milestone scope surfaced during discussion.

</deferred>

---

*Phase: 3-ICAO-Driven Build*
*Context gathered: 2026-08-25*
