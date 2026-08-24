# External Integrations

**Analysis Date:** 2026-08-24

## APIs & External Services

**OpenStreetMap (Overpass API):**
- Service: Overpass API - OSM vector data download for roads, water, airports
- SDK/Client: `requests` library with custom parsing in `src/O4_OSM_Utils.py`
- Auth: None (public API)
- Server Selection: Multiple mirror servers configured in `overpass_servers.txt`:
  - DE: https://overpass-api.de/api/interpreter
  - CH: https://overpass.osm.ch/api/interpreter
  - FR: https://overpass.openstreetmap.fr/api/interpreter
  - VK: https://maps.mail.ru/osm/tools/overpass/api/interpreter
- Features: Random server rotation for load balancing, configurable via `overpass_server_choice` setting

**Imagery Providers (TMS):**
- Multiple tile map service providers (Bing, USGS, Maxar, Google, etc.)
- Implementation: Custom URL template system in `Providers/O4_Custom_URL.py`
- Client: `requests` library in `src/O4_Imagery_Utils.py`
- Download: Parallel multi-threaded downloads controlled by `max_download_slots` setting

**Community Servers:**
- Service: Custom community-hosted tile servers
- Configuration: `community_server.txt` lists community-managed OSM/imagery mirrors
- Usage: Fallback providers for imagery and OSM data

## Data Storage

**Databases:**
- None detected - project is file-based only

**File Storage:**
- Local filesystem only
- Cached data stored in project directories:
  - `Orthophotos/` - Downloaded imagery tiles
  - `OSM_data/` - Downloaded OpenStreetMap vector data (XML)
  - `Elevation_data/` - Downloaded or calculated elevation data
  - `Geotiffs/` - Processed raster data
  - `Tiles/` - Generated X-Plane scenery files
  - `Masks/` - Generated mask data for water/features
  - `Previews/` - Generated preview images

**Caching:**
- Aggressive caching of downloaded tiles and OSM data
- Reuse of cached data for repeated tile builds
- Manual cache clearing via "Erase cached data" GUI function

## Elevation & Geospatial Data Sources

**DEM (Digital Elevation Model) Providers:**

1. **Viewfinderpanorama (J. de Ferranti)**
   - Global coverage, mostly worldwide
   - Source definition: `"Viewfinderpanoramas (J. de Ferranti) - mostly worldwide"`
   - Used as default in `src/O4_DEM_Utils.py`

2. **SRTM (Shuttle Radar Topography Mission)**
   - Global coverage via CGIAR-CSI
   - One of three global sources

3. **SRTMv3 (from OpenTopography)**
   - Manual download required (not auto-fetched)
   - Higher precision SRTM data

4. **NED 1" (USGS National Elevation Dataset)**
   - Coverage: USA, Canada, Mexico
   - Direct download from USGS via HTTP

5. **NED 1/3" (USGS)**
   - Coverage: USA only
   - Higher resolution variant

6. **ALOS 3W30 (from OpenTopography)**
   - Manual download required
   - Global alternative to SRTM

7. **ALOS (JAXA Advanced Land Observing Satellite)**
   - Global coverage

**Data Access Pattern:**
- Sources configured as strings in `src/O4_DEM_Utils.py`
- Composite sources supported (multiple sources combined with `;`)
- Local manual files referenced via `{latlon}` placeholder substitution
- GDAL used for raster file reading when available

## Geospatial Libraries & APIs

**Shapely (2.1.2):**
- Geometric operations library
- Used for: Road/water geometry simplification, area calculations
- Files: `src/O4_Vector_Utils.py`, `src/O4_Vector_Map.py`, `src/O4_OSM_Utils.py`, `src/O4_Airport_Utils.py`

**pyproj (3.7.2):**
- Coordinate system transformations
- Uses PROJ library with `proj.db` database
- Environment: `PROJ_DATA` environment variable points to system proj database
- Fallback: Bundled pyproj data if system PROJ not found
- Files: `src/O4_Geo_Utils.py`, `src/O4_Geotag.py`

**GDAL (Geospatial Data Abstraction Library):**
- Optional raster data access
- Platform-dependent installation:
  - Windows: gdal==3.12.2
  - macOS: gdal==3.12.3
  - Linux: gdal==3.9.0
- Used via `from osgeo import gdal` with exception handling for missing library
- Files: `src/O4_DEM_Utils.py`

## Authentication & Identity

**Auth Provider:**
- None - All external services are public/unauthenticated
- API Keys: Some imagery providers support optional API keys (e.g., Bing, Here) but not required

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Console logging via Python's `logging` module
- Verbosity controlled by `verbosity` config setting (1 = default)
- Files: `src/O4_GUI_Utils.py` (logging.StreamHandler), various modules with `UI.vprint()`
- Log file: `Ortho4XP.log` (text log of session)

## HTTP Configuration

**HTTP Client (requests library):**
- Default timeout: `http_timeout = 10.0` seconds (configurable)
- Retries for connection failures: `max_connect_retries = 5` (configurable)
- Retries for bad/incomplete data: `max_baddata_retries = 5` (configurable)
- Response validation: `check_tms_response = True` (configurable)
- User-Agent: Generic Firefox UA string for web requests
- Request headers defined in `src/O4_Imagery_Utils.py`:
  ```
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
  "Accept": "*/*"
  "Connection": "keep-alive"
  "Accept-Encoding": "gzip, deflate"
  ```

## Environment Configuration

**Required env vars (set at runtime):**
- `PROJ_DATA` - Path to PROJ coordinate database directory (set in `Ortho4XP.py`)
- `DYLD_LIBRARY_PATH` - macOS library path for bundled libraries (set in `Ortho4XP.py`)

**Secrets location:**
- No secrets/credentials stored - project is entirely public API based

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## X-Plane Integration

**Target Application:**
- X-Plane flight simulator (versions 11, 12 supported)
- Output format: DSF (Scenery Definition Format) with custom overlays
- Scenery path: `custom_scenery_dir` configuration (default: `C:/X-Plane 12/Custom Scenery`)
- Overlay source: X-Plane global scenery base files
- Symlink support: Can create symlink to `yOrtho4XP_Overlays` folder (one-click feature)

---

*Integration audit: 2026-08-24*
