# Technology Stack

**Analysis Date:** 2026-08-24

## Languages

**Primary:**
- Python 3.13.5 - CPython implementation, configured in `venv/pyvenv.cfg`

## Runtime

**Environment:**
- CPython 3.13.5 (Windows x86_64)
- Virtual environment managed by `uv` (0.9.25)

**Package Manager:**
- `uv` (0.9.25) - Manages dependencies and virtual environment
- Lockfile: Not detected (uses `requirements.txt` directly)

## Frameworks

**Core:**
- tkinter (stdlib) - GUI framework for Ortho4XP_GUI, defined in `src/O4_GUI_Utils.py`

**Image Processing:**
- Pillow 12.2.0 - Image manipulation and DDS conversion support

**Build/Distribution:**
- PyInstaller - Bundling application into standalone executable, configured in `Ortho4XP.spec`

## Key Dependencies

**Critical:**
- numpy 2.4.4 - Numerical computations for mesh and imagery processing
- shapely 2.1.2 - Geometric operations for roads, water, and vector data (used in `src/O4_Vector_Utils.py`, `src/O4_Vector_Map.py`, `src/O4_OSM_Utils.py`)
- pyproj 3.7.2 - Coordinate system transformations and projection handling (used in `src/O4_Geo_Utils.py`, `src/O4_Geotag.py`)
- requests 2.33.1 - HTTP client for downloading imagery and OSM data

**Data Processing:**
- Pillow 12.2.0 - Image processing, JPEG/PNG conversion, DDS texture generation
- Rtree 1.4.1 - Spatial indexing for geometric queries
- scikit-fmm 2025.6.23 - Fast Marching Method for mesh smoothing
- gdal (platform-dependent: 3.12.3 on macOS, 3.12.2 on Windows, 3.9.0 on Linux) - Geospatial raster data access

## Configuration

**Environment:**
- Config files stored as plain text `.cfg` format in `Ortho4XP.cfg` (global) and per-tile `.cfg` files
- Config variables defined in `src/O4_Cfg_Vars.py`
- Environment variables for projection data: `PROJ_DATA`, `DYLD_LIBRARY_PATH` set at startup in `Ortho4XP.py`

**Build:**
- `Ortho4XP.spec` - PyInstaller configuration for creating standalone executable
- `requirements.txt` - Python dependencies with pinned versions
- `venv/pyvenv.cfg` - Virtual environment configuration

## Platform Requirements

**Development:**
- Python 3.13.5
- uv package manager
- PROJ library (version 5+) with `proj.db` for coordinate transformations
- GDAL library for geospatial data access
- Windows/macOS/Linux capable of running Python

**Production (Bundled):**
- PROJ coordinate database (`proj.db`)
- Embedded utilities directory containing:
  - DDS texture converters: `nvcompress.exe` (Windows), `DDSTool` (macOS), `nvcompress` (Linux)
  - `Utils/` directory with geospatial tools

**Deployment Target:**
- Windows, macOS (Intel and Apple Silicon), Linux
- Standalone executable via PyInstaller bundling

## External Binaries

**Included in Distribution:**
- `DFSTool` (version 24-5) - X-Plane DSF file format tool, used in `src/O4_Tile_Utils.py`
- `Triangle4XP.exe` (Windows/Mac/Linux variants) - Mesh generation, C++ executable
- `nvcompress` (platform-specific) or `DDSTool` (macOS) - DDS texture compression

---

*Stack analysis: 2026-08-24*
