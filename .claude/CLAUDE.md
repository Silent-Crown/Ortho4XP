<!-- GSD:project-start source:PROJECT.md -->

## Project

**Ortho4XP — Command-Line Automation**

Ortho4XP is a scenery generation tool for X-Plane that builds terrain mesh and
orthophoto textures for 1°×1° tiles. This milestone extends its thin headless mode into
a real command-line interface: build tiles around ICAO airport codes, report on
already-built terrain, and grow more automation commands over time — for users who script
scenery generation instead of driving the Tkinter GUI.

**Core Value:** A scriptable Ortho4XP: given an ICAO code (or a list), build the right tiles unattended —
without opening the GUI.

### Constraints

- **Compatibility**: Existing headless invocations (`Ortho4XP.py lat lon [provider zl]`)
  and no-arg GUI launch must keep working — scripts and docs depend on them.

- **Tech stack**: Python 3.13, stdlib `argparse` (no new CLI framework); reuse existing
  `O4_` modules rather than reimplementing build logic.

- **Dependencies**: ICAO lookup goes through `mcp_aviation_server`; degrade gracefully
  (clear error, optional local fallback) when it is unreachable.

- **Platform**: Runs on Windows/macOS/Linux — path handling via FNAMES, not OS-specific code.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.13.5 - CPython implementation, configured in `venv/pyvenv.cfg`

## Runtime

- CPython 3.13.5 (Windows x86_64)
- Virtual environment managed by `uv` (0.9.25)
- `uv` (0.9.25) - Manages dependencies and virtual environment
- Lockfile: Not detected (uses `requirements.txt` directly)

## Frameworks

- tkinter (stdlib) - GUI framework for Ortho4XP_GUI, defined in `src/O4_GUI_Utils.py`
- Pillow 12.2.0 - Image manipulation and DDS conversion support
- PyInstaller - Bundling application into standalone executable, configured in `Ortho4XP.spec`

## Key Dependencies

- numpy 2.4.4 - Numerical computations for mesh and imagery processing
- shapely 2.1.2 - Geometric operations for roads, water, and vector data (used in `src/O4_Vector_Utils.py`, `src/O4_Vector_Map.py`, `src/O4_OSM_Utils.py`)
- pyproj 3.7.2 - Coordinate system transformations and projection handling (used in `src/O4_Geo_Utils.py`, `src/O4_Geotag.py`)
- requests 2.33.1 - HTTP client for downloading imagery and OSM data
- Pillow 12.2.0 - Image processing, JPEG/PNG conversion, DDS texture generation
- Rtree 1.4.1 - Spatial indexing for geometric queries
- scikit-fmm 2025.6.23 - Fast Marching Method for mesh smoothing
- gdal (platform-dependent: 3.12.3 on macOS, 3.12.2 on Windows, 3.9.0 on Linux) - Geospatial raster data access

## Configuration

- Config files stored as plain text `.cfg` format in `Ortho4XP.cfg` (global) and per-tile `.cfg` files
- Config variables defined in `src/O4_Cfg_Vars.py`
- Environment variables for projection data: `PROJ_DATA`, `DYLD_LIBRARY_PATH` set at startup in `Ortho4XP.py`
- `Ortho4XP.spec` - PyInstaller configuration for creating standalone executable
- `requirements.txt` - Python dependencies with pinned versions
- `venv/pyvenv.cfg` - Virtual environment configuration

## Platform Requirements

- Python 3.13.5
- uv package manager
- PROJ library (version 5+) with `proj.db` for coordinate transformations
- GDAL library for geospatial data access
- Windows/macOS/Linux capable of running Python
- PROJ coordinate database (`proj.db`)
- Embedded utilities directory containing:
- Windows, macOS (Intel and Apple Silicon), Linux
- Standalone executable via PyInstaller bundling

## External Binaries

- `DFSTool` (version 24-5) - X-Plane DSF file format tool, used in `src/O4_Tile_Utils.py`
- `Triangle4XP.exe` (Windows/Mac/Linux variants) - Mesh generation, C++ executable
- `nvcompress` (platform-specific) or `DDSTool` (macOS) - DDS texture compression

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Pattern: `O4_<Module>_<Category>.py` (e.g., `O4_Imagery_Utils.py`, `O4_Config_Utils.py`)
- Convention: Prefix all source files in `src/` with `O4_` to indicate Ortho4XP module
- Location: All core modules live in `src/` directory
- Convention: snake_case (e.g., `short_latlon()`, `build_dir()`, `initialize_extents_dict()`)
- Utility functions grouped by domain in single module
- Factory/initialization functions prefixed with `initialize_` or `build_` (e.g., `initialize_extents_dict()`)
- Module-level constants: UPPER_CASE_WITH_UNDERSCORES (e.g., `global_prefix`, `Preview_dir`, `http_timeout`)
- Local/parameter variables: snake_case
- Configuration dictionaries: lowercase descriptive names (e.g., `cfg_vars`, `providers_dict`, `extents_dict`)
- Convention: CamelCase (e.g., `Tile`, `DEM`, `parallel_worker`)
- Base class inheritance from threading.Thread or custom abstractions
- Instance variables prefixed with underscore when private (e.g., `_task`, `_queue`, `_progress`)
- All module imports use two-letter uppercase aliases: `import O4_Imagery_Utils as IMG`, `import O4_Vector_Map as VMAP`
- Aliases used throughout the codebase: IMG, VMAP, MESH, MASK, TILE, GUI, CFG, OSM, DEM, FNAMES, UI, VECT, OVL
- File: `Ortho4XP.py` (main entry point) imports and aliases all major modules at top level

## Code Style

- No formal code formatter is configured (no .pylintrc, .flake8, or pyproject.toml found)
- Line length: Varies; some long lines observed (80-100+ characters)
- Indentation: 4 spaces (standard Python convention)
- Spacing: No strict conventions enforced
- Not detected: No linting configuration found
- No CI/CD workflows for automated linting
- Manual code review expected
- Section separators: `################################################################################` (80+ # characters)
- Inline comments: Sparse; mostly found in complex algorithms
- Comment convention: Uppercase letter after `#` (e.g., `# Required for pyinstaller`)

## Import Organization

- None detected; absolute imports from `src/` directory
- `sys.path.append()` used to add `src/` directory to path at runtime (in `Ortho4XP.py`)
- Provider directory added via `sys.path.append(FNAMES.Provider_dir)`

## Error Handling

- Bare `except:` blocks used throughout (anti-pattern but observed in `Ortho4XP.py`, `O4_Imagery_Utils.py`, `O4_Config_Utils.py`)
- Specific exception catching in newer code: `except FileNotFoundError:`, `except Exception as e:`
- Error messages printed via `UI.vprint()` and `UI.lvprint()` before raising exceptions
- Exceptions raised as bare `raise Exception` without message qualification

## Logging

- `vprint(min_verbosity, *args)`: Print to console if verbosity >= min_verbosity
- `lvprint(min_verbosity, *args)`: Print to console AND log file if verbosity >= min_verbosity
- `logprint(*args)`: Append to `Ortho4XP.log` with timestamp
- 0: Critical errors only
- 1: Normal output (default)
- 2: Debug information (for user with more detail)
- 3: Full debug output
- Example from `O4_Config_Utils.py`:

## Docstrings

- One-line summary followed by blank line (when extended)
- `:param type name:` for parameters
- `:returns:` for return value
- `:return type:` for type information
- Used in functions and class methods; less common in private functions

## Configuration

- `O4_Cfg_Vars.py`: Defines all configuration variables as Python dictionaries
- `Ortho4XP.cfg`: Global configuration file (key=value format, # for comments)
- Per-tile config: `zOrtho4XP_<latlon>.cfg` in tile build directory

## Function Design

- Typically 2-4 parameters
- Class methods may have progress callbacks and mutable state lists as parameters (anti-pattern but observed)
- Type hints in docstrings, not in function signatures (Python 3.5 style)
- Functions often return tuples of related values (e.g., `(lat, lon, strlatround, strlonround)`)
- Success/status functions return integers (1 for success, 0 for failure) in config reading
- Void functions return nothing (common for initialization and side-effect functions)

## Module Design

- Modules export constants, functions, and classes directly
- No explicit `__all__` lists detected
- Global module-level state: configuration variables, dictionaries, mutable lists
- Module-level dictionaries: `providers_dict`, `combined_providers_dict`, `extents_dict`, `color_filters_dict`
- Module-level mutable state: `verbosity`, `red_flag`, `is_working`, `cleaning_level`, `gui`, `log`
- State modified by configuration loading in `O4_Config_Utils.py`

## Threading and Concurrency

- `parallel_worker`: Custom Thread subclass consuming queue tasks
- `parallel_execute()`: Launch workers, wait for completion, return success status
- `parallel_launch()`: Launch workers without blocking
- `parallel_join()`: Wait for workers to complete

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Entry Point** | Initialize sys.path, load providers/configs, route to GUI or CLI | `Ortho4XP.py` |
| **GUI Framework** | Tkinter window, tile map, config tabs, batch controls | `src/O4_GUI_Utils.py` |
| **Configuration System** | Load/save tile and global configs, manage Tile class state | `src/O4_Config_Utils.py`, `src/O4_Cfg_Vars.py` |
| **Vector Map Stage** | Fetch OSM data, include roads/airports/coastlines, produce `.poly` file | `src/O4_Vector_Map.py` |
| **Mesh Stage** | Triangulate using Triangle4XP binary, generate mesh from `.poly` + elevation | `src/O4_Mesh_Utils.py` |
| **Mask Stage** | Build water/coastline masks from vector data | `src/O4_Mask_Utils.py` |
| **Tile/DSF Stage** | Download imagery, convert to DDS, assemble `.dsf` file with textures | `src/O4_Tile_Utils.py` |
| **Imagery Download** | Fetch tiles from providers, manage concurrency, format conversion | `src/O4_Imagery_Utils.py` |
| **Elevation Data** | Load DEM sources (SRTM, ALOS, NED, Viewfinder), cache locally | `src/O4_DEM_Utils.py` |
| **OSM/Vector Queries** | Query Overpass API, parse XML, construct vector features | `src/O4_OSM_Utils.py`, `src/O4_Vector_Utils.py` |
| **DSF Encoding** | Serialize terrain mesh and metadata into X-Plane `.dsf` format | `src/O4_DSF_Utils.py` |
| **File Path Management** | Centralized source of truth for all directory and file naming | `src/O4_File_Names.py` |
| **Parallelization** | Thread pool executor for concurrent downloads/conversions | `src/O4_Parallel_Utils.py` |

## Pattern Overview

- **Flat module structure**: All application code in `src/` as individual `O4_*.py` modules (no package nesting)
- **Import-order dependency**: `O4_Config_Utils` (CFG) imported last because it mutates module-level variables in other modules at initialization time
- **Provider-based extensibility**: Imagery sources defined in `.lay` files under `Providers/` directory; code discovers and loads them at startup
- **Two-tier configuration**: Global defaults (`Ortho4XP.cfg`) + per-tile overrides in tile directories; per-tile config auto-loads when tile is selected
- **Multi-stage build pipeline**: Each tile build sequentially calls `build_poly_file` → `build_mesh` → `build_masks` → `build_tile`
- **Thread-based concurrency**: Separate worker threads for imagery download, DDS conversion, and mesh building; coordinated via queues

## Layers

- Purpose: Load data, initialize UI or headless pipeline
- Location: `Ortho4XP.py`
- Contains: `sys.path` setup, provider/extent/filter initialization, branch to GUI or CLI
- Depends on: All modules via imports (loads in specific order)
- Used by: Everything else
- Purpose: Declare settings, load/save configs, represent tile metadata
- Location: `src/O4_Cfg_Vars.py`, `src/O4_Config_Utils.py`
- Contains: Setting declarations, Tile class, config file I/O
- Depends on: File paths (`O4_File_Names`), UI for logging
- Used by: GUI, headless CLI, all build stages
- Purpose: Render Tkinter windows, capture user input, display progress
- Location: `src/O4_GUI_Utils.py`
- Contains: Main window, tile collection/map, config tabs, batch build dialog
- Depends on: Config system, build pipeline modules
- Used by: User (not called by other code)
- Purpose: Fetch imagery and elevation from external sources
- Location: `src/O4_Imagery_Utils.py`, `src/O4_DEM_Utils.py`, `src/O4_OSM_Utils.py`
- Contains: Provider management, HTTP requests, format parsing
- Depends on: File system, HTTP (requests library), native tools (gdal_translate, gdalwarp)
- Used by: Build pipeline stages
- Purpose: Geometry, file paths, vector math, parallel execution
- Location: `src/O4_Vector_Utils.py`, `src/O4_File_Names.py`, `src/O4_Geo_Utils.py`, `src/O4_Parallel_Utils.py`, `src/O4_UI_Utils.py`
- Contains: Shapely/geometry operations, path construction, coordinate transforms, thread pools
- Used by: All modules

## Data Flow

### Primary Build Flow (Single Tile)

### Batch Build Flow

### Config Loading & Inheritance

```

```

## Key Abstractions

- Represents a single 1°×1° tile and its build state
- Instance variables: lat, lon, build_dir, dem (cache), all config vars (road_level, default_zl, etc.)
- Methods: `read_from_config()`, `write_to_config()`, `make_dirs()`
- Scope: One instance per tile being built; passed between pipeline stages
- Represents terrain geometry as edges and nodes
- Contains: `dico_edges` (dict of line segments), nodes, coastlines, roads
- Used by: Vector map builder, mesh triangulator, mask builder
- Each provider is a dict entry: `providers_dict[code] = {name, url_template, max_threads, imagery_dir, ...}`
- Loaded from `.lay` files in `Providers/` subdirectories at startup
- Supports combined providers (multi-layer imagery blends)
- Single source of truth for all directory paths and file naming conventions
- Functions return full paths for imagery, DEMs, OSM data, masks, tiles, etc.
- Used instead of hardcoding paths throughout codebase

## Entry Points

- Location: `Ortho4XP.py:51` (`Ortho4XP = GUI.Ortho4XP_GUI()`)
- Triggers: Running `python Ortho4XP.py` with no arguments
- Responsibilities: Render map, capture tile selection, route build requests to pipeline
- Location: `Ortho4XP.py:78-82` (try block calling VMAP/MESH/MASK/TILE)
- Triggers: Running `python Ortho4XP.py <lat> <lon> [provider] [zl]`
- Responsibilities: Load config, execute full 4-stage pipeline, exit
- Location: `O4_Tile_Utils.build_tile_list()` (called from GUI)
- Triggers: User clicks batch build button with tile selection
- Responsibilities: Loop over tiles, apply stage flags, report errors

## Architectural Constraints

- **Import Order**: `O4_Config_Utils` must be imported last; it mutates module-level variables via `exec()` at init time.
- **Single-threaded UI**: Tkinter is not thread-safe. GUI updates via `UI.vprint()` use a thread-safe queue; worker threads queue messages, main thread flushes queue periodically.
- **Global State**: Modules use module-level variables (e.g., `IMG.providers_dict`, `OSM.overpass_servers`) to hold initialized state; mutation via config loading can surprise callers if done mid-pipeline.
- **Flat Module Structure**: No package nesting means all modules are imported at module level (not class level), so circular imports are possible if not careful.
- **Native Binary Dependencies**: Triangle4XP, nvcompress/DDSTool, DFSTool, moulinette are platform-specific; version mismatches can cause silent failures or malformed output.
- **Thread Pool Size**: Download/convert worker counts are global settings; changing at runtime does not affect threads already spawned.

## Anti-Patterns

### Module-Level State Mutation

### Bare Exception Handlers

### Hardcoded Retry Logic

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
