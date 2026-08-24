# Coding Conventions

**Analysis Date:** 2026-08-24

## Naming Patterns

**Files:**
- Pattern: `O4_<Module>_<Category>.py` (e.g., `O4_Imagery_Utils.py`, `O4_Config_Utils.py`)
- Convention: Prefix all source files in `src/` with `O4_` to indicate Ortho4XP module
- Location: All core modules live in `src/` directory

**Functions:**
- Convention: snake_case (e.g., `short_latlon()`, `build_dir()`, `initialize_extents_dict()`)
- Utility functions grouped by domain in single module
- Factory/initialization functions prefixed with `initialize_` or `build_` (e.g., `initialize_extents_dict()`)

**Variables:**
- Module-level constants: UPPER_CASE_WITH_UNDERSCORES (e.g., `global_prefix`, `Preview_dir`, `http_timeout`)
- Local/parameter variables: snake_case
- Configuration dictionaries: lowercase descriptive names (e.g., `cfg_vars`, `providers_dict`, `extents_dict`)

**Types/Classes:**
- Convention: CamelCase (e.g., `Tile`, `DEM`, `parallel_worker`)
- Base class inheritance from threading.Thread or custom abstractions
- Instance variables prefixed with underscore when private (e.g., `_task`, `_queue`, `_progress`)

**Imports and Aliases:**
- All module imports use two-letter uppercase aliases: `import O4_Imagery_Utils as IMG`, `import O4_Vector_Map as VMAP`
- Aliases used throughout the codebase: IMG, VMAP, MESH, MASK, TILE, GUI, CFG, OSM, DEM, FNAMES, UI, VECT, OVL
- File: `Ortho4XP.py` (main entry point) imports and aliases all major modules at top level

## Code Style

**Formatting:**
- No formal code formatter is configured (no .pylintrc, .flake8, or pyproject.toml found)
- Line length: Varies; some long lines observed (80-100+ characters)
- Indentation: 4 spaces (standard Python convention)
- Spacing: No strict conventions enforced

**Linting:**
- Not detected: No linting configuration found
- No CI/CD workflows for automated linting
- Manual code review expected

**Comments and Separators:**
- Section separators: `################################################################################` (80+ # characters)
- Inline comments: Sparse; mostly found in complex algorithms
- Comment convention: Uppercase letter after `#` (e.g., `# Required for pyinstaller`)

## Import Organization

**Order:**
1. Standard library imports (e.g., `import os`, `import sys`, `import time`)
2. Third-party imports (e.g., `import numpy`, `from PIL import Image`, `import requests`)
3. Local module imports (prefixed with `O4_`, aliased to uppercase abbreviations)

**Path Aliases:**
- None detected; absolute imports from `src/` directory
- `sys.path.append()` used to add `src/` directory to path at runtime (in `Ortho4XP.py`)
- Provider directory added via `sys.path.append(FNAMES.Provider_dir)`

**Example import pattern** (`O4_Config_Utils.py`):
```python
import ast
import logging
import os
from math import ceil

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import E, N, S, W, filedialog, messagebox

import O4_Cfg_Vars as CFG
import O4_DEM_Utils as DEM
import O4_File_Names as FNAMES
# ... more imports
```

## Error Handling

**Patterns:**
- Bare `except:` blocks used throughout (anti-pattern but observed in `Ortho4XP.py`, `O4_Imagery_Utils.py`, `O4_Config_Utils.py`)
- Specific exception catching in newer code: `except FileNotFoundError:`, `except Exception as e:`
- Error messages printed via `UI.vprint()` and `UI.lvprint()` before raising exceptions
- Exceptions raised as bare `raise Exception` without message qualification

**Examples from codebase:**

Bare except (from `Ortho4XP.py` line 43):
```python
except:
    print("Could not create required directory", directory, ". Exit.")
    sys.exit()
```

Specific exception (from `O4_Config_Utils.py` line 126):
```python
except FileNotFoundError:
    # Create a new global config file using default values
    with open(global_cfg_file, "w") as file:
        ...
except Exception as e:
    _LOGGER.error("Error accessing global config file: %s", e)
```

## Logging

**Framework:** Custom logging via `O4_UI_Utils` module

**Functions:**
- `vprint(min_verbosity, *args)`: Print to console if verbosity >= min_verbosity
- `lvprint(min_verbosity, *args)`: Print to console AND log file if verbosity >= min_verbosity
- `logprint(*args)`: Append to `Ortho4XP.log` with timestamp

**Verbosity levels:**
- 0: Critical errors only
- 1: Normal output (default)
- 2: Debug information (for user with more detail)
- 3: Full debug output

**Pattern:**
```python
import O4_UI_Utils as UI

UI.vprint(1, "Normal priority message")
UI.lvprint(0, "Critical message with logging")
UI.logprint("Direct log entry")
```

**Logger setup** (when using stdlib logging):
- Example from `O4_Config_Utils.py`:
```python
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)
handler = logging.StreamHandler()
_LOGGER.addHandler(handler)
```

## Docstrings

**Format:** Triple-quoted docstrings with parameter and return type documentation

**Pattern:**
```python
def set_global_variables(var: str, value: str) -> None:
    """
    Set global Python variables for the application.
    
    :param str var: variable name
    :param str value: value for variable
    :returns: None
    """
    # implementation
```

**Elements:**
- One-line summary followed by blank line (when extended)
- `:param type name:` for parameters
- `:returns:` for return value
- `:return type:` for type information
- Used in functions and class methods; less common in private functions

## Configuration

**Approach:** Dictionary-driven configuration system

**Files:**
- `O4_Cfg_Vars.py`: Defines all configuration variables as Python dictionaries
- `Ortho4XP.cfg`: Global configuration file (key=value format, # for comments)
- Per-tile config: `zOrtho4XP_<latlon>.cfg` in tile build directory

**Configuration Dictionary Structure** (from `O4_Cfg_Vars.py`):
```python
cfg_app_vars = {
    "verbosity": {
        "module": "UI",
        "type": int,
        "default": 1,
        "values": (0, 1, 2, 3),
        "hint": "Verbosity determines..."
    },
    # ... more variables
}
```

**Dynamic variable assignment:** Uses `exec()` to set module variables from config

## Function Design

**Size:** 30-150 lines typical; some utility functions are 5-20 lines

**Parameters:** 
- Typically 2-4 parameters
- Class methods may have progress callbacks and mutable state lists as parameters (anti-pattern but observed)
- Type hints in docstrings, not in function signatures (Python 3.5 style)

**Return Values:**
- Functions often return tuples of related values (e.g., `(lat, lon, strlatround, strlonround)`)
- Success/status functions return integers (1 for success, 0 for failure) in config reading
- Void functions return nothing (common for initialization and side-effect functions)

## Module Design

**Exports:**
- Modules export constants, functions, and classes directly
- No explicit `__all__` lists detected
- Global module-level state: configuration variables, dictionaries, mutable lists

**Module structure** (typical):
```python
# Imports at top
import os
import sys

# Module-level constants
CONSTANT_NAME = value
config_dict = {...}

# Initialization functions (section separator comment)
def initialize_X():
    pass

# Main API functions
def main_function():
    pass
```

**Global state:**
- Module-level dictionaries: `providers_dict`, `combined_providers_dict`, `extents_dict`, `color_filters_dict`
- Module-level mutable state: `verbosity`, `red_flag`, `is_working`, `cleaning_level`, `gui`, `log`
- State modified by configuration loading in `O4_Config_Utils.py`

## Threading and Concurrency

**Pattern:** Queue-based worker thread pool

**Implementation** (from `O4_Parallel_Utils.py`):
- `parallel_worker`: Custom Thread subclass consuming queue tasks
- `parallel_execute()`: Launch workers, wait for completion, return success status
- `parallel_launch()`: Launch workers without blocking
- `parallel_join()`: Wait for workers to complete

**Global interruption flag:** `UI.red_flag` checked in worker threads; setting it stops processing

---

*Convention analysis: 2026-08-24*
