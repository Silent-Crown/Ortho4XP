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

## Files

- `src/O4_CLI_Utils.py` — build_dir param on run_build/run_batch_build, new
  `--build-dir` arg, dispatch wiring, batch base-folder guard, self-check asserts.

## Verification

`python src/O4_CLI_Utils.py` self-check → `O4_CLI_Utils self-check OK`.

## Usage

```
python Ortho4XP.py build 47 -122 --build-dir D:/xp_tiles/
python Ortho4XP.py build --icao KJFK,KLGA --build-dir D:/xp_tiles/
```
</content>
