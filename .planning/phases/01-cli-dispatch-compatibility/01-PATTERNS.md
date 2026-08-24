# Phase 1: CLI Dispatch & Compatibility - Pattern Map

**Mapped:** 2026-08-24
**Files analyzed:** 2 (1 new, 1 modified)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/O4_CLI_Utils.py` (new) | controller/utility (dispatch + orchestration) | request-response (argv in, exit code out) | `src/O4_File_Names.py` (module conventions) + `Ortho4XP.py` (dispatch body it replaces) | role-match |
| `Ortho4XP.py` (modified) | entry point / controller | request-response | itself (existing 84-line file) | exact (same file, targeted edit) |

## Pattern Assignments

### `src/O4_CLI_Utils.py` (new module)

**Analog for module conventions:** `src/O4_File_Names.py`

**Imports pattern** (`src/O4_File_Names.py:1-5`):
```python
import os
import sys
from math import floor

import O4_UI_Utils as UI
```
Stdlib imports first, then O4_ project imports aliased. `O4_CLI_Utils.py` should follow
the same shape: `import sys`, `import math`, `import traceback`, `import argparse` at
top; **no top-level import of `O4_Config_Utils`/`O4_Vector_Map`/`O4_Mesh_Utils`/
`O4_Mask_Utils`/`O4_Tile_Utils`** — those go inside the function that runs the build
(see Shared Patterns > CFG-import-last below).

**Function naming convention** (`src/O4_File_Names.py:35-38`):
```python
def short_latlon(lat, lon):
    strlat = "{:+.0f}".format(lat).zfill(3)
    strlon = "{:+.0f}".format(lon).zfill(4)
    return strlat + strlon
```
snake_case, small single-purpose functions. `O4_CLI_Utils.py` should use
`parse_and_floor_coord()`, `run_build()`, `run_legacy()`, `run_gui()`, `dispatch()` —
same naming register as existing `build_*`/`initialize_*` functions elsewhere in the
codebase (e.g. `IMG.initialize_extents_dict`).

**Section separator convention** (used throughout `src/*.py`, e.g.
`src/O4_File_Names.py:34`):
```python
##############################################################################
```
Use this 80-char `#` separator between top-level functions in the new module, matching
existing file style.

**Two-letter alias convention:** the new module is imported elsewhere as
`import O4_CLI_Utils as CLI` (matches `IMG`, `VMAP`, `MESH`, `MASK`, `TILE`, `GUI`, `CFG`,
`FNAMES`, `UI` — all two/four-letter uppercase aliases already established across the
codebase).

**Tile construction pattern to reuse inside `run_build()`** (`src/O4_Config_Utils.py:142-158`,
called from `Ortho4XP.py:64,72-74`):
```python
tile = CFG.Tile(lat, lon, '')
tile.default_website = provider_code   # only if provider given
tile.default_zl = zoomlevel            # only if zl given
```
`Tile.__init__(self, lat, lon, custom_build_dir)` — confirmed signature at
`src/O4_Config_Utils.py:144`. Pass `''` for `custom_build_dir` (matches existing legacy
call site).

**4-stage pipeline call to reuse inside `run_build()`** (`Ortho4XP.py:78-81`):
```python
VMAP.build_poly_file(tile)
MESH.build_mesh(tile)
MASK.build_masks(tile)
TILE.build_tile(tile)
```

---

### `Ortho4XP.py` (modified — 84 lines total, read in full)

**Preserve verbatim — module-level imports and init block** (`Ortho4XP.py:1-53`):
```python
#!/usr/bin/env python3
import sys
import os
...
import O4_File_Names as FNAMES
sys.path.append(FNAMES.Provider_dir)
import O4_Imagery_Utils as IMG
import O4_Vector_Map as VMAP
import O4_Mesh_Utils as MESH
import O4_Mask_Utils as MASK
import O4_Tile_Utils as TILE
import O4_GUI_Utils as GUI
import O4_Config_Utils as CFG  # CFG imported last because it can modify other modules variables

cmd_line = "USAGE: Ortho4XP.py lat lon imagery zl (won't read a tile config)\n  OR:  Ortho4XP.py lat lon (with existing tile config file)"

if __name__ == '__main__':
    if not os.path.isdir(FNAMES.Utils_dir):
        print("Missing ", FNAMES.Utils_dir, "directory, check your install. Exiting.")
        sys.exit()
    for directory in (FNAMES.Preview_dir, FNAMES.Provider_dir, FNAMES.Extent_dir, FNAMES.Filter_dir, FNAMES.OSM_dir,
                      FNAMES.Mask_dir, FNAMES.Imagery_dir, FNAMES.Elevation_dir, FNAMES.Geotiff_dir, FNAMES.Patch_dir,
                      FNAMES.Tile_dir, FNAMES.Tmp_dir):
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
                print("Creating missing directory", directory)
            except:
                print("Could not create required directory", directory, ". Exit.")
                sys.exit()
    IMG.initialize_extents_dict()
    IMG.initialize_color_filters_dict()
    IMG.initialize_providers_dict()
    IMG.initialize_combined_providers_dict()
```
This block (lines 1-49, plus `cmd_line` at line 30) must run unchanged, before any
dispatch decision. `cmd_line` (line 30) is kept verbatim per locked decision, still
printed only from the legacy-path usage-error branch (now inside `O4_CLI_Utils`, passed
or reconstructed there — do not delete this string from `Ortho4XP.py` since it is the
existing source of truth for legacy usage text; simplest is to keep it here and pass it
into `CLI.dispatch()`, or duplicate the identical string into `O4_CLI_Utils.py` — planner's
call, either satisfies "keep exact text").

**Replace — legacy dispatch + bare except block** (`Ortho4XP.py:50-84`):
```python
    if len(sys.argv) == 1:  # switch to the graphical interface
        Ortho4XP = GUI.Ortho4XP_GUI()
        Ortho4XP.mainloop()
        print("Bon vol!")
    else:  # sequel is only concerned with command line
        if len(sys.argv) < 3:
            print(cmd_line); sys.exit()
        try:
            lat = int(sys.argv[1])
            lon = int(sys.argv[2])
        except:
            print(cmd_line); sys.exit()
        if len(sys.argv) == 3:
            try:
                tile = CFG.Tile(lat, lon, '')
            except Exception as e:
                print(e)
                print("ERROR: could not read tile config file."); sys.exit()
        else:
            try:
                provider_code = sys.argv[3]
                zoomlevel = int(sys.argv[4])
                tile = CFG.Tile(lat, lon, '')
                tile.default_website = provider_code
                tile.default_zl = zoomlevel
            except:
                print(cmd_line); sys.exit()
        try:
            VMAP.build_poly_file(tile)
            MESH.build_mesh(tile)
            MASK.build_masks(tile)
            TILE.build_tile(tile)
            print("Bon vol!")
        except:
            print("Crash!")
```
Everything from `if len(sys.argv) == 1:` (line 50) through EOF (line 84) is replaced by:
```python
    import O4_CLI_Utils as CLI
    CLI.dispatch(sys.argv[1:])
```
`GUI.Ortho4XP_GUI()`/`.mainloop()` and the exact `"Bon vol!"` print stay — either kept in
`Ortho4XP.py`'s no-arg branch directly (simplest, since `GUI` is already imported at
module top) or moved into `CLI.run_gui()` if the planner wants `O4_CLI_Utils` to own all
three branches uniformly. Given `GUI` is already an existing top-level import in
`Ortho4XP.py` (line 27, harmless to import early — unlike CFG/VMAP/MESH/MASK/TILE it does
not mutate other modules), leaving the no-arg GUI branch inline in `Ortho4XP.py` and only
delegating the legacy/subcommand branches to `CLI.dispatch()` is the smaller diff and
still satisfies "no-arg behavior unchanged" without adding a new function crossing the
module boundary for zero benefit.

## Shared Patterns

### CFG-import-last / lazy build-module imports
**Source:** `Ortho4XP.py:28` (`import O4_Config_Utils as CFG  # CFG imported last because it can modify other modules variables`)
**Apply to:** `O4_CLI_Utils.py`

`O4_CLI_Utils.py` must NOT import `O4_Config_Utils`, `O4_Vector_Map`, `O4_Mesh_Utils`,
`O4_Mask_Utils`, or `O4_Tile_Utils` at module top level. `Ortho4XP.py` imports
`O4_CLI_Utils` (to call `CLI.dispatch`), and if `O4_CLI_Utils` imported CFG at its own
top level, CFG's `exec()`-based mutation of other modules' variables would run at
`O4_CLI_Utils` import time — before `Ortho4XP.py`'s own `import O4_Config_Utils as CFG`
line (line 28) has established the "CFG last" order. Do these imports inside
`run_build()`:
```python
def run_build(lat, lon, provider=None, zl=None):
    import O4_Config_Utils as CFG
    import O4_Vector_Map as VMAP
    import O4_Mesh_Utils as MESH
    import O4_Mask_Utils as MASK
    import O4_Tile_Utils as TILE
    ...
```

### Error handling — replace bare `except:` with report-and-exit-1
**Source:** `Ortho4XP.py:83-84` (being replaced), pattern per RESEARCH.md Pattern 3
**Apply to:** `O4_CLI_Utils.run_build()` / wherever the pipeline call is wrapped
```python
import sys
import traceback

try:
    ...  # VMAP -> MESH -> MASK -> TILE
except SystemExit:
    raise
except Exception:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
```
This is the only place in the codebase using this pattern — it is new to the project
(existing code uses bare `except: print(...)` everywhere else), so there is no in-repo
analog beyond the block being replaced. Do not propagate this new pattern back into
other modules; scope is this one wrapper per locked decision.

### Coordinate parsing — replace `int()` with `math.floor(float())`
**Source:** `Ortho4XP.py:58-59` (`lat = int(sys.argv[1])`, being replaced)
**Apply to:** `O4_CLI_Utils.parse_and_floor_coord()` / `parse_lat()` / `parse_lon()`
```python
import math

def parse_and_floor_coord(value, *, lo, hi, name):
    try:
        f = float(value)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {value!r}")
    n = math.floor(f)
    if not (lo <= n <= hi):
        raise ValueError(f"{name} {n} out of range [{lo}, {hi}]")
    return n
```
No existing in-repo analog uses `math.floor` for coordinate handling — this is a new
correctness fix (CLI-04), sourced from stdlib docs per RESEARCH.md, not from an existing
codebase pattern.

## No Analog Found

None. Both files have adequate in-repo analogs — `O4_File_Names.py` for new-module
conventions, and `Ortho4XP.py` itself (before/after) for the entry-point edit. The
argparse/traceback/math.floor mechanics are new to this codebase (first CLI-framework
usage) and are sourced from RESEARCH.md's stdlib patterns rather than an existing file,
as noted inline above.

## Metadata

**Analog search scope:** `src/*.py` (module conventions), `Ortho4XP.py` (entry point,
read in full), `src/O4_Config_Utils.py:140-179` (`Tile.__init__`)
**Files scanned:** `Ortho4XP.py`, `src/O4_File_Names.py`, `src/O4_Config_Utils.py`
**Pattern extraction date:** 2026-08-24
