# Testing Patterns

**Analysis Date:** 2026-08-24

## Test Framework

**Current Status:** Not detected

- No pytest configuration found
- No unittest framework detected
- No testing directory (`tests/`, `test/`, etc.)
- No test runner commands in project

**Assertion Library:** Not applicable — no automated testing infrastructure present

**Run Commands:** Not defined

## Test File Organization

**Location:** Not applicable — no test files exist

**File pattern:** None; no test files found in repository

**Naming convention:** None established

## Test Structure

**Current approach:** Manual testing only

The project appears to rely on manual testing during development. No automated test suites are present.

## Manual Testing Approach

**Verbosity-based debugging:** The codebase uses a verbosity system for debugging and information output during manual runs:

```python
# From O4_UI_Utils.py
verbosity = 1  # Module-level verbosity setting
red_flag = False  # Global interrupt flag

def vprint(min_verbosity, *args):
    """Print if verbosity >= min_verbosity"""
    if verbosity >= min_verbosity:
        print(*args)

def lvprint(min_verbosity, *args):
    """Print and log if verbosity >= min_verbosity"""
    if verbosity >= min_verbosity:
        print(*args)
    if log:
        logprint(*args)
```

**Verbosity levels for manual testing:**
- Level 0: Critical errors only
- Level 1: Normal operations (default)
- Level 2: Debug information (useful for testing)
- Level 3: Full debug output (useful for deep debugging)

**Configuration override:** Manual testing typically adjusts `verbosity` in `Ortho4XP.cfg` or via GUI before running a tile build.

## Mocking

**Framework:** Not used

**Approach:** Not applicable — no automated tests to mock dependencies

## Fixtures and Test Data

**Test data:** Not organized; no dedicated fixtures

**Manual test workflow:**
1. Edit `Ortho4XP.cfg` with test parameters
2. Run `Ortho4XP.py <lat> <lon> [provider zoomlevel]` from command line
3. Observe console output and log file (`Ortho4XP.log`)
4. Verify output files in tile directory (e.g., `Tiles/zOrtho4XP_+45-005/`)

## Coverage

**Requirements:** None enforced

**Measurement:** Not performed

**Logging for verification:** When debugging failures, check `Ortho4XP.log` file for timestamped events

## Fragile Areas Requiring Manual Testing

**Module downloads and network handling** (`O4_Imagery_Utils.py`):
- Network timeout behavior
- Retry logic for failed connections
- Response validation from tile servers
- Relevant config: `http_timeout`, `max_connect_retries`, `max_baddata_retries`, `check_tms_response`

**Elevation data handling** (`O4_DEM_Utils.py`):
- DEM file parsing from multiple sources
- No-data value handling and interpolation
- File: `fill_nodata_values_with_nearest_neighbor()` function needs testing

**Parallel processing** (`O4_Parallel_Utils.py`):
- Worker thread spawning and shutdown
- Queue-based task distribution
- Global interrupt flag (`red_flag`) behavior

**Vector and OSM data** (`O4_Vector_Utils.py`, `O4_OSM_Utils.py`):
- OSM Overpass server selection and fallback
- Vector data parsing from OpenStreetMap
- Server configuration: `overpass_servers.txt`

## Anti-Patterns to Watch During Manual Testing

**1. Bare except blocks throughout codebase:**
Location: `Ortho4XP.py`, `O4_Imagery_Utils.py`, `O4_Config_Utils.py` and others
- Masks actual errors
- Makes debugging harder
- Test by intentionally causing errors in dependencies and observing silent failures

**2. Dynamic variable assignment using exec():**
Location: `O4_Config_Utils.py` lines 74, 102, 157, 220, 229, 235
- Configuration loading uses `exec()` to dynamically set module variables
- Test by creating invalid config files and verifying graceful fallback

**3. Global mutable state:**
Locations: `O4_UI_Utils.py` (verbosity, red_flag, is_working, gui, log)
- Functions depend on global state set elsewhere
- Test by verifying state isolation between consecutive tile builds

## Key Functions Requiring Verification

**Configuration loading** (`O4_Config_Utils.py`):
- `set_global_variables(var, value)`: Lines 52-74
- `config_compatibility(value)`: Lines 76-88
- `Tile.read_from_config()`: Lines 181-249
- Test: Create config files with edge cases (missing keys, invalid values, malformed lines)

**Parallel execution** (`O4_Parallel_Utils.py`):
- `parallel_execute()`: Lines 37-49
- `parallel_worker.run()`: Lines 13-34
- Test: With nbr_workers = 1, 4, 8; verify success flag and red_flag behavior

**Network requests** (`O4_Imagery_Utils.py`):
- Retry logic with `http_timeout` and `max_connect_retries`
- Test: Simulate network timeouts, server errors (HTTP 500), partial responses

**DEM file handling** (`O4_DEM_Utils.py`):
- `DEM.__init__()`: Lines 38-71
- `DEM.load_data()`: Lines 73-172
- Test: With missing files, corrupted geotiff, no-data-only regions

## Command-Line Testing

**Normal build:**
```bash
python Ortho4XP.py 45 -5 bing 16
```

**With debugging (requires manual verbosity adjustment in .cfg):**
```bash
python Ortho4XP.py 45 -5
# Then check Ortho4XP.log for detailed output
```

**GUI mode (manual interactive testing):**
```bash
python Ortho4XP.py
# Opens tkinter GUI for manual tile configuration and building
```

## Recommended Testing Additions

**Immediate priorities for automation:**
1. Configuration file parsing — high risk of silent failures
2. Parallel worker behavior — threading issues are hard to debug
3. Network error handling — critical for reliability

**Low-hanging fruit:**
- Unit tests for utility functions: `short_latlon()`, `build_dir()`, `hem_latlon()` in `O4_File_Names.py`
- Integration tests for configuration loading chain

---

*Testing analysis: 2026-08-24*
