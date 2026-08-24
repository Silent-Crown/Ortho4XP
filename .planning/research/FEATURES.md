# Feature Research

**Domain:** Batch geospatial/scenery build CLI + asset-inventory reporting (X-Plane orthophoto scenery)
**Researched:** 2026-08-24
**Confidence:** MEDIUM

Ortho4XP has no direct CLI-automation competitor — the GUI's "Batch Build Tiles" dialog is
the only precedent inside the tool itself. So this research triangulates from three
neighboring domains that all define what "table stakes" looks like for this feature set:
(1) the X-Plane scenery ecosystem itself (Ortho4XP GUI batch mode, xOrganizer's coverage
scanner, AutoOrtho), (2) general geospatial tile-build CLIs (gdal2tiles.py, tippecanoe),
and (3) mature infrastructure-as-code CLIs that popularized dry-run/resume/plan-report
patterns (terraform, ansible, rsync, kubectl). Confidence is MEDIUM: the X-Plane-specific
precedents are thin (one GUI dialog, one third-party inventory tool) so most of the
feature judgment leans on the general-CLI pattern, which is well-established but not
scenery-specific.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Build a single tile by lat/lon | Already exists (`Ortho4XP.py lat lon [provider zl]`) — the floor every other feature builds on | LOW | Preserve verbatim per PROJECT.md compatibility constraint |
| Build around an ICAO (containing tile) | The whole point of ICAO-based automation — "build me this airport" is the #1 ask in the Ortho4XP/AutoOrtho community | MEDIUM | Needs ICAO→lat/lon resolution (`mcp_aviation_server`); containing tile = floor(lat), floor(lon) |
| Configurable radius around the ICAO tile | Airports straddle tile edges; GUI users already do this manually by multi-selecting adjacent tiles in the tile map | LOW-MEDIUM | Radius in whole tiles (N/S/E/W square or Chebyshev distance), not km — matches Ortho4XP's 1°×1° tiling |
| Batch build from multiple ICAOs (args) | GUI's "Batch Build Tiles" already supports multi-select; CLI users expect `--icao KJFK,KLGA,KEWR` parity | LOW | Straightforward loop over the single-ICAO path |
| Batch build from a list file | Standard for any batch CLI (rsync `--files-from`, ansible inventory files, tippecanoe `-L`) — scripting/CI users need a file, not shell argv limits | LOW | Plain text, one ICAO per line, `#` comments; reuse for scheduled/unattended runs |
| `--help` / discoverable subcommands | argparse migration is explicitly in scope; every CLI tool has this | LOW | Table stakes of the argparse migration itself, not a report feature |
| Tile inventory listing (what's built) | Every asset-management CLI has a "list what exists" command (`docker images`, `terraform state list`) — GUI already shows this visually via tile map colors | LOW-MEDIUM | Walk `Tiles/zOrtho4XP_*` via FNAMES; provider/zoom/date/size come from the per-tile `.cfg` + filesystem stat |
| Coverage-by-ICAO check ("is this airport built?") | Direct ask in PROJECT.md; mirrors xOrganizer's "Scenery Coverage" feature in the same ecosystem | MEDIUM | Requires the same ICAO→lat/lon resolution as the build command — natural reuse |
| Exit codes / machine-parseable failure signal | Batch + scripting implies CI/unattended use; current code prints "Crash!" on any failure per PROJECT.md — that's explicitly being fixed | LOW | Non-zero exit on failure is the actual bar; JSON output is a differentiator (below) |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Health/staleness report (partial builds, missing DDS/DSF, stale tiles) | No existing tool in this ecosystem does this — xOrganizer shows coverage, not build integrity. Solves the real pain of "I ran a batch build overnight, did it actually finish everything?" | MEDIUM-HIGH | Needs a definition of "complete" per tile (DSF present + expected DDS count present + no `.mesh`/`.node` leftovers signaling a crashed run) |
| Disk overlap / redundant coverage report | Genuinely novel — nothing in the researched ecosystem detects wasted disk from overlapping provider/zoom builds of the same tile | MEDIUM | Overlap here is really "same tile rebuilt at different provider/zoom, old artifacts not cleaned" rather than geometric overlap (tiles are a fixed 1°×1° grid, so they don't geometrically overlap each other) — scope this precisely before building |
| Detail-zone surfacing (custom higher-zoom areas per tile) | Ortho4XP supports per-tile zoom overrides today but they're buried in per-tile `.cfg` files with no aggregate view — reporting them is pure visibility, not new capability | LOW | Read-only report over existing config; genuinely low-hanging differentiator since the data already exists |
| Dry-run mode (`--dry-run` / `--plan`) | Standard in terraform/ansible/kubectl for anything that mutates state; here it would resolve ICAOs → tile list and print what *would* build without downloading/computing | LOW-MEDIUM | High leverage for batch builds — catches ICAO typos and radius miscalculation before a multi-hour run |
| Resume / skip-already-built | Standard in rsync/terraform (idempotent re-apply) and directly useful given multi-hour builds; batch build should skip tiles that already pass the health check instead of re-downloading | MEDIUM | Depends on the health/staleness definition above — build resume ON TOP of health check, don't invent a second "is it done" concept |
| Machine-readable report output (`--json`) | Turns the terrain report from a human dashboard into something CI/scripts can consume (matches `terraform show -json`, `kubectl get -o json`) | LOW | Cheap once report data model exists; do human-readable table first, JSON is additive |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Radius in kilometers/nautical miles | Feels more "aviation native" than tile counts | Ortho4XP's world model is 1°×1° tiles, not a continuous coordinate radius — a km radius has to be converted to tile counts anyway and the conversion is latitude-dependent (a degree of longitude shrinks toward the poles), inviting off-by-one confusion | Radius in whole tiles (N/S/E/W), document that 1 tile ≈ 111km N-S, less E-W at altitude |
| True geometric overlap detection between tiles | "Disk overlap" reads like it wants polygon intersection | Ortho4XP tiles are a fixed non-overlapping 1°×1° grid — two tiles literally cannot geometrically overlap. Building this would be solving a problem that doesn't exist in this data model | Reinterpret "overlap" as redundant/stale artifacts within a single tile (old provider's DDS/imagery not cleaned after a rebuild at a new provider/zoom) — this is what PROJECT.md's "wasting space" framing actually points at |
| Bundling a full ICAO/airport database in Ortho4XP | Convenient, no external dependency | Duplicates `mcp_aviation_server`'s data, creates a second source of truth to keep in sync, bloats the repo — explicitly called Out of Scope in PROJECT.md | Call `mcp_aviation_server`; degrade with a clear error (optionally a small local fallback) if unreachable, per PROJECT.md constraint |
| Auto-fix on staleness detection (report command silently rebuilds) | Convenient — "just fix it for me" | Reporting and mutating are different trust levels; a report command that silently triggers multi-hour rebuilds violates the principle of least surprise and breaks dry-run/CI use of the report | Report is read-only; staleness findings feed a *separate*, explicit rebuild/resume invocation |
| Real-time/live progress dashboard for batch report | Sounds impressive | High complexity (web server, polling, state sync) for a feature whose actual job is "answer a question once, exit" — batch builds already have `O4_UI_Utils` console progress | Static report output (table or JSON) run on demand; leave live progress to the existing build-time console output |

## Feature Dependencies

```
ICAO→lat/lon resolution (mcp_aviation_server client)
    └──requires──> nothing new (external service call)

Build around ICAO (containing tile)
    └──requires──> ICAO→lat/lon resolution

Build around ICAO + radius
    └──requires──> Build around ICAO (containing tile)

Batch ICAO build (args or list file)
    └──requires──> Build around ICAO + radius

Coverage-by-ICAO report
    └──requires──> ICAO→lat/lon resolution
    └──requires──> Tile inventory listing

Health/staleness report
    └──requires──> Tile inventory listing
    └──enhances──> Resume (batch build skip-already-built)

Disk overlap (redundant-artifact) report
    └──requires──> Tile inventory listing (per-tile provider/zoom/artifact enumeration)

Detail-zone report
    └──requires──> Tile inventory listing (reads per-tile .cfg)

Resume / skip-already-built
    └──requires──> Health/staleness report (reuses its "is this tile complete" definition)

Dry-run
    └──enhances──> Batch ICAO build (preview before committing)
    └──conflicts──> nothing (pure read path, safe to add anytime)

JSON report output
    └──enhances──> all report commands (additive, same data model)
```

### Dependency Notes

- **Batch ICAO build requires Build-around-ICAO-with-radius:** batch is just "do the
  single-ICAO-plus-radius resolution N times" — build the single case first, batch falls
  out almost for free (loop + list-file parsing).
- **Coverage-by-ICAO and Health/staleness both require Tile inventory listing:** the
  inventory (walk `Tiles/` via FNAMES, read per-tile `.cfg`, stat files) is the shared
  data layer under every report subcommand. Build it once as an internal function, not
  once per report.
- **Resume requires Health/staleness's completeness definition:** don't invent two
  different notions of "is this tile done" — a batch build's skip-logic and the
  standalone health report should call the same predicate.
- **Disk overlap conflicts with "geometric overlap":** flagged explicitly in
  Anti-Features — this dependency chain assumes overlap means *stale artifacts within a
  tile*, not *tiles intersecting each other*, because the latter can't happen in
  Ortho4XP's fixed grid.
- **Dry-run has no real dependency:** it's a pure preview over the ICAO-resolution +
  tile-list-construction path, so it can be added to the batch command at any point
  without touching the report commands.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] argparse migration preserving existing no-arg/GUI and `lat lon [provider zl]` behavior
- [ ] Build around an ICAO (containing tile + `--radius`)
- [ ] Batch ICAO build (args + list file)
- [ ] Tile inventory report (provider, zoom, build date, size) — the shared data layer
- [ ] Coverage-by-ICAO report — cheapest high-value report, reuses ICAO resolution
- [ ] Health/staleness report (partial builds, missing DDS/DSF, stale tiles)

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Detail-zone report — trigger: once inventory report's data model is proven, this is
  a thin read over existing per-tile `.cfg`, low risk to add
- [ ] Disk overlap (redundant-artifact) report — trigger: once "staleness" definition is
  validated by real usage, since overlap detection reuses the same artifact-enumeration
- [ ] Dry-run mode on batch build — trigger: once batch build is used enough that users
  hit ICAO typos or radius miscalculations in real unattended runs
- [ ] `--json` output on report commands — trigger: first time someone wants to pipe a
  report into another script/CI check

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Resume / skip-already-built for batch builds — defer until health/staleness
  predicate has been used and trusted; resume built on an unproven completeness check
  is worse than no resume
- [ ] Auto-cleanup of stale/redundant artifacts (as a distinct, explicit mutating command
  separate from the read-only overlap report)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Build around ICAO + radius | HIGH | MEDIUM | P1 |
| Batch ICAO build (args/list file) | HIGH | LOW | P1 |
| Tile inventory report | HIGH | LOW-MEDIUM | P1 |
| Coverage-by-ICAO report | HIGH | MEDIUM | P1 |
| Health/staleness report | HIGH | MEDIUM-HIGH | P1 |
| Detail-zone report | MEDIUM | LOW | P2 |
| Disk overlap (redundant-artifact) report | MEDIUM | MEDIUM | P2 |
| Dry-run mode | MEDIUM | LOW-MEDIUM | P2 |
| JSON report output | LOW-MEDIUM | LOW | P2 |
| Resume / skip-already-built | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

No direct CLI competitor exists for Ortho4XP; comparisons drawn from adjacent tools.

| Feature | Ortho4XP GUI (existing) | xOrganizer v3 (3rd-party X-Plane tool) | Terraform/Ansible/rsync (general CLI pattern) | Our Approach |
|---------|--------------------------|------------------------------------------|------------------------------------------------|--------------|
| Batch selection | Multi-select checkboxes in "Batch Build Tiles" dialog | N/A (inventory-only tool) | List files / glob patterns / inventory files | `--icao` (comma-list) + `--icao-file` |
| Area-around-a-point | Manual: user clicks adjacent tiles on the map | N/A | N/A (not geospatial) | `--radius` around ICAO's containing tile |
| Coverage reporting | Visual tile-map coloring (built/not built) | Dedicated "Scenery Coverage" scan across installed scenery, flags gaps | N/A | Coverage-by-ICAO CLI report reusing the ICAO resolver |
| Dry-run | None | None (read-only tool by design) | `terraform plan`, `ansible --check`, `rsync --dry-run` — universal pattern | Add as batch-build preview flag (v1.x) |
| Resume | None (re-run redoes everything) | N/A | `rsync` (checksums), `terraform apply` (state-aware), idempotent by design | Deferred to v2+, built on staleness predicate |
| Health/staleness | None | None found | N/A (not this domain) | Novel differentiator for this ecosystem — partial build / missing artifact detection |

## Sources

- [shred86/Ortho4XP fork](https://github.com/shred86/Ortho4XP) — this repo's own current fork lineage; MEDIUM confidence (primary repo, not independently verified beyond browsing)
- [OrthoForge (codeberg.org/xbard/OrthoForge)](https://codeberg.org/xbard/OrthoForge) — community fork context; LOW confidence (surfaced via search snippet only, not read in full)
- [Flusiboard: Scenery Creation with Ortho4XP](https://www.flusiboard.com/lexicon/entry/52-scenery-creation-with-ortho4xp/) — describes GUI batch-build dialog behavior; MEDIUM confidence (community wiki, consistent with known GUI behavior)
- [X-PlaneReviews: xOrganizer v3 review](https://xplanereviews.com/forums/topic/16895-utility-review-xorganizer-v3-xp12/) — direct precedent for "Scenery Coverage" reporting in this ecosystem; MEDIUM confidence (third-party review site, not vendor docs)
- [HeliSimmer: Using scenery on X-Plane 10/11 using half the disk space](https://www.helisimmer.com/tutorials/using-scenery-x-plane-10-11-using-half-disk-space) — background on X-Plane scenery disk-usage patterns and zoom-level scaling; MEDIUM confidence
- General CLI pattern knowledge (terraform plan/apply, ansible --check, rsync --dry-run, kubectl apply --dry-run, docker images) — HIGH confidence, well-established public tooling conventions, not project-specific but broadly applicable to the dry-run/resume/report design questions raised here
- `.planning/PROJECT.md` and `.planning/codebase/STRUCTURE.md` (this repo) — HIGH confidence, ground truth for what already exists (GUI batch build, FNAMES path authority, per-tile `.cfg`)

---
*Feature research for: Ortho4XP CLI automation (batch scenery build + terrain reporting)*
*Researched: 2026-08-24*
