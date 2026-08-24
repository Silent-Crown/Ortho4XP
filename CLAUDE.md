# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Ortho4XP is a scenery generation tool for X-Plane. It builds a terrain base mesh and
orthophoto texture layer for 1°×1° "tiles" from external elevation and imagery sources.
This is a fork of oscarpilote/Ortho4XP with additional GUI, config, and download features
(see README.md for the full change list).

## Running

```bash
# Windows
venv\Scripts\activate.bat && python Ortho4XP.py     # or: start_windows.bat

# macOS / Linux
source venv/bin/activate && python3 Ortho4XP.py     # or: ./start_mac.sh
```

`Ortho4XP.py` is the single entry point. With **no args** it launches the Tkinter GUI.
With args it runs headless:

```
python Ortho4XP.py <lat> <lon>                       # build using existing tile config
python Ortho4XP.py <lat> <lon> <provider> <zl>       # build without a tile config
```

`lat`/`lon` are integers naming the tile's SW corner. There is no test suite, linter
config, or build step — it runs from source. Native helper binaries are committed under
`Utils/{win,mac,lin}` (Triangle4XP, DSFTool, nvcompress/DDSTool, 7-zip).

## Dependencies

Python deps are in `requirements.txt` (numpy, pillow, pyproj, requests, Rtree, shapely,
scikit-fmm, gdal). GDAL and scikit-fmm are hard to pip-install on Windows/Mac, so
prebuilt `.whl` files are vendored in `Utils/win` and `Utils/mac`. `Ortho4XP.spec` drives
a PyInstaller bundle for distribution.

## Architecture

All application code lives in `src/` as flat `O4_*.py` modules (no package). `Ortho4XP.py`
appends `src/` to `sys.path` and imports them by bare name. **Import order matters**:
`O4_Config_Utils` (CFG) is imported last because it mutates module-level variables in the
other modules.

### The build pipeline

A tile build is four sequential stages, orchestrated by `Ortho4XP.py` (headless) or the
GUI. Each stage reads/writes files under the tile's working directory:

1. `O4_Vector_Map.build_poly_file` — fetch OSM vector data, produce the vector map / poly file
2. `O4_Mesh_Utils.build_mesh` — triangulate the terrain mesh (shells out to `Triangle4XP`)
3. `O4_Mask_Utils.build_masks` — build water/coastline transition masks
4. `O4_Tile_Utils.build_tile` — download imagery, cut textures to DDS, assemble the `.dsf`

Key supporting modules: `O4_Imagery_Utils` (imagery providers, tile download — the largest
module), `O4_DEM_Utils` (elevation sources), `O4_OSM_Utils` (Overpass queries),
`O4_DSF_Utils` (X-Plane DSF format), `O4_Vector_Utils` (geometry), `O4_Airport_Utils`,
`O4_Geo_Utils`, `O4_Parallel_Utils` (threaded download/convert workers).

### Config system

- `O4_Cfg_Vars.py` declares every setting (name, default, type, GUI tab, help text).
- `O4_Config_Utils.py` defines the `Tile` class and loads/saves configs.
- Two layers: a **global** config and a **per-tile** config file in each tile's directory.
  When a tile config exists it wins; otherwise global defaults are used. Building via the
  GUI auto-loads the per-tile config when the active tile changes.

`O4_File_Names.py` (imported as `FNAMES`) is the single source of truth for all directory
and file path conventions — consult it rather than hardcoding paths. Top-level data
directories (`Tiles/`, `Orthophotos/`, `Elevation_data/`, `OSM_data/`, `Masks/`, etc.) are
created on first run and are gitignored.

### Providers and external data

- `Providers/` — imagery provider definitions (`.lay` layer files, API keys/templates).
- `overpass_servers.txt` — Overpass API endpoints for OSM downloads, one `ID = URL` per
  line; the code rotates servers per request.
- `Filters/`, `Extents/`, `Patches/` — color filters, custom extent masks, tile patches.

## Gotchas

- The GUI is Tkinter and tightly coupled to config state; changing a setting's name or
  default in `O4_Cfg_Vars.py` ripples into the GUI tabs and saved config files.
- Native binaries are platform-specific and version-sensitive (see the README bug-fix log
  for repeated Triangle4XP rebuilds) — don't assume a binary swap is behavior-neutral.
- Headless build wraps the whole pipeline in a bare `except: print("Crash!")`, so failures
  are silent. Run stages individually when debugging.
