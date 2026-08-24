#!/usr/bin/env python3
import sys
import os

Ortho4XP_dir = '..' if getattr(sys, 'frozen', False) else '.'

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _proj_data_path = os.path.join(sys._MEIPASS, "pyproj", "proj_dir", "share", "proj")
    _lib_path = os.path.join(sys._MEIPASS, "_internal")
    os.environ["PROJ_DATA"] = _proj_data_path
    os.environ["DYLD_LIBRARY_PATH"] = _lib_path + ":" + os.environ.get("DYLD_LIBRARY_PATH", "")

from pyproj import datadir

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    datadir.set_data_dir(_proj_data_path)

sys.path.append(os.path.join(Ortho4XP_dir, 'src'))

import O4_File_Names as FNAMES
sys.path.append(FNAMES.Provider_dir)
import O4_Imagery_Utils as IMG
import O4_Vector_Map as VMAP
import O4_Mesh_Utils as MESH
import O4_Mask_Utils as MASK
import O4_Tile_Utils as TILE
import O4_GUI_Utils as GUI
import O4_Config_Utils as CFG  # CFG imported last because it can modify other modules variables

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
    if len(sys.argv) == 1:  # switch to the graphical interface
        Ortho4XP = GUI.Ortho4XP_GUI()
        Ortho4XP.mainloop()
        print("Bon vol!")
    else:  # sequel is only concerned with command line
        import O4_CLI_Utils as CLI
        CLI.dispatch(sys.argv[1:])