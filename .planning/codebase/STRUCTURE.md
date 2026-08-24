# Codebase Structure

**Analysis Date:** 2026-08-24

## Directory Layout

```
Ortho4XP/
├── Ortho4XP.py                    # Single entry point (GUI or headless)
│
├── src/                            # All application code (23 modules, flat structure)
│   ├── O4_*.py                     # Core pipeline & utilities
│   ├── Unused/                     # Deprecated/archived code
│   └── __pycache__/                # Compiled Python cache
│
├── Providers/                      # Imagery provider definitions
│   ├── Global/                     # Global providers (.lay files)
│   ├── [Country]/                  # Regional provider overrides
│   │   └── *.lay                   # Provider layer files (URL templates, API keys)
│   └── __pycache__/
│
├── Extents/                        # Custom extent masks (per-provider)
│   ├── [Region]/
│   │   └── *.ext                   # Extent definition files
│   └── ...
│
├── Filters/                        # Color correction filters
│   └── *.png                       # Filter images
│
├── Utils/                          # Platform-specific native binaries
│   ├── win/                        # Windows executables
│   │   ├── Triangle4XP.exe
│   │   ├── 7z.exe
│   │   ├── nvcompress/nvcompress.exe
│   │   ├── moulinette.exe
│   │   └── *.whl                   # Pre-built wheels (gdal, scikit-fmm)
│   ├── mac/                        # macOS binaries (Universal, x86/ARM)
│   │   ├── Triangle4XP
│   │   ├── triangle
│   │   ├── moulinette
│   │   ├── DDSTool
│   │   ├── 7zz
│   │   └── *.whl
│   ├── lin/                        # Linux binaries
│   │   ├── Triangle4XP
│   │   ├── triangle
│   │   ├── moulinette
│   │   ├── nvcompress
│   │   └── *
│   ├── Earth/                      # Earth texture assets
│   │   └── *.gif                   # UI icons (Folder.gif, Earth.gif, etc.)
│   ├── src/                        # Source for native binaries (C, C++)
│   └── toolchains/                 # Build configs for cross-compiling
│
├── Ortho4XP.cfg                    # Global default config (created on first run)
├── Ortho4XP.cfg.bak                # Backup of global config
├── overpass_servers.txt            # Overpass API endpoints (ID = URL)
├── Ortho4XP.spec                   # PyInstaller bundle specification
│
├── Tiles/                          # Output tile data (gitignored)
│   └── zOrtho4XP_±lat±lon/         # Per-tile build directory
│       ├── Data±lat±lon.node       # Triangle input (nodes)
│       ├── Data±lat±lon.poly       # Triangle input (polygons)
│       ├── Data±lat±lon.mesh       # Triangulated mesh output
│       ├── Data±lat±lon.alt        # Altitude data
│       ├── Ortho4XP_±lat±lon.cfg   # Per-tile config (created on first build)
│       ├── Earth nav data/         # X-Plane DSF output
│       │   └── ±lat±lon/
│       │       └── ±lat±lon.dsf    # Final X-Plane scenery file
│       └── textures/               # Converted DDS textures
│           └── *.dds
│
├── Orthophotos/                    # Downloaded imagery cache (gitignored)
│   └── ±lat±lon/                   # Or grouped/provider-specific depending on layout
│       └── [provider]_[zl]/        # Provider-specific zoom level
│           └── *.jpg               # Downloaded tiles
│
├── Elevation_data/                 # Downloaded DEM cache (gitignored)
│   └── ±lat±lon/                   # Rounded to 10-degree grid
│       └── *.hgt, *.tif            # DEM files (format varies by source)
│
├── OSM_data/                       # OpenStreetMap cache (gitignored)
│   └── ±lat±lon/
│       ├── ±lat±lon_*.osm.bz2      # Compressed OSM XML from Overpass
│       └── custom_*/               # User-provided OSM overrides
│
├── Masks/                          # Generated mask files (gitignored)
│   └── ±lat±lon/
│       └── *.png                   # Water/coastline masks
│
├── Geotiffs/                       # Temporary geotiff conversions
│   └── *.obj, *.mtl, *.tif         # GDAL intermediate files
│
├── Previews/                       # Provider preview images (gitignored)
│   └── Earth/
│       └── ±lat±lon_[provider][zl].jpg
│
├── Patches/                        # User-provided tile patches
│   └── ±lat±lon/
│       └── *.patch files
│
├── yOrtho4XP_Overlays/             # X-Plane custom overlay symlink target
│   └── Earth nav data/             # Created on first build (or via "O" key)
│
├── tmp/                            # Temporary build artifacts (gitignored)
│
├── Licence/                        # License files
├── README.md                        # Project overview
├── CLAUDE.md                        # This file's guidance
│
└── venv/                           # Virtual environment (gitignored)
```

## Directory Purposes

**`src/`:**
- Purpose: All application source code (Python modules)
- Contains: 23 `O4_*.py` modules, no package nesting
- Key files: `O4_GUI_Utils.py` (largest, 86KB), `O4_Imagery_Utils.py` (103KB), `O4_Config_Utils.py` (63KB)

**`Providers/`:**
- Purpose: Define imagery sources and their API templates
- Contains: `.lay` files (layer definition files, text format with key=value pairs)
- Structure: `Global/` for worldwide providers, `[Country]/` for regional overrides
- Auto-loaded at startup by `IMG.initialize_providers_dict()` and `IMG.initialize_combined_providers_dict()`

**`Extents/`:**
- Purpose: Define spatial bounds where specific providers are valid
- Contains: `.ext` files (extent definition files)
- Usage: Used by imagery downloader to select appropriate provider for given tile coords

**`Filters/`:**
- Purpose: Color correction overlays applied during texture conversion
- Contains: PNG images used as color filters
- Usage: Referenced in provider definitions, applied via PIL during DDS conversion

**`Utils/`:**
- Purpose: Platform-specific native binaries and helper tools
- Contains: Triangle4XP, nvcompress/DDSTool, moulinette (mesh tools), 7-zip, pre-built wheels
- Subdirs: `win/`, `mac/`, `lin/` (platform-specific); `src/` (source code for binaries); `Earth/` (UI icons)
- Committed to repo (not downloaded at runtime)

**`Tiles/`, `Orthophotos/`, `Elevation_data/`, `OSM_data/`, `Masks/`, etc.:**
- Purpose: Working directories for tile builds and downloaded data
- Created: On first run (via `O4_File_Names.resource_path()` check)
- Gitignored: Yes (large, non-source files)
- Cleanup: Controlled by `cleaning_level` config setting (0-3)

**`yOrtho4XP_Overlays/`:**
- Purpose: X-Plane-compatible scenery output directory
- Created: On demand (user presses "O" key in tile map) or as symlink to `Tiles/`
- Usage: Point X-Plane's Custom Scenery folder to this directory to load generated tiles

## Key File Locations

**Entry Points:**
- `Ortho4XP.py`: Single entry point; branching logic for GUI vs. headless CLI

**Configuration:**
- `Ortho4XP.cfg`: Global defaults (text key=value format, created on first run)
- `Ortho4XP.cfg.bak`: Backup of global config
- `Tiles/zOrtho4XP_±lat±lon/Ortho4XP_±lat±lon.cfg`: Per-tile config (created on first build)
- `overpass_servers.txt`: List of Overpass API endpoints (one `ID = URL` per line)

**Core Logic:**
- `src/O4_Config_Utils.py`: Tile class, config file I/O
- `src/O4_GUI_Utils.py`: Tkinter GUI (tiles map, config tabs, batch dialog)
- `src/O4_Vector_Map.py`: Stage 1 (fetch OSM, build vector geometry)
- `src/O4_Mesh_Utils.py`: Stage 2 (triangulate mesh)
- `src/O4_Mask_Utils.py`: Stage 3 (build water masks)
- `src/O4_Tile_Utils.py`: Stage 4 (download imagery, build DSF)

**Data Sources:**
- `src/O4_Imagery_Utils.py`: Imagery provider management, JPEG download, DDS conversion
- `src/O4_DEM_Utils.py`: Elevation data sources (SRTM, ALOS, NED, Viewfinder), loading/caching
- `src/O4_OSM_Utils.py`: Overpass query construction, server rotation
- `src/O4_Vector_Utils.py`: Shapely-based geometry operations, coordinate transforms

**File I/O & Metadata:**
- `src/O4_File_Names.py`: Centralized path construction (single source of truth)
- `src/O4_DSF_Utils.py`: X-Plane `.dsf` file serialization (the binary output format)

**Utilities:**
- `src/O4_Parallel_Utils.py`: Thread pool executor for concurrent download/conversion
- `src/O4_UI_Utils.py`: Console logging, progress bar, thread-safe print queue
- `src/O4_Geo_Utils.py`: WGS84 / Mercator conversions
- `src/O4_Airport_Utils.py`: Parse ICAO airport data from OSM
- `src/O4_Version.py`: Version string (imported by GUI)

## Naming Conventions

**Files:**
- Application code: `O4_[Module].py` (O4 = Ortho4XP generation 4)
- Test/unused: `O4_[Module]_test.py` or moved to `Unused/`
- Tile build dir: `zOrtho4XP_±lat±lon` (leading 'z' to sort last in directory listing)
- Config files: `Ortho4XP.cfg` (global), `Ortho4XP_±lat±lon.cfg` (per-tile)
- Imagery: `[y]_[x]_[provider][zl].jpg` (tile y/x coordinates, provider code, zoom level)
- Masks: `[y]_[x]_ZL[zl].png` (same scheme)
- DDS textures: `[y]_[x]_[provider][zl].dds` (converted from JPEG)

**Directories:**
- Lat/lon paths: `long_latlon()` format: `±(rounded)lat±lon/±lat±lon/` (e.g., `+10-160/+10-160/` for 10.5°N, 160.5°E)
- Tile coords: `short_latlon()` format: `±lat±lon` (e.g., `+10-160` without rounding)
- Imagery subdirs: Depend on provider's `imagery_dir` setting: `normal` (by short_latlon), `grouped` (by long_latlon), `code` (by provider code), or custom

**Functions:**
- camelCase: `buildMesh()`, `downloadTextures()` — NOT used; actually snake_case throughout
- snake_case: `build_mesh()`, `download_textures()`, `build_poly_file()` — standard
- Constants: `UPPERCASE` (e.g., `Imagery_dir`, `Tile_dir` in O4_File_Names.py)

**Variables:**
- Tile attributes: lowercase with underscores (e.g., `tile.default_zl`, `tile.road_level`, `tile.iterate`)
- Config settings: lowercase with underscores (e.g., `max_download_slots`, `cleaning_level`)
- Dicts: descriptive plural (e.g., `providers_dict`, `extents_dict`, `color_filters_dict`)
- Booleans: prefix with `is_` or `has_` (e.g., `UI.is_working`, `UI.red_flag` — though inconsistent)

**Types:**
- Classes: PascalCase (e.g., `Tile`, `Vector_Map`, `Ortho4XP_GUI`)
- Exceptions: Use Python builtins, no custom exception classes defined

## Where to Add New Code

**New Imagery Provider:**
- Create `.lay` file under `Providers/[Region]/` with URL template and metadata
- Register in `IMG.initialize_providers_dict()` auto-discovery (reads all `.lay` files)
- No code change needed if following `.lay` format

**New Elevation Source:**
- Add to `DEM_sources` dict in `src/O4_DEM_Utils.py`
- Implement download/caching logic (follow SRTM pattern)
- Update `src/O4_Cfg_Vars.py` if adding a new config setting for the source

**New Configuration Setting:**
- Declare in `src/O4_Cfg_Vars.py`: add to `cfg_tile_vars` or `cfg_app_vars` dict with type, default, values, hint
- Setting automatically appears in GUI tabs (by `gui_tab` field)
- Code accesses via `tile.setting_name` or module-level variable (e.g., `IMG.http_timeout`)
- Saved/loaded by `O4_Config_Utils.py` (no code changes needed)

**New GUI Window/Tab:**
- Add to `src/O4_GUI_Utils.py` class `Ortho4XP_GUI`
- Create frame and widgets in `__init__` method
- Call `self.grid()` to place in layout
- Bind event handlers to button/field changes

**New Build Stage or Variant:**
- Add function to relevant module (e.g., `O4_Vector_Map.py`, `O4_Tile_Utils.py`)
- Follow naming: `build_[thing](tile)` takes Tile instance, returns 0 (error) or 1 (success)
- Set/check `UI.is_working` and `UI.red_flag` flags for concurrency safety
- Sequence calls in `O4_Tile_Utils.build_all()` or `build_tile_list()` for batch integration

**New Utility Function:**
- Place in existing utility module if it fits (e.g., vector math → `O4_Vector_Utils.py`, paths → `O4_File_Names.py`)
- If utility is general-purpose and doesn't fit elsewhere, add to `src/O4_Geo_Utils.py` or create new `O4_[Purpose]_Utils.py`
- Use snake_case function names

**Tests:**
- No test framework configured (no pytest, unittest, or CI)
- Manual testing via GUI or CLI commands recommended
- Example: `python Ortho4XP.py 40 -74 sentinel2 18` builds a single tile headless

## Special Directories

**`src/Unused/`:**
- Purpose: Archived/deprecated code
- Generated: No, manually moved
- Committed: Yes (historical record)
- Rationale: Keeps old implementations for reference before deletion

**`tmp/`:**
- Purpose: Temporary build artifacts (intermediate files during build)
- Generated: Yes, during builds
- Committed: No (gitignored)
- Cleanup: Controlled by `cleaning_level` config (level 1+)

**`Utils/`:**
- Purpose: Pre-compiled native binaries
- Generated: No (manually built and committed)
- Committed: Yes (required for distribution; avoids compilation step)
- Versioning: Specific versions pinned (e.g., Triangle4XP recompiled when changes needed, see README changelog)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents (this directory)
- Generated: Yes, by `/gsd-map-codebase` skill
- Committed: Yes (for reference in planning)
- Not used by application (informational only)

---

*Structure analysis: 2026-08-24*
