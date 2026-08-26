# Phase 3: ICAO-Driven Build - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 3-ICAO-Driven Build
**Areas discussed:** Command surface, Radius & antimeridian, Batch failure policy, Tile dedup & already-built

---

## Command Surface

| Option | Description | Selected |
|--------|-------------|----------|
| --icao on `build` | Extend existing `build` subcommand, mutually exclusive with positional lat/lon | ✓ |
| New `build-icao` subcommand | Separate subcommand, two build entry points | |

| Option | Description | Selected |
|--------|-------------|----------|
| --icao comma-list + --icao-file | `--icao KJFK,KLGA,KEWR` inline; `--icao-file PATH` list file | ✓ |
| --icao repeatable + positional file | argparse append + positional path | |

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse --provider/--zl for all tiles | Same flags, applied uniformly, config fallback | ✓ |
| ICAO builds ignore provider/zl | Always config/global defaults | |

| Option | Description | Selected |
|--------|-------------|----------|
| Exactly one source | positional / --icao / --icao-file mutually exclusive (usage error if two) | ✓ |
| --icao + --icao-file combine | Union of both then dedupe | |

| Option | Description | Selected |
|--------|-------------|----------|
| --radius works for all build forms | Tile-expansion flag independent of center source | |
| --radius only with --icao/--icao-file | Radius is ICAO-only; usage error with positional | ✓ |

**User's choice:** `--icao`/`--icao-file` on the existing `build` subcommand; comma-list + list file; reuse `--provider`/`--zl`; exactly one input source; `--radius` restricted to ICAO forms.
**Notes:** Keeps a single build entry point and single shared `run_build`; positional lat/lon stays a manual single-tile path with no radius.

---

## Radius & Antimeridian

| Option | Description | Selected |
|--------|-------------|----------|
| Wrap longitude | 179 → −180 (mod 360); builds real dateline neighbors | ✓ |
| Skip off-grid, match coverage_tiles | Drop neighbors outside [−180,179] | |

| Option | Description | Selected |
|--------|-------------|----------|
| Clamp/skip above 89 or below −90 | Latitude does not wrap; skip past poles | ✓ |
| Same skip as today | Identical to coverage_tiles range check | |

| Option | Description | Selected |
|--------|-------------|----------|
| Chebyshev square | (2N+1)² block, radius 0 = containing tile | ✓ |
| Something else | Diamond/Manhattan or other | |

**User's choice:** Chebyshev square; longitude wraps at antimeridian; latitude skips past poles.
**Notes:** Build path gets a new radius generator with wrap; Phase 2 `coverage_tiles()` skip behavior is left unchanged (documented report-side v1.x decision).

---

## Batch Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Continue, summarize at end (resolve fail) | Skip bad ICAO, per-ICAO summary, exit 1 if any failed | ✓ |
| Fail-fast | First resolve failure aborts | |
| Resolve all up front, then build | All-or-nothing before any build | |

| Option | Description | Selected |
|--------|-------------|----------|
| Continue, summarize at end (build fail) | Log failure, next tile, summary, exit non-zero if any failed | ✓ |
| Fail-fast | First tile-build crash stops the batch | |

| Option | Description | Selected |
|--------|-------------|----------|
| 0 all-ok, 1 any-failure | Binary exit code, details in summary | ✓ |
| Distinct codes per failure type | Granular per-failure exit codes | |

| Option | Description | Selected |
|--------|-------------|----------|
| Abort on server-unreachable | Unknown ICAO skips; server-down aborts whole batch | ✓ |
| Treat both the same — skip and continue | Uniform skip-and-summarize | |

**User's choice:** Unknown ICAO skips + continues; server-unreachable aborts immediately; tile-build crash logs + continues; binary exit code 0/1; end-of-run summary.
**Notes:** Distinguishes the two existing resolver exception types (`ICAONotFound` vs `AviationServerUnreachable`) to avoid grinding through a dead server.

---

## Tile Dedup & Already-Built

| Option | Description | Selected |
|--------|-------------|----------|
| Dedupe to a unique tile set | Build each tile once across all ICAOs + radii | ✓ |
| Build per-ICAO, allow repeats | Shared tile built multiple times | |

| Option | Description | Selected |
|--------|-------------|----------|
| Always rebuild | Build every tile regardless of existing artifacts | ✓ |
| Skip already-built tiles | Reuse D-05 predicate to skip complete tiles | |

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic sort by (lat, lon) | Reproducible order + predictable logs | ✓ |
| Input order (first-seen) | Preserve user ordering across dedup | |

**User's choice:** Dedupe to unique tile set; always rebuild; deterministic (lat, lon) sort.
**Notes:** Skip-already-built explicitly kept as v2-deferred per REQUIREMENTS (needs a trusted staleness predicate first).

---

## Claude's Discretion

- End-of-run summary format/columns and per-tile progress wording.
- Module organization for the radius generator, list/file parser, and batch orchestrator (in `O4_CLI_Utils.py` vs new `O4_*` helper module).
- Resolve-then-build sequencing, as long as skip/abort/dedupe semantics hold.
- Resolver failure-message wording (must distinguish the two failure modes).

## Deferred Ideas

- Skip-already-built / resume — v2.
- `--dry-run` and `--json` — v1.x.
- Distinct exit codes per failure type — rejected for v1.
- Unifying build radius generator with report `coverage_tiles()` antimeridian behavior.
- Radius in km / nautical miles — out of scope (whole tiles only).
