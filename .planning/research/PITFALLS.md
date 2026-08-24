# Pitfalls Research

**Domain:** CLI migration (argparse) + geospatial tile radius math + external MCP integration + cross-platform artifact scanning, for Ortho4XP's headless build/report commands
**Researched:** 2026-08-24
**Confidence:** MEDIUM-HIGH (argparse/geodesy patterns are well-established; MCP-coupling and artifact-scan findings are grounded directly in this codebase, not external sources)

## Critical Pitfalls

### Pitfall 1: `int()` truncation instead of `floor()` breaks negative-coordinate tiles

**What goes wrong:**
Ortho4XP's whole tile-naming system (`O4_File_Names.short_latlon`, `round_latlon`, `tile_dir`, `build_dir`) is built on `floor()` semantics: a tile's lat/lon is the **integer SW corner**, e.g. tile `-34` covers `-34.0` to `-33.0`. The current entry point does `lat = int(sys.argv[1])`. `int()` truncates toward zero, not toward negative infinity. `int(-33.9)` → `-33` (wrong tile — off by one, points at the tile to the north). This is a live bug today, but it's latent because users normally type the SW-corner integer directly, not a raw float. ICAO→lat/lon resolution changes that: `mcp_aviation_server` will hand back precise decimal coordinates (e.g. `-33.9461`), and naive `int()`/`round()` truncation of those will silently pick the wrong tile for any airport in the southern hemisphere or west of the prime meridian — a large fraction of all ICAO codes (South America, Africa, Australia, most of the Americas).

**Why it happens:**
`int()` "looks" like the right conversion and works correctly for the common positive-coordinate demo case (Europe/most of Asia), so it goes unnoticed until someone builds an airport in Brazil, Chile, Argentina, South Africa, or the Americas.

**How to avoid:**
Use `math.floor(lat)`, `math.floor(lon)` (already imported in `O4_File_Names.py`) everywhere raw decimal coordinates are converted to a tile index — in ICAO resolution, in radius/neighbor-tile computation, and ideally as a fix to the existing positional path too (in-scope as a bugfix, or flagged explicitly as pre-existing and out of scope if minimizing diff).

**Warning signs:**
Any `int(lat)` / `int(lon)` / `round(lat)` in new CLI code; test cases that only use positive-hemisphere ICAO codes (e.g. EDDF, EGLL) will never catch this.

**Phase to address:**
ICAO resolution / radius-build phase — add explicit unit test with a southern/western-hemisphere ICAO (e.g. SBGR São Paulo, or FACT Cape Town).

---

### Pitfall 2: Radius-in-degrees vs radius-in-tiles vs radius-in-nautical-miles conflated

**What goes wrong:**
"Tiles within a radius" is ambiguous in three different ways that get silently merged into one wrong implementation:
1. A degree of longitude is not a fixed distance — it shrinks by `cos(latitude)` as you move toward the poles. A "50 nm radius" near the equator spans roughly the same longitude-degree width as a much larger nm radius near 60° latitude.
2. Tiles are 1°×1° squares, not circles — a true "radius" search needs to test tile-corner distance against the radius, not just add/subtract a fixed degree offset per tile, or it will both include tiles it shouldn't (near-corner tiles just outside a true circle) and exclude tiles it should (near-edge tiles just inside).
3. If the config's `--radius` flag is intended in nautical miles (aviation-natural unit, matches how pilots/ICAO users think) but implemented as raw integer tile count, users get wildly different coverage depending on latitude for the "same" radius value.

**Why it happens:**
The simplest implementation (`for dlat in range(-r, r+1): for dlon in range(-r, r+1): ...`) is a square, not a circle, and is latitude-naive — it's the fastest thing to write and looks correct until tested away from the equator or against a circular-radius expectation.

**How to avoid:**
Pick one explicit definition and document it: **recommend tile-count radius** (`--radius N` = N tiles in each direction, a square/Chebyshev neighborhood), which is simple, predictable, matches how Ortho4XP already thinks in whole-degree tiles, and needs no latitude correction. If a real-world-distance radius (nm) is required instead, convert nm → degrees-of-latitude directly (`dlat = nm / 60`, since 1° latitude ≈ 60 nm everywhere) but convert nm → degrees-of-longitude using `dlon = nm / (60 * cos(radians(lat)))`, and clamp/document behavior above ~85° latitude where `cos(lat)` approaches 0 and `dlon` blows up. Do not silently swap between these representations in the same code path.

**Warning signs:**
A `--radius` value tested only at one latitude; no test at high latitude (Alaska, Scandinavia, southern Chile) where the degree/nm distortion is largest.

**Phase to address:**
ICAO radius-build phase — pick tile-count (Chebyshev) radius as the MVP definition per the ladder (rung 1: does nm-accurate distance need to exist yet? No — tile-count is what the codebase already understands and is trivial to reason about). Document the choice in `--help` text so users aren't surprised.

---

### Pitfall 3: Antimeridian and pole wraparound silently produce wrong or duplicate tiles

**What goes wrong:**
An airport near ±180° longitude (e.g. Fiji, Kiribati, the Aleutians) with a radius search will compute neighbor tiles like `lon+1 = 181`, which is not a valid tile — X-Plane/Ortho4XP tile longitudes run `-180..179`. Naive code either crashes on an out-of-range provider/config lookup, silently builds a nonsensical tile `181`, or (worse) produces two different string representations of the same physical tile (`-180` and `180`) that both get "built" as if distinct, wasting disk and confusing the report commands. Similarly a radius search near a pole (rare for ICAO airports, but not impossible — northern Canada/Svalbard/Antarctic strips exist) can request `lat > 89` or `lat < -90`, outside valid tile space.
X-Plane/Ortho4XP tiles are always whole-number degree squares, so poles are naturally somewhat self-limiting (no tile can straddle latitude 90), but the wraparound normalization at longitude ±180 is a real, easy-to-miss edge case.

**Why it happens:**
Longitude arithmetic (`lon + dlon`) is naively linear; nobody hits this case in initial testing because almost no popular test airports sit near the dateline.

**How to avoid:**
Normalize computed longitudes with `((lon + 180) % 360) - 180` after adding the radius offset, and clamp latitude to `[-90, 89]` (a tile can't start at 90). Add one antimeridian test case (e.g. an ICAO near Fiji/Kiribati, longitude ~+179 to -179) to the radius-build tests.

**Warning signs:**
No test coordinate above ±170° longitude anywhere in the test/verification plan.

**Phase to address:**
ICAO radius-build phase — include an antimeridian test fixture explicitly in the phase's verification criteria.

---

### Pitfall 4: argparse migration silently breaks the two contractually-frozen invocations

**What goes wrong:**
PROJECT.md constraints require `Ortho4XP.py` (no args → GUI) and `Ortho4XP.py lat lon [provider zl]` (positional headless build) to keep working byte-for-byte. The most common way this breaks with argparse:
- Adding subcommands (`Ortho4XP.py build --icao KJFK`) via `add_subparsers()` typically makes the subcommand **required**, so `Ortho4XP.py` with zero args either errors ("required: command") or prints argparse's own usage/help instead of launching the GUI — argparse intercepts before your own "no args → GUI" branch ever runs.
- argparse's positional-vs-optional parsing does not accept `lat lon` as bare positionals once subcommands exist unless they're wired as a legacy top-level positional group, and argparse does not support "either exactly 2 positionals OR exactly 4 positionals OR a subcommand" out of the box — that dispatch has to happen *before* argparse parses, or via a custom pattern.
- `int lat lon` today (see Pitfall 1) accepts things like `"33"` but also things Ortho4XP never validated (e.g. `"+33"`, `"033"`); if the argparse version adds `type=int` validation that's stricter/looser than the old bare `int()` cast, some previously-"working" invocations from user scripts could now be rejected (or vice versa).
- Global `-h`/`--help` is auto-added by argparse and will now intercept any script that (accidentally or not) was passing `-h` positionally before — unlikely here, but worth a sanity check since old code had zero flag parsing.

**Why it happens:**
argparse's subcommand model is fundamentally "pick a mode via a required token," which doesn't map cleanly onto "positional args with no keyword IS a valid mode."

**How to avoid:**
Branch on `sys.argv` shape *before* invoking argparse, exactly as today (`len(sys.argv) == 1` → GUI, `len(sys.argv) in (3, 5)` and `sys.argv[1]` looks numeric → legacy positional path, calling the exact same code as before), and only hand off to `argparse.ArgumentParser` for everything else (subcommands like `build --icao`, `report`, etc.). This is the standard "hybrid dispatch" pattern (detect legacy args, fall through to argparse otherwise) — do not try to force the legacy 2/4-positional form into argparse subparsers, since argparse subcommands and floating positionals don't compose. Write one smoke test per frozen invocation shape (no args; `lat lon`; `lat lon provider zl`) that asserts the same code path/behavior as before the migration, run manually since there's no test suite.

**Warning signs:**
Any PR that replaces the `len(sys.argv)` branching with `subparsers.add_parser(...)` for the *whole* CLI, or that makes `dest="command"` required at the top level without a bare fallback.

**Phase to address:**
CLI/argparse migration phase — the compatibility check itself should be the phase's primary verification gate (run the exact old commands, diff output/behavior against pre-migration).

---

### Pitfall 5: Coupling the CLI directly to `mcp_aviation_server` makes it fail (or hang) offline

**What goes wrong:**
`mcp_aviation_server` is a separate Dockerized service (SQLite/Postgres/MySQL backend). If the CLI's ICAO resolution imports and calls into it synchronously with no timeout, and the service is down/unreachable/not running locally, the build command either hangs indefinitely (default socket timeouts can be very long or absent), or throws a raw connection-refused traceback that means nothing to a user running a batch build script overnight. PROJECT.md already flags "degrade gracefully... when it is unreachable" as a constraint — the common way projects get this wrong is treating the external dependency as always-available in the happy path and only handling failure as an afterthought, or catching the failure with another bare `except:` (the exact anti-pattern this milestone is meant to fix — see CONCERNS.md's 173 bare-except count and the explicit goal to "surface real errors").

**Why it happens:**
MCP/service clients are usually built and tested with the service running locally, so the offline/unreachable path never gets exercised until a real user hits it in the field — and Ortho4XP's own codebase culture (per CONVENTIONS.md) currently normalizes bare `except:` around anything that can fail, so the path of least resistance is to reuse that same pattern here.

**How to avoid:**
Set an explicit, short connect/read timeout on the MCP/DB client call for ICAO lookups. Catch the *specific* failure modes (connection refused, timeout, malformed/empty response) and translate each into one clear, actionable CLI error message (e.g. "ICAO lookup service unavailable at <endpoint> — check mcp_aviation_server is running, or pass --lat/--lon directly"). Per PROJECT.md's own "optional local fallback" language, keep the raw `--lat lon` positional/flag path as the escape hatch that never depends on the external service — that's the graceful-degradation story, not a second data source to bundle. Do not let the report commands (which don't need ICAO resolution at all — they only read `FNAMES`/on-disk state) import or depend on the aviation-server client at import time; keep that import lazy/scoped to the ICAO-resolving subcommand so a report run works with zero network dependency.

**Warning signs:**
Any `import` of the aviation-server client at module top-level in a file that also implements report/`--help`; no `timeout=` on the client call; a bare `except:` wrapping the ICAO lookup.

**Phase to address:**
ICAO resolution phase for the timeout/error-message work; keep it isolated so the terrain-report phase (no external dependency) can ship and be tested independently of `mcp_aviation_server`'s availability.

---

### Pitfall 6: Report commands hardcode `zOrtho4XP_` glob patterns instead of going through FNAMES, or use OS-specific path scanning

**What goes wrong:**
There is currently no existing tile-scanning/inventory code in the codebase — the report feature is entirely new. The two most common mistakes when writing it: (1) hand-rolling the tile-directory name pattern (`zOrtho4XP_+33+007` style) instead of round-tripping through `O4_File_Names` helpers (`short_latlon`, `tile_dir`, `build_dir`), which PROJECT.md explicitly calls out as the single source of truth — any drift between a hardcoded glob and a future change to the naming scheme silently breaks the report; (2) using `os.walk`/`glob` patterns or path-separator assumptions (`"/"` joins, case-sensitive matching) that behave differently across Windows/macOS/Linux — Windows paths are case-insensitive on the filesystem but Python string comparisons are not, so a report that string-matches directory names built with `os.path.join` on one platform can miscompare on another; also Windows `MAX_PATH` and the vendored `Utils/{win,mac,lin}` binaries mean deep tile trees are more likely to hit path-length issues on Windows specifically.

**Why it happens:**
It's faster to write `glob.glob("Tiles/zOrtho4XP_*")` directly than to look up whether FNAMES exposes an enumeration helper, especially since no such helper exists yet and has to be added.

**How to avoid:**
Add one FNAMES-level helper (e.g. `iter_built_tiles()`) that encapsulates the directory pattern and returns parsed `(lat, lon)` pairs, so report commands consume structured data, not raw path strings — matches the existing convention (all path construction routes through FNAMES). Use `pathlib.Path.glob`/`rglob` (already cross-platform) rather than manual string concatenation; parse the tile name back into `(lat, lon)` using the same format string logic as `short_latlon` (or its inverse) instead of ad hoc regex, so any future naming change only has to update one place.

**Warning signs:**
`glob.glob` or raw string patterns appearing in a new `O4_Report_Utils.py`-style module instead of calls into `O4_File_Names`; any `\\` or `/` literal in new path-joining code.

**Phase to address:**
Terrain-report phase — verification should include running the report on a Windows-built tile tree path (or at minimum reviewing that all new path code uses `pathlib`/`os.path.join`, never string concatenation).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse bare `except:` pattern for new CLI error paths (matches existing 173 occurrences) | Fast, consistent with rest of codebase | Directly contradicts this milestone's own stated goal ("surface real errors"); masks ICAO/network failures users need to see | Never for new code in this milestone |
| Square (Chebyshev) tile radius instead of true circular/nm radius | Trivial to implement, no latitude math, matches tile-integer mental model | Over-builds tiles near corners vs. a "true" radius search if a user expects distance semantics | Acceptable as the documented MVP definition — see Pitfall 2 |
| `int()` truncation left as-is in the legacy positional path (not touched by this milestone) | Zero risk to the frozen-compatibility contract | Pre-existing bug stays alive for the one invocation shape that isn't going through the new ICAO path | Acceptable only if explicitly noted as pre-existing/out-of-scope; NOT acceptable to copy the same bug into new ICAO-resolution code |
| Eagerly import `mcp_aviation_server` client at CLI startup for all subcommands | Simpler import graph | Report/`--help` commands now silently depend on network availability | Never — keep the import scoped to ICAO-resolving code paths only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| `mcp_aviation_server` (ICAO→coords) | Synchronous call with no timeout; bare `except:` swallowing connection errors | Explicit short timeout + specific exception handling → clear CLI error message; keep it optional/lazy-imported |
| `argparse` subcommands + legacy positionals | Wiring the whole CLI through `add_subparsers()`, making a subcommand token required and breaking no-arg GUI launch | Branch on raw `sys.argv` shape first for the two frozen legacy invocations; hand off to argparse only for new subcommands |
| `O4_File_Names` (FNAMES) as path authority | New report code hardcodes `zOrtho4XP_*` glob patterns instead of calling FNAMES helpers | Add a FNAMES-level tile-enumeration helper; report code never constructs tile paths itself |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Radius search that scans the entire `Tiles/` directory tree per report call instead of computing the bounded lat/lon range up front | Report command gets slower as more tiles accumulate on disk | Compute the candidate `(lat, lon)` set mathematically first (from ICAO/radius), then check existence per-tile via FNAMES, rather than walking the whole tree for every query | Noticeable once a user has built more than a few hundred tiles |
| Batch ICAO build issuing one network round-trip per ICAO to `mcp_aviation_server` sequentially | Slow batch builds when list file has dozens/hundreds of ICAOs | Prefer a single batch lookup call if the server supports it; otherwise this is fine at expected list sizes (tens, not thousands) — don't over-engineer concurrency for a feature with no evidence of that scale | Only worth revisiting if list files routinely exceed ~100 ICAOs |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Passing a batch ICAO list-file path straight into `open()` with no validation, or accepting shell-like input | Path traversal / accidental read of arbitrary files if the CLI is ever wrapped by another script passing untrusted input | Standard `argparse` `type=argparse.FileType`/path validation; not a high-severity concern for a local dev tool, but worth a basic existence/extension check before opening |
| Logging the full ICAO lookup response (which may include operator/registration-adjacent data depending on the aviation DB) verbosely by default | Minor privacy/PII leak into `Ortho4XP.log` at high verbosity | Keep ICAO lookup response logging behind the existing verbosity levels (2/3), not level 1 default |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| New argparse `--help` output that doesn't mention the legacy positional form still works | Users following old docs/scripts think the tool has been fully rewritten and their scripts will break | Document both forms explicitly in `--help` epilog: "Legacy: Ortho4XP.py lat lon [provider zl]" |
| Radius build silently produces 0 extra tiles near dateline/high latitude with no warning | User assumes coverage was built, finds gaps later | When a requested radius tile is out of valid tile-space (post antimeridian/pole normalization) or already built, print an explicit one-line note per skipped/deduped tile, not silent success |
| Report command reports "healthy" for a tile that's mid-build (partial DDS/DSF present because a previous run crashed) | User trusts a report that says the tile is fine when it's actually broken | Define "health" checks explicitly against the known DSF/DDS-per-tile file set from FNAMES, not just directory existence |

## "Looks Done But Isn't" Checklist

- [ ] **argparse migration:** Looks done when `--help` works — verify the two frozen legacy invocations (`Ortho4XP.py` no-args, `Ortho4XP.py lat lon [provider zl]`) still produce identical behavior, not just "doesn't crash"
- [ ] **ICAO radius build:** Looks done when it works for a European/US airport — verify against a southern-hemisphere ICAO (negative lat) and a near-dateline ICAO (longitude near ±180)
- [ ] **ICAO→coords resolution:** Looks done when the happy path (server up) works — verify the server-down/unreachable path produces a clear error, not a hang or traceback
- [ ] **Terrain report:** Looks done when it lists tiles found in `Tiles/` on the dev machine — verify it goes through FNAMES helpers, not hardcoded path strings, and works on a path with mixed-case or long nested directories (Windows)
- [ ] **Batch ICAO build:** Looks done when a 2-3 ICAO list works — verify behavior when one ICAO in the list fails to resolve (does the whole batch abort, or skip-and-continue with a clear per-ICAO report?)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| `int()`/truncation tile-index bug found after ICAO builds already ran | LOW | Fix the conversion to `floor()`; affected builds are just at the wrong tile coordinate — re-run the build for the corrected tile, delete the mis-named one |
| argparse migration broke a legacy invocation shape post-release | MEDIUM | No test suite means this surfaces via user report; revert to `len(sys.argv)`-based dispatch for that shape, add the regression as a permanent manual smoke-test step |
| MCP coupling caused hangs in the field (no timeout set) | LOW | Add timeout in a follow-up patch; no data corruption risk, just a bad UX until fixed |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| `int()` truncation on negative coords | ICAO resolution / radius-build phase | Unit test with a southern/western-hemisphere ICAO (e.g. SBGR, FACT) |
| Degree vs nm vs tile-count radius ambiguity | ICAO radius-build phase | `--help` documents the chosen unit explicitly; test at high latitude |
| Antimeridian/pole wraparound | ICAO radius-build phase | Test fixture near ±180° longitude (e.g. Fiji/Kiribati ICAO) |
| argparse breaking frozen legacy invocations | CLI/argparse migration phase | Manual smoke test of both legacy invocation shapes before/after, diffed |
| MCP coupling without timeout/graceful degradation | ICAO resolution phase | Simulate server-down (stop the Docker container) and confirm a clear error, not a hang |
| Hardcoded glob patterns bypassing FNAMES | Terrain-report phase | Code review: no raw `zOrtho4XP_*` string pattern outside `O4_File_Names.py` |

## Sources

- Codebase inspection: `Ortho4XP.py` (entry point, lines 1-84), `src/O4_File_Names.py` (tile naming/`floor()` convention, lines 1-90), `src/O4_Airport_Utils.py` (ICAO tag parsing), `.planning/codebase/CONCERNS.md`, `.planning/codebase/CONVENTIONS.md` — HIGH confidence, direct code read
- [Using both argparse and sys.argv in the same script for backwards compatibility — Slowbro Blog](https://blog.slowb.ro/using-both-argparse-and-sys-argv-in-the-same-script/) — MEDIUM confidence, single blog source but pattern matches standard practice
- [Migrating optparse code to argparse — Python docs](https://docs.python.org/3/howto/argparse-optparse.html) — HIGH confidence, official Python documentation
- General geodesy: degree-to-distance conversion (`1° latitude ≈ 60 nm`, `1° longitude ≈ 60·cos(lat) nm`), antimeridian bbox wraparound (`minX > maxX` convention), pole-region longitude blowup — MEDIUM confidence, general GIS knowledge cross-checked via web search (Jason Davies bounding-box tooling, MIT 6.005 Bounds problem set, bbox-buffer-helper documentation)

---
*Pitfalls research for: Ortho4XP CLI automation (argparse migration, ICAO radius geodesy, MCP coupling, cross-platform artifact scanning)*
*Researched: 2026-08-24*
