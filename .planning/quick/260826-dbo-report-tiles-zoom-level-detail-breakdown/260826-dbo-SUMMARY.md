---
quick_id: 260826-dbo
slug: report-tiles-zoom-level-detail-breakdown
date: 2026-08-26
status: complete
commit: 50fd78a
---

# Quick Task 260826-dbo: report tiles zoom-level detail breakdown — Summary

## What changed

`report tiles --zoom` now expands each tile with a per-zoom-level breakdown
(texture count + size), so custom higher-detail zones (ZL17/18/19) are visible
instead of just the base `default_zl` from the cfg. Default output is unchanged
(flag is opt-in). Works against a custom store via `--build-dir` too.

Zoom level is read from the DDS filenames themselves (`{y}_{x}_{provider}{zl}.dds`,
trailing 2 digits = ZL), which is the on-disk ground truth — a provider code
ending in a digit (e.g. GO2) still parses correctly.

## Files

- `src/O4_Report_Utils.py` — `zoom_breakdown(build_dir)` scanner + `_TEX_RE`;
  `report_tiles` gains `show_zoom` param and prints indented per-ZL lines.
- `src/O4_CLI_Utils.py` — `--zoom` flag on `report tiles`; dispatch wiring;
  arg-parse self-checks.

## Verification

Both module self-checks pass. Functional run against the real `C:\Ortho` store
matched a manual texture count for +35-080 (ZL16:195, ZL17:69, ZL18:59, ZL19:71).

## Usage

```
python Ortho4XP.py report tiles --zoom
python Ortho4XP.py report tiles --zoom --build-dir C:/Ortho/
```

Sample:
```
+35-080   BI         16    2026-08-21 10:57         4.3G
    ZL16     195 tex      2.0G
    ZL17      69 tex    736.0M
    ZL18      59 tex    629.3M
    ZL19      71 tex    757.3M
```

## Note

Branched off the cu5 (`--build-dir`) tip rather than origin/master — both edit
`report_tiles`, and `--zoom` composes with `--build-dir`. Merge/rebase together.
</content>
