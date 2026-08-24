<!-- refreshed: 2026-08-24 -->
# Architecture

**Analysis Date:** 2026-08-24

## System Overview

Ortho4XP is a X-Plane scenery generation tool that builds 1°×1° terrain tiles by fetching orthophoto imagery and elevation data from external sources, triangulating a mesh from OSM vector data, and assembling the output into X-Plane's `.dsf` (DSF/Dataref Set File) format.

The system operates in two modes:
1. **GUI mode** (default): Interactive Tkinter UI for tile selection, configuration, and batch builds
2. **Headless mode** (CLI args): Command-line tile building without UI

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Entry Point                                    │
│                    `Ortho4XP.py`                                      │
│              (GUI mode or CLI/headless mode)                          │
└──────────────────┬─────────────────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
    ┌────────────┐      ┌──────────────┐
    │   GUI      │      │  Headless    │
    │ `O4_GUI_   │      │ Pipeline     │
    │ Utils.py`  │      └──┬───────────┘
    └────┬───────┘         │
         │                 │
         └────────┬────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │      Build Pipeline (4-stage sequence)      │
    ├─────────────────────────────────────────────┤
    │  1. Vector Map (`O4_Vector_Map`)            │
    │  2. Mesh (`O4_Mesh_Utils`)                  │
    │  3. Masks (`O4_Mask_Utils`)                 │
    │  4. Tile DSF/Imagery (`O4_Tile_Utils`)      │
    └──────┬──────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────┐
    │      Core Processing & I/O Layers           │
    ├─────────────────────────────────────────────┤
    │  Config: `O4_Config_Utils`, `O4_Cfg_Vars`   │
    │  Imagery: `O4_Imagery_Utils`, Providers     │
    │  Elevation: `O4_DEM_Utils`                  │
    │  Vector: `O4_Vector_Utils`, `O4_OSM_Utils`  │
    │  File I/O: `O4_File_Names`, `O4_DSF_Utils`  │
    │  Concurrency: `O4_Parallel_Utils`           │
    └──────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────┐
    │      External Data & Output                 │
    ├─────────────────────────────────────────────┤
    │  Input:  Providers/, Elevation data,        │
    │          Extents/, Filters/, Overpass API   │
    │  Output: Tiles/, Orthophotos/, OSM_data/    │
    └─────────────────────────────────────────────┘
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

**Overall:** Data pipeline with layered I/O and configuration inheritance

**Key Characteristics:**
- **Flat module structure**: All application code in `src/` as individual `O4_*.py` modules (no package nesting)
- **Import-order dependency**: `O4_Config_Utils` (CFG) imported last because it mutates module-level variables in other modules at initialization time
- **Provider-based extensibility**: Imagery sources defined in `.lay` files under `Providers/` directory; code discovers and loads them at startup
- **Two-tier configuration**: Global defaults (`Ortho4XP.cfg`) + per-tile overrides in tile directories; per-tile config auto-loads when tile is selected
- **Multi-stage build pipeline**: Each tile build sequentially calls `build_poly_file` → `build_mesh` → `build_masks` → `build_tile`
- **Thread-based concurrency**: Separate worker threads for imagery download, DDS conversion, and mesh building; coordinated via queues

## Layers

**Entry & Initialization:**
- Purpose: Load data, initialize UI or headless pipeline
- Location: `Ortho4XP.py`
- Contains: `sys.path` setup, provider/extent/filter initialization, branch to GUI or CLI
- Depends on: All modules via imports (loads in specific order)
- Used by: Everything else

**Configuration & State:**
- Purpose: Declare settings, load/save configs, represent tile metadata
- Location: `src/O4_Cfg_Vars.py`, `src/O4_Config_Utils.py`
- Contains: Setting declarations, Tile class, config file I/O
- Depends on: File paths (`O4_File_Names`), UI for logging
- Used by: GUI, headless CLI, all build stages

**User Interface:**
- Purpose: Render Tkinter windows, capture user input, display progress
- Location: `src/O4_GUI_Utils.py`
- Contains: Main window, tile collection/map, config tabs, batch build dialog
- Depends on: Config system, build pipeline modules
- Used by: User (not called by other code)

**Build Pipeline (Sequential Stages):**

1. **Vector Map** (`src/O4_Vector_Map.py`)
   - Fetches OSM data via Overpass, includes airports/roads/coastlines, produces `.poly` file
   - Depends on: OSM API, elevation data, vector utilities
   - Outputs: `.node` and `.poly` files to tile's build directory

2. **Mesh** (`src/O4_Mesh_Utils.py`)
   - Runs `Triangle4XP` binary to triangulate `.poly` into mesh
   - Depends on: Native Triangle4XP binary, DEM for elevation, vector data
   - Outputs: `.mesh` file

3. **Masks** (`src/O4_Mask_Utils.py`)
   - Builds water and coastline transition masks
   - Depends on: Mesh, vector data
   - Outputs: `.png` mask files

4. **Tile/DSF** (`src/O4_Tile_Utils.py`)
   - Downloads orthophoto tiles, converts to DDS, assembles final `.dsf` file
   - Depends on: Imagery provider system, DDS converter, DSF encoder
   - Outputs: `.dsf` file (X-Plane scenery), texture `.dds` files

**Data Acquisition:**
- Purpose: Fetch imagery and elevation from external sources
- Location: `src/O4_Imagery_Utils.py`, `src/O4_DEM_Utils.py`, `src/O4_OSM_Utils.py`
- Contains: Provider management, HTTP requests, format parsing
- Depends on: File system, HTTP (requests library), native tools (gdal_translate, gdalwarp)
- Used by: Build pipeline stages

**Utilities & Helpers:**
- Purpose: Geometry, file paths, vector math, parallel execution
- Location: `src/O4_Vector_Utils.py`, `src/O4_File_Names.py`, `src/O4_Geo_Utils.py`, `src/O4_Parallel_Utils.py`, `src/O4_UI_Utils.py`
- Contains: Shapely/geometry operations, path construction, coordinate transforms, thread pools
- Used by: All modules

## Data Flow

### Primary Build Flow (Single Tile)

1. **Entry** (`Ortho4XP.py`)
   - Parse CLI args or launch GUI
   - Initialize providers, extents, color filters
   - Create `Tile` object with (lat, lon, custom_build_dir)

2. **Config Load** (`O4_Config_Utils.Tile.read_from_config()`)
   - Check for per-tile config file in `Tiles/zOrtho4XP_±lat±lon/`
   - Fall back to global `Ortho4XP.cfg` if per-tile config missing
   - Populate `Tile` instance variables from config file

3. **Stage 1: Vector Map** (`O4_Vector_Map.build_poly_file(tile)`)
   ```
   OSM Data (Overpass API) → Vector Map object
   Airports layer → Feature intersection
   Roads layer → Filtered by tile bounds
   Coastline/water → Sea boundary
   Vector geometry → .node and .poly files
   ```
   - Fetches OSM XML from Overpass (rotates servers)
   - Parses into Shapely geometries
   - Applies airport/road/sea inclusion logic
   - Writes Triangle format `.node` and `.poly` to tile build dir
   - Output: `Tiles/zOrtho4XP_±lat±lon/Data±lat±lon.node`, `Data±lat±lon.poly`

4. **Stage 2: Mesh** (`O4_Mesh_Utils.build_mesh(tile)`)
   ```
   .node/.poly + DEM elevation → Triangle4XP binary
   Triangulated mesh → .mesh file
   ```
   - Loads elevation from DEM (SRTM, ALOS, NED, etc.)
   - Runs platform-specific Triangle4XP executable
   - Handles mesh simplification and iteration if triangulation fails
   - Output: `Data±lat±lon.mesh`

5. **Stage 3: Masks** (`O4_Mask_Utils.build_masks(tile)`)
   ```
   Vector features + Mesh → Mask generation
   Water/coastline detection → .png masks
   ```
   - Generates distance/legacy masks for water
   - Creates transition masks for coastlines
   - Output: `.png` files in `Masks/±lat±lon/`

6. **Stage 4: Tile/DSF** (`O4_Tile_Utils.build_tile(tile)`)
   ```
   Download thread ──┬→ Convert thread ──┐
                    │                    │
                    └→ DSF build thread ─┴→ Final .dsf
   ```
   - **Concurrent**: Three worker threads in parallel (configurable workers per thread)
   
   **Download thread** (`download_textures`):
   - Pops tiles from provider imagery lists
   - Downloads JPEG tiles via HTTP (retry up to 3 times)
   - Pushes to convert queue

   **Convert thread** (implicit via `parallel_launch`):
   - Pops JPEG from convert queue
   - Runs `nvcompress` (Windows/Linux) or `DDSTool` (macOS) to convert JPEG → DDS
   - Stores `.dds` in tile's `textures/` directory

   **DSF build thread** (`DSF.build_dsf`):
   - Reads mesh, masks, elevation
   - Constructs DSF object with terrain and property data
   - Writes temporary `.dsf.tmp` file
   - Waits for convert queue to drain
   - Atomically renames `.dsf.tmp` → `.dsf` (activates tile)

   - Output: `Tiles/zOrtho4XP_±lat±lon/Earth\ nav\ data/±lat±lon.dsf`, textures in `textures/`

### Batch Build Flow

**Entry**: `build_tile_list(tile, list_lat_lon, do_osm, do_mesh, do_mask, do_dsf, do_ovl, override_cfg)`

Loops over each (lat, lon):
1. Update tile's `.lat` and `.lon`
2. Reload build directory path
3. Optionally reload config (per-tile or global depending on `override_cfg`)
4. Call pipeline stages based on flags (`do_osm`, `do_mesh`, etc.)
5. Repeat for next tile

### Config Loading & Inheritance

```
Global Ortho4XP.cfg (created on first run with defaults)
        │
        ├─→ Module-level variables initialized
        │   (e.g., IMG.http_timeout, MESH.community_server)
        │
        └─→ global_* variables set
            (e.g., global_default_zl for fallback per-tile)

Per-Tile Config (if exists)
        │
        └─→ Tile.read_from_config()
            → Tile instance variables override defaults
            (e.g., tile.default_zl, tile.road_level)
```

**Import Order Matters**: `O4_Config_Utils` imported last in `Ortho4XP.py` because its initialization code (lines 96-139) executes `exec()` statements to set module-level variables in other modules based on config file values. If imported earlier, those modules would not yet have default values to override.

## Key Abstractions

**Tile Class** (`src/O4_Config_Utils.py`)
- Represents a single 1°×1° tile and its build state
- Instance variables: lat, lon, build_dir, dem (cache), all config vars (road_level, default_zl, etc.)
- Methods: `read_from_config()`, `write_to_config()`, `make_dirs()`
- Scope: One instance per tile being built; passed between pipeline stages

**Vector_Map Class** (`src/O4_Vector_Utils.py`)
- Represents terrain geometry as edges and nodes
- Contains: `dico_edges` (dict of line segments), nodes, coastlines, roads
- Used by: Vector map builder, mesh triangulator, mask builder

**Provider Dictionary** (`src/O4_Imagery_Utils.py`)
- Each provider is a dict entry: `providers_dict[code] = {name, url_template, max_threads, imagery_dir, ...}`
- Loaded from `.lay` files in `Providers/` subdirectories at startup
- Supports combined providers (multi-layer imagery blends)

**File_Names Module** (`src/O4_File_Names.py`)
- Single source of truth for all directory paths and file naming conventions
- Functions return full paths for imagery, DEMs, OSM data, masks, tiles, etc.
- Used instead of hardcoding paths throughout codebase

## Entry Points

**GUI Mode**:
- Location: `Ortho4XP.py:51` (`Ortho4XP = GUI.Ortho4XP_GUI()`)
- Triggers: Running `python Ortho4XP.py` with no arguments
- Responsibilities: Render map, capture tile selection, route build requests to pipeline

**Headless Mode (Tile Build)**:
- Location: `Ortho4XP.py:78-82` (try block calling VMAP/MESH/MASK/TILE)
- Triggers: Running `python Ortho4XP.py <lat> <lon> [provider] [zl]`
- Responsibilities: Load config, execute full 4-stage pipeline, exit

**Headless Mode (Batch)**:
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

**What happens:** `O4_Config_Utils` initialization code uses `exec()` to set variables in other modules (e.g., `IMG.http_timeout = value`). If config is reloaded mid-pipeline, these values change globally and in-flight requests see different timeouts.

**Why it's wrong:** Makes state flow implicit; bugs where a config change during batch build silently affects later tiles.

**Do this instead:** Pass config values as function parameters, or use a `Config` class that pipeline stages query (e.g., `stage(tile, config)` rather than `stage(tile)` and reading globals).

### Bare Exception Handlers

**What happens:** Several modules catch all exceptions with bare `except:` clauses (e.g., in `O4_Tile_Utils.build_tile_list()`, in `O4_Vector_Map.build_poly_file()`), log minimal info, and continue.

**Why it's wrong:** Masks real errors; makes debugging hard. Example: a provider returns 403 Forbidden, exception is swallowed, tile gets white textures, user doesn't know why.

**Do this instead:** Catch specific exceptions (`requests.Timeout`, `OSError`, etc.) and log the exception type and message; re-raise or return specific error codes.

### Hardcoded Retry Logic

**What happens:** Download retry count (max 3) is hardcoded in `O4_Tile_Utils.download_textures()` (`max_attempts = 3`). Convert retry count is not configurable; mesh simplification retry logic in `O4_Mesh_Utils.build_mesh()` has its own retry loop.

**Why it's wrong:** Users can't tune retry behavior for slow/flaky networks; inconsistent retry strategies across stages.

**Do this instead:** Make retry counts configurable settings in `O4_Cfg_Vars.py` and pass them as parameters to download/convert functions.

---

*Architecture analysis: 2026-08-24*
