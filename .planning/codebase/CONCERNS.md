# Codebase Concerns

**Analysis Date:** 2026-08-24

## Tech Debt

### Bare Exception Handling (Critical)
- **Issue:** 173 bare `except:` blocks throughout codebase silently swallow all exceptions including `KeyboardInterrupt`, `SystemExit`, and `MemoryError`
- **Files:** Every module in `src/` — highest concentration in:
  - `src/O4_Imagery_Utils.py` (34 occurrences)
  - `src/O4_GUI_Utils.py` (30 occurrences)
  - `src/O4_Airport_Utils.py` (12 occurrences)
  - `src/O4_Vector_Map.py` (14 occurrences)
  - `Ortho4XP.py` (4 occurrences, including final build error at line 83)
- **Impact:** Errors are masked, making debugging difficult. Network timeouts, file I/O failures, and computational errors disappear silently. CLAUDE.md acknowledges this as a gotcha (line 89): "Headless build wraps the whole pipeline in a bare `except: print("Crash!")`, so failures are silent."
- **Fix approach:** Replace with specific exception types (`except FileNotFoundError:`, `except RequestException:`, etc.) or add logging before re-raising

### Mutable Default Arguments
- **Issue:** `def parallel_worker(..., success=[1])` at `src/O4_Parallel_Utils.py:6` uses mutable list as default argument
- **Files:** `src/O4_Parallel_Utils.py:6`
- **Impact:** Shared mutable default between worker instances can cause unexpected state persistence across parallel job runs
- **Fix approach:** Use `None` as default and initialize inside the function: `if success is None: success = [1]`

### Hardcoded Country/Region Hacks
- **Issue:** Two identical hacks for Slovenia EPSG code (102060 → 3912) hardcoded in data loading logic
- **Files:** 
  - `src/O4_Imagery_Utils.py:129` (extent initialization)
  - `src/O4_Imagery_Utils.py:282` (provider initialization)
- **Impact:** Fragile — any other regions with similar EPSG issues will silently fail. Hacks are duplicated instead of centralized in `O4_Geo_Utils.py`
- **Fix approach:** Create a mapping table in `O4_Geo_Utils.py` for known EPSG transformations, call it from both locations

### Incomplete Fetch Ratio Implementation
- **Issue:** Fetch ratio hardcoded to 1 in two DSF construction paths with TODO comments
- **Files:**
  - `src/O4_DSF_Utils.py:820` — "TODO (improve fetch values)"
  - `src/O4_DSF_Utils.py:870` — "TODO improve bathy and fetch ratio variety"
- **Impact:** Bathymetry/fetch values are not properly varied, resulting in uniform water appearance in generated scenery. Affects water realism in DSF output
- **Fix approach:** Implement proper fetch ratio calculation based on tile proximity to coast and water depth variation

### Unreachable Dead Code
- **Issue:** Dead return statement at `src/O4_DEM_Utils.py:719` bypasses entire OpenTopography SRTM fallback implementation
- **Files:** `src/O4_DEM_Utils.py:715-729`
- **Impact:** SRTM elevation data from OpenTopography can never be downloaded; users silently fall back to other sources. Previously working, now broken
- **Fix approach:** Either restore the OpenTopography functionality (auth flow, URL validation) or remove the dead code and update documentation about available elevation sources

### Config Loading with exec()
- **Issue:** Dynamic variable assignment via `exec()` at `src/O4_Config_Utils.py` (lines 74, 102, 157, 220, 229, 235)
- **Files:** `src/O4_Config_Utils.py`
- **Impact:** Executes untrusted config file content; potential security risk with malicious config files. Difficult to debug when config syntax is invalid. No validation of executed code
- **Fix approach:** Replace `exec()` with explicit `ast.literal_eval()` or attribute-based assignment for each known config key

### Tile Change Event Handling Incomplete
- **Issue:** TODO comment indicates `tile_change()` callback is incomplete and returns without implementing coordinate change detection
- **Files:** `src/O4_GUI_Utils.py:430-435`
- **Impact:** Tile configuration is not reloaded when coordinates are manually edited in the GUI text fields. Only loads when tile is selected from the collection window. Creates inconsistency between displayed state and active tile
- **Fix approach:** Implement proper coordinate change detection with debouncing to avoid double-loading from individual lat/lon field changes

---

## Known Bugs

### Memory Leak in Preview Window
- **Symptoms:** GUI becomes slow and memory usage grows over time when using the preview window repeatedly
- **Files:** `src/O4_GUI_Utils.py` (preview rendering logic)
- **Trigger:** Open preview window → close → repeat multiple times
- **Status:** Partially fixed in commit `193c133` but requires monitoring
- **Workaround:** Restart GUI after extensive preview usage

### Overpass Server Intermittent Failures
- **Symptoms:** "Part of image could not be obtained" errors during tile builds; white squares in output
- **Files:** `src/O4_OSM_Utils.py`, `overpass_servers.txt`
- **Trigger:** Random failures across builds, suggesting server-side issues or rate limiting
- **Current mitigation:** Round-robin server selection (commit `d7f1c54`), aggressive 429 backoff (commit `c41f13b`), server rotation per request
- **Known dead servers:** VK (maps.mail.ru) was pruned in latest commit

### Triangle4XP Executable Instability
- **Symptoms:** Mesh generation gets stuck on complex tiles (e.g., `+30-085`); high computational cost
- **Files:** `src/O4_Mesh_Utils.py` (shells out to `Utils/{win,mac,lin}/Triangle4XP`)
- **Trigger:** Tiles with complex coastlines or dense OSM data
- **Workaround:** Automatic fallback to lower `min_angle` value (implemented); recompile Triangle4XP with different algorithm if persistent
- **Cross-platform note:** Multiple Triangle4XP rebuilds documented in README (line 88)

### Platform-Specific GDAL Issues
- **Symptoms:** "CoreFoundation error" on macOS; version mismatches between platforms
- **Files:** `requirements.txt` (lines 8-10) specifies different GDAL versions per platform
  - Darwin: 3.12.3
  - Windows: 3.12.2
  - Linux: 3.9.0
- **Trigger:** Platform-specific geospatial operations; especially shapefile reading
- **Current mitigation:** Different `.whl` files vendored in `Utils/win` and `Utils/mac` (CLAUDE.md line 38); CI likely handles Linux
- **Risk:** Version skew can cause subtle data loading errors

### Temporary TIF File Not Cleaned Up
- **Symptoms:** Disk fills up with temporary GeoTIFF files over many builds
- **Files:** `src/O4_Tile_Utils.py` (in `convert_texture()` function)
- **Trigger:** Every tile texture conversion
- **Status:** Fixed in README (line 79) but needs verification

---

## Security Considerations

### Dynamic Config Execution via exec()
- **Risk:** Malicious `Ortho4XP.cfg` or tile config file can execute arbitrary Python code
- **Files:** `src/O4_Config_Utils.py`
- **Current mitigation:** None; config files are treated as trusted
- **Recommendations:** 
  - Replace `exec()` with safe parsing (e.g., `json.load()` or `ast.literal_eval()`)
  - Validate all config keys against a whitelist
  - Add type checking for loaded values

### HERE API Key Scraping
- **Risk:** Custom URL provider attempts to scrape API key from HERE website at runtime
- **Files:** `Providers/O4_Custom_URL.py:80`
- **Code:** `Here_value=str(requests.get('https://wego.here.com'+js_path).content).split('PLATFORM_API_KEY:"')[1][:100].split('"')[0]`
- **Impact:** Fragile and violates HERE's terms of service; website changes will break functionality
- **Recommendations:** 
  - Use HERE's official SDK or require explicit API key configuration
  - Add error handling for failed scraping
  - Document that this method violates ToS

### No Input Validation on Command-Line Arguments
- **Risk:** Integer parsing of lat/lon with bare `except:` at `Ortho4XP.py:58-61`
- **Files:** `Ortho4XP.py:58-76`
- **Impact:** Invalid input silently exits; no feedback to user
- **Recommendations:** Validate lat/lon ranges (±90, ±180) and provider codes before processing

---

## Performance Bottlenecks

### Large Monolithic Modules
- **Problem:** `O4_Imagery_Utils.py` (2,627 lines) and `O4_GUI_Utils.py` (2,340 lines) are difficult to navigate and modify
- **Files:** 
  - `src/O4_Imagery_Utils.py` (largest)
  - `src/O4_GUI_Utils.py` (second largest)
- **Cause:** Multiple concerns (providers, downloads, caching, GUI tabs) packed into single files
- **Improvement path:** Break into submodules once stabilized:
  - `O4_Imagery_*.py`: Providers, downloader, cache, converters
  - `O4_GUI_*.py`: Tile window, config tabs, preview

### Quadratic Queue Progress Calculation
- **Problem:** Progress bar calculation at `src/O4_Parallel_Utils.py:30` uses `self._queue.qsize()` every callback
- **Cause:** `qsize()` requires acquiring queue lock; called for every completed task
- **Impact:** Parallel workers with many small tasks may spend more time updating progress than working
- **Improvement path:** Track remaining items in shared counter instead of querying queue size

### Fetch Ratio Always 1
- **Problem:** Bathymetry variations use hardcoded fetch ratio of 1 in DSF output
- **Files:** `src/O4_DSF_Utils.py:823`, `src/O4_DSF_Utils.py:871`
- **Impact:** Water surface appears flat and unrealistic; no wave/texture variation
- **Improvement path:** Implement distance-to-coast calculation to vary fetch ratio

---

## Fragile Areas

### OSM Overpass Data Fetching
- **Files:** `src/O4_OSM_Utils.py`
- **Why fragile:** 
  - Depends on external Overpass API servers (4 documented, VK recently pruned)
  - Network timeouts are silently caught by bare `except:` blocks
  - No timeout configuration per request type; uses global `http_timeout`
  - Rate limiting (429 responses) recently added but may still fail under high load
- **Safe modification:**
  - Add detailed logging before/after each Overpass request
  - Implement per-server failure counters to skip consistently down servers
  - Add retry budgets per server (not global)
- **Test coverage:** Manual testing only; no unit tests for Overpass request logic

### Parallel Worker Thread Management
- **Files:** `src/O4_Parallel_Utils.py`
- **Why fragile:**
  - Mutable default argument for `success` flag can cause state leakage
  - No timeout on `worker.join()`; hung workers block entire build
  - Global `UI.red_flag` used for cancellation; not thread-safe
- **Safe modification:**
  - Replace mutable default with explicit initialization
  - Add join timeout and force thread termination if exceeded
  - Use threading.Event for cancellation instead of global flag
- **Test coverage:** No unit tests; parallel failures are hard to reproduce

### DEM File Handling and No-Data Interpolation
- **Files:** `src/O4_DEM_Utils.py`
- **Why fragile:**
  - Multiple elevation sources with different formats (GeoTIFF, HGT, etc.)
  - No-data value handling is interpolation-based; quality depends on neighboring tiles
  - SRTM fallback is dead code (line 719); relies on other sources
- **Safe modification:**
  - Add validation that DEM files load successfully before using
  - Add unit tests for edge cases: missing files, all no-data regions, out-of-bounds coords
- **Test coverage:** Manual testing only

### Config File Parsing and Merging
- **Files:** `src/O4_Config_Utils.py`
- **Why fragile:**
  - Uses `exec()` to load arbitrary Python code from config files
  - No schema validation; missing keys silently use defaults
  - Tile config files can reference undefined variables via exec
- **Safe modification:**
  - Replace `exec()` with safe parsing (JSON or TOML)
  - Add validation schema for all known config keys
  - Document required vs. optional keys
- **Test coverage:** Manual testing only; no config edge case tests

---

## Scaling Limits

### Parallel Download Thread Count
- **Current capacity:** User-configurable via `max_download_slots` (added in fork)
- **Limit:** No built-in upper bound; OS may run out of file descriptors or connection pools
- **Scaling path:** 
  - Profile thread/memory overhead per worker
  - Document recommended values for typical hardware
  - Add warning if `max_download_slots` exceeds system limits

### Mesh Triangulation Complexity
- **Current capacity:** Triangle4XP runs single-threaded; complex tiles can take hours
- **Limit:** Very dense coastlines (e.g., Norway fjords) or complex OSM data cause exponential slowdown
- **Scaling path:**
  - Pre-split problematic tiles into subtiles
  - Use Triangle4XP's parallel mode if available
  - Cache intermediate mesh files to avoid re-running

### Imagery Provider API Rate Limits
- **Current capacity:** 4 Overpass servers with round-robin; other providers have undocumented limits
- **Limit:** Batch building many tiles can trigger rate limiting; fallback chain may not have alternatives
- **Scaling path:**
  - Add per-provider rate limit tracking and backoff
  - Document each provider's limits in `Providers/*/` docs
  - Implement request queuing with exponential backoff

---

## Dependencies at Risk

### GDAL Version Fragmentation
- **Risk:** Different versions per platform (3.12.3 macOS, 3.12.2 Windows, 3.9.0 Linux)
- **Impact:** Data loading behavior may differ between platforms; shapefile parsing could be inconsistent
- **Migration plan:** 
  - Upgrade all to 3.12.3 if compatible
  - Add integration tests that load sample DEM/shapefile data on each platform
  - Document any version-dependent behavior differences

### scikit-fmm Vendored .whl Files
- **Risk:** Only Windows and macOS have prebuilt wheels in `Utils/win` and `Utils/mac`; no Linux wheels
- **Impact:** Linux users cannot pip-install; must build from source or use conda
- **Migration plan:** 
  - Verify Linux build works with `requirements.txt:7`
  - Consider switching to `uv pip` which handles prebuilt wheels better

### Pillow Deprecated Method
- **Risk:** `BICUBIC` resampling method was deprecated in Pillow 10.0.0
- **Impact:** Code updated to `Resampling.BICUBIC` (README line 80), but verify all uses are updated
- **Migration plan:** Search codebase for any remaining `Image.BICUBIC` references

---

## Missing Critical Features

### No Automated Testing
- **Problem:** No unit tests, integration tests, or E2E tests
- **Blocks:** 
  - Confident refactoring of large modules (Imagery, GUI, Config)
  - Regression detection when dependencies are updated
  - Quick feedback during development
- **Impact:** Manual testing is time-consuming and error-prone; bugs slip through into releases

### No Configuration Schema Validation
- **Problem:** Config files loaded via `exec()`; no validation that keys exist or have correct types
- **Blocks:** 
  - Safe sharing of config files between versions
  - Clear error messages when user edits config manually
  - Backwards compatibility guarantees
- **Impact:** Silent config corruption or missed settings when upgrading

### No Logging to File in Headless Mode
- **Problem:** Headless builds print to stdout but don't log to file; errors are lost
- **Blocks:**
  - Batch building multiple tiles (can't review all console output)
  - CI/CD integration (no audit trail of builds)
  - Debugging user-reported failures
- **Impact:** Users can't troubleshoot build failures; developers can't diagnose issues from log files

### No Image Download Resume/Retry Strategy
- **Problem:** Failed imagery downloads are retried once per tile but not persisted
- **Blocks:**
  - Reliable large-scale batch builds (network interruptions lose progress)
  - Resuming incomplete builds
- **Impact:** Batch builds on unstable networks fail silently; users must restart

---

## Test Coverage Gaps

### Bare except Blocks
- **What's not tested:** Error propagation; what actually fails when dependencies throw exceptions
- **Files:** Every module in `src/`
- **Risk:** Silent failures mask real errors; users see "Crash!" with no context
- **Priority:** High — errors during network/disk I/O are common in real usage

### Parallel Worker Thread Behavior
- **What's not tested:** 
  - Multiple workers with queue underflow
  - Cancellation via `red_flag` during active work
  - Mutable default argument impact across consecutive runs
- **Files:** `src/O4_Parallel_Utils.py`
- **Risk:** Threading bugs are hard to reproduce; affect download and conversion stages
- **Priority:** High — affects reliability of core pipeline

### Config File Edge Cases
- **What's not tested:**
  - Missing config file (should fall back to defaults)
  - Malformed Python in config (exec() will fail)
  - Out-of-range values (e.g., negative zoom level, lat > 90)
  - Tile-specific config overrides with invalid keys
- **Files:** `src/O4_Config_Utils.py`
- **Risk:** Silent failures or crashes during config load
- **Priority:** High — affects every tile build

### DEM Loading Edge Cases
- **What's not tested:**
  - Missing DEM files for a tile
  - DEM with all no-data values
  - Out-of-bounds coordinate queries
  - GeoTIFF parsing failures
- **Files:** `src/O4_DEM_Utils.py`
- **Risk:** Mesh builds with incorrect elevation; data corruption
- **Priority:** Medium — affects mesh quality but usually caught during visual inspection

### OSM Vector Data Parsing
- **What's not tested:**
  - Overpass server timeouts
  - Malformed GeoJSON response
  - Empty result sets (no OSM data for tile)
  - Circular ways or self-intersecting ways
- **Files:** `src/O4_OSM_Utils.py`, `src/O4_Vector_Utils.py`
- **Risk:** Silent data loss or malformed vector maps
- **Priority:** Medium — affects feature placement but rare edge case

### Imagery Download and Conversion
- **What's not tested:**
  - Network timeout during large tile download
  - Incomplete HTTP response (Content-Length mismatch)
  - DDS conversion failures for certain image formats
  - Retry exhaustion after max attempts
- **Files:** `src/O4_Imagery_Utils.py`, `src/O4_Tile_Utils.py`
- **Risk:** White squares in output or corrupted textures
- **Priority:** High — frequent cause of build failures

---

*Concerns audit: 2026-08-24*
