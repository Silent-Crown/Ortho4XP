---
quick_id: 260826-cu5
slug: add-a-build-dir-arg-to-the-cli
date: 2026-08-26
status: complete
commit: 7576f75
---

# Quick Task 260826-cu5: add a --build-dir arg to the CLI — Summary

## What changed

`build` now accepts `--build-dir DIR`. `run_build`/`run_batch_build` take a
`build_dir` (default `""`) and pass it to `CFG.Tile(lat, lon, build_dir)`
instead of the hardcoded `''`. Empty keeps the default `./Tiles` store; a
trailing `/` or `\` nests tiles under a base folder; otherwise it's the literal
per-tile dir. Batch builds force base-folder semantics so tiles don't collide.

Legacy `lat lon [provider zl]` path is unchanged (still uses the default store).

Report side (`report tiles`/`coverage`/`health`) also accepts `--build-dir` to
point at a non-default store. A `store` root threads through
`iter_tiles`/`tile_status` and the three report entry points; empty = ./Tiles.

## Files

- `src/O4_CLI_Utils.py` — build_dir on run_build/run_batch_build + `--build-dir`
  on the `build` subparser; `--build-dir` on all three `report` subparsers;
  dispatch wiring; batch base-folder guard; self-check asserts.
- `src/O4_Report_Utils.py` — `store` param on report_tiles/report_coverage/
  report_health/iter_tiles/tile_status; `_store_root` normalizer.

## Verification

Both self-checks pass (`O4_CLI_Utils self-check OK`, `O4_Report_Utils self-check
OK`). Functional: `report_tiles`/`report_health` against a temp store dir
correctly list tiles from that store instead of ./Tiles.

## Usage

```
python Ortho4XP.py build 47 -122 --build-dir D:/xp_tiles/
python Ortho4XP.py build --icao KJFK,KLGA --build-dir D:/xp_tiles/
python Ortho4XP.py report tiles --build-dir D:/xp_tiles/
python Ortho4XP.py report coverage --icao KJFK --build-dir D:/xp_tiles/
python Ortho4XP.py report health --build-dir D:/xp_tiles/
```
</content>
