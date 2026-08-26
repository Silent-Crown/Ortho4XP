---
quick_id: 260826-dbo
slug: report-tiles-zoom-level-detail-breakdown
date: 2026-08-26
---

# Quick Task 260826-dbo: report tiles zoom-level detail breakdown

`report tiles` only showed each tile's base `default_zl` from its cfg, hiding
the custom higher-detail zones a tile actually contains (e.g. +35-080 mixes
ZL16 with large ZL17/18/19 zones). Add a `--zoom` flag that scans `textures/`
and reports count + size per zoom level under each tile.

Ground truth is the DDS files themselves: FNAMES names them
`{y}_{x}_{provider}{zl}.dds`, so the zoom level is the trailing 2 digits.

## Tasks

1. `zoom_breakdown(build_dir)` in O4_Report_Utils — scan `textures/`, bucket
   `.dds` by ZL, return sorted `(zl, count, bytes)`; skip non-tile files.
2. `report_tiles(store, show_zoom=False)` — when `show_zoom`, print indented
   per-ZL lines under each tile row.
3. `report tiles --zoom` flag in O4_CLI_Utils; dispatch passes `args.zoom`.
   Composes with `--build-dir`.
4. Self-checks: ZL parser (incl. digit-suffixed provider code) + arg parsing.
</content>
