# Shadows-of-the-Fallen



========================================================================
1. WORLD_MASTER SOURCE
========================================================================
JSON path:
  /home/aks1727/programming/gamedev/Shadows-of-the-Fallen/WORLD_MASTER/coordinates/worldmaster.json
File exists: NO

WARNING: WORLD_MASTER JSON was not found.
The remaining JSON-based checks cannot run.

========================================================================
2. BLENDER SCENE SETTINGS
========================================================================
Scene: Scene

Unit settings:
  Unit system : METRIC
  Unit scale  : 1.0
  Length unit : METERS

3D cursor:
  Location: (0.000, 0.000, 0.000)

========================================================================
3. WORLD ORIGIN
========================================================================
Origin objects found: 1

Object: WORLD_ORIGIN_0_0_0
  Location: (0.000, 0.000, 0.000)
  Type    : EMPTY
  At origin: YES

========================================================================
4. WORLD GRID
========================================================================
Collection '05_WORLD_GRID' exists: YES

Objects in WORLD_GRID:
  - WORLD_AXIS_X
      Type=CURVE Location=(0.000, 0.000, 0.000) Dimensions=(32000.000, 10.000, 10.000)
  - WORLD_AXIS_Y
      Type=CURVE Location=(0.000, 0.000, 0.000) Dimensions=(10.000, 32000.000, 10.000)
  - WORLD_GRID_1KM
      Type=MESH Location=(0.000, 0.000, 0.000) Dimensions=(32000.000, 32000.000, 0.000)
  - WORLD_ORIGIN_0_0_0
      Type=EMPTY Location=(0.000, 0.000, 0.000) Dimensions=(0.000, 0.000, 0.000)

Expected grid objects:
  WORLD_AXIS_X: YES
  WORLD_AXIS_Y: YES
  WORLD_GRID_1KM: YES

========================================================================
5. WORLD_MASTER REGIONS
========================================================================
Regions found in JSON: 0
Expected regions      : 9
Region count check: FAIL

========================================================================
6. 01_REGION_BOUNDS COLLECTION
========================================================================
Collection '01_REGION_BOUNDS' exists: YES

Objects in 01_REGION_BOUNDS: 18

Object: BOUNDS_ABYSS_ATOLL
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (3500.000, 3500.000, 330.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 180.0
    elevation_min: -150.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: abyss_atoll

Object: BOUNDS_CENTRAL_WILDERNESS
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (3000.000, 3000.000, 200.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 250.0
    elevation_min: 50.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: central_wilderness

Object: BOUNDS_GANG_CITY
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (4500.000, 4000.000, 80.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 80.0
    elevation_min: 0.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: gang_city

Object: BOUNDS_KARTHEN_MOUNTAINS
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (7500.000, 3500.000, 2400.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 3200.0
    elevation_min: 800.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: karthen_mountains

Object: BOUNDS_KHARA_ARCHIPELAGO
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (4500.000, 5000.000, 950.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 950.0
    elevation_min: 0.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: khara_archipelago

Object: BOUNDS_MAINLAND_BADLANDS
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (5000.000, 4000.000, 520.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 600.0
    elevation_min: 80.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: mainland_badlands

Object: BOUNDS_NOVA_CITY
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (5000.000, 4500.000, 150.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 150.0
    elevation_min: 0.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: nova_city

Object: BOUNDS_SOUTHERN_COASTLINE
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (12500.000, 2000.000, 60.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 60.0
    elevation_min: 0.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: southern_coastline

Object: BOUNDS_WESTERN_TIMBER
  Type      : MESH
  Location  : (0.000, 0.000, 0.000)
  Dimensions: (4000.000, 3000.000, 650.000)
  Vertices  : 8
  Polygons  : 0

  Custom properties:
    bounds_max: <bpy id property array [2]>
    bounds_min: <bpy id property array [2]>
    elevation_max: 800.0
    elevation_min: 150.0
    sotf_category: REGION_BOUND
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: western_timber

Object: CENTER_ABYSS_ATOLL
  Type      : EMPTY
  Location  : (9750.000, -12250.000, 15.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: abyss_atoll

Object: CENTER_CENTRAL_WILDERNESS
  Type      : EMPTY
  Location  : (0.000, 500.000, 150.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: central_wilderness

Object: CENTER_GANG_CITY
  Type      : EMPTY
  Location  : (3750.000, -1500.000, 40.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: gang_city

Object: CENTER_KARTHEN_MOUNTAINS
  Type      : EMPTY
  Location  : (-250.000, 6250.000, 2000.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: karthen_mountains

Object: CENTER_KHARA_ARCHIPELAGO
  Type      : EMPTY
  Location  : (-9750.000, -9500.000, 475.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: khara_archipelago

Object: CENTER_MAINLAND_BADLANDS
  Type      : EMPTY
  Location  : (2000.000, 2500.000, 340.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: mainland_badlands

Object: CENTER_NOVA_CITY
  Type      : EMPTY
  Location  : (-4000.000, -750.000, 75.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: nova_city

Object: CENTER_SOUTHERN_COASTLINE
  Type      : EMPTY
  Location  : (-250.000, -3500.000, 30.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: southern_coastline

Object: CENTER_WESTERN_TIMBER
  Type      : EMPTY
  Location  : (-3500.000, 3000.000, 475.000)
  Dimensions: (0.000, 0.000, 0.000)

  Custom properties:
    sotf_category: REGION_CENTER
    sotf_generated: SOTF_STAGE_A
    sotf_source_key: western_timber

========================================================================
7. REGION-LIKE OBJECT DISCOVERY
========================================================================
Region/bounds-like objects found globally: 54

BOUNDS_ABYSS_ATOLL
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (3500.000, 3500.000, 330.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_CENTRAL_WILDERNESS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (3000.000, 3000.000, 200.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_GANG_CITY
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (4500.000, 4000.000, 80.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_KARTHEN_MOUNTAINS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (7500.000, 3500.000, 2400.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_KHARA_ARCHIPELAGO
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (4500.000, 5000.000, 950.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_MAINLAND_BADLANDS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (5000.000, 4000.000, 520.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_NOVA_CITY
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (5000.000, 4500.000, 150.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_SOUTHERN_COASTLINE
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (12500.000, 2000.000, 60.000)
  sotf_generated: SOTF_STAGE_A

BOUNDS_WESTERN_TIMBER
  Collection(s): ['01_REGION_BOUNDS']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (4000.000, 3000.000, 650.000)
  sotf_generated: SOTF_STAGE_A

CENTER_ABYSS_ATOLL
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (9750.000, -12250.000, 15.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_CENTRAL_WILDERNESS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (0.000, 500.000, 150.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_GANG_CITY
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (3750.000, -1500.000, 40.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_KARTHEN_MOUNTAINS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (-250.000, 6250.000, 2000.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_KHARA_ARCHIPELAGO
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (-9750.000, -9500.000, 475.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_MAINLAND_BADLANDS
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (2000.000, 2500.000, 340.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_NOVA_CITY
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (-4000.000, -750.000, 75.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_SOUTHERN_COASTLINE
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (-250.000, -3500.000, 30.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

CENTER_WESTERN_TIMBER
  Collection(s): ['01_REGION_BOUNDS']
  Type        : EMPTY
  Location    : (-3500.000, 3000.000, 475.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_LAKE_VALIS
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-2200.000, 3800.000, 670.000)
  Dimensions  : (594.480, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_central_plains_interchange
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (0.000, 0.000, 300.000)
  Dimensions  : (1782.360, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_eclipse_hq_abyss
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (9800.000, -12200.000, 265.000)
  Dimensions  : (980.040, 99.600, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_eclipse_summit_station
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (300.000, 7100.000, 3100.000)
  Dimensions  : (1390.920, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_gang_city_container_port
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (4900.000, -2800.000, 254.000)
  Dimensions  : (1694.400, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_nova_deep_water_port
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-4600.000, -2800.000, 255.000)
  Dimensions  : (1420.320, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_station_0_khara
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-9200.000, -9500.000, 390.000)
  Dimensions  : (1023.120, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_sub_surface_siding
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (1800.000, 2400.000, 560.000)
  Dimensions  : (1142.520, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_POI_valis_hydro_dam
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-2200.000, 3650.000, 870.000)
  Dimensions  : (1039.320, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_abyss_atoll
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (9750.000, -12250.000, 280.000)
  Dimensions  : (1146.240, 110.880, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_central_wilderness
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (0.000, 500.000, 350.000)
  Dimensions  : (1315.560, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_gang_city
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (3750.000, -1500.000, 180.000)
  Dimensions  : (1241.760, 110.520, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_karthen_mountains
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-250.000, 6250.000, 3300.000)
  Dimensions  : (1246.680, 110.520, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_khara_archipelago
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-9750.000, -9500.000, 1050.000)
  Dimensions  : (910.200, 113.520, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_mainland_badlands
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (2000.000, 2500.000, 700.000)
  Dimensions  : (1359.720, 82.920, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_nova_city
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-4000.000, -750.000, 250.000)
  Dimensions  : (1428.000, 110.520, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_southern_coastline
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-250.000, -3500.000, 160.000)
  Dimensions  : (1392.720, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LABEL_REGION_western_timber
  Collection(s): ['06_LABELS']
  Type        : FONT
  Location    : (-3500.000, 3000.000, 900.000)
  Dimensions  : (1332.720, 84.000, 0.000)
  sotf_generated: SOTF_STAGE_A

LAKE_VALIS
  Collection(s): ['02_HYDROLOGY']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (1906.000, 1906.000, 6.000)
  sotf_generated: SOTF_STAGE_A

LAKE_VALIS_SURFACE
  Collection(s): ['02_HYDROLOGY']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (1900.000, 1900.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_CENTRAL_PLAINS_INTERCHANGE
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (0.000, 0.000, 50.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_ECLIPSE_HQ_ABYSS
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (9800.000, -12200.000, 15.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_ECLIPSE_SUMMIT_STATION
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (300.000, 7100.000, 2850.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_GANG_CITY_CONTAINER_PORT
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (4900.000, -2800.000, 4.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_NOVA_DEEP_WATER_PORT
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (-4600.000, -2800.000, 5.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_STATION_0_KHARA
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (-9200.000, -9500.000, 140.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_SUB_SURFACE_SIDING
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (1800.000, 2400.000, 310.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

POI_VALIS_HYDRO_DAM
  Collection(s): ['04_STORY_NODES']
  Type        : EMPTY
  Location    : (-2200.000, 3650.000, 620.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

RIVER_RAVEN_RIVER
  Collection(s): ['02_HYDROLOGY']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (3046.147, 7569.439, 667.546)
  sotf_generated: SOTF_STAGE_A

RIVER_THE_BLACK_GUT
  Collection(s): ['02_HYDROLOGY']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (1144.252, 2921.064, 92.615)
  sotf_generated: SOTF_STAGE_A

ROAD_HIGHWAY_1
  Collection(s): ['03_INFRASTRUCTURE']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (8209.730, 1660.801, 68.199)
  sotf_generated: SOTF_STAGE_A

ROAD_ROUTE_9
  Collection(s): ['03_INFRASTRUCTURE']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (2527.014, 6816.869, 2577.290)
  sotf_generated: SOTF_STAGE_A

WORLD_AXIS_X
  Collection(s): ['05_WORLD_GRID']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (32000.000, 10.000, 10.000)
  sotf_generated: SOTF_STAGE_A

WORLD_AXIS_Y
  Collection(s): ['05_WORLD_GRID']
  Type        : CURVE
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (10.000, 32000.000, 10.000)
  sotf_generated: SOTF_STAGE_A

WORLD_GRID_1KM
  Collection(s): ['05_WORLD_GRID']
  Type        : MESH
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (32000.000, 32000.000, 0.000)
  sotf_generated: SOTF_STAGE_A

WORLD_ORIGIN_0_0_0
  Collection(s): ['05_WORLD_GRID']
  Type        : EMPTY
  Location    : (0.000, 0.000, 0.000)
  Dimensions  : (0.000, 0.000, 0.000)
  sotf_generated: SOTF_STAGE_A

========================================================================
8. EXPECTED REGION OBJECT VERIFICATION
========================================================================

[01] karthen_mountains
  Expected object: REGION_01_KARTHEN_MOUNTAINS
  Object exists  : NO

[02] western_timber
  Expected object: REGION_02_WESTERN_TIMBER
  Object exists  : NO

[03] nova_city
  Expected object: REGION_03_NOVA_CITY
  Object exists  : NO

[04] mainland_badlands
  Expected object: BOUNDS_MAINLAND_BADLANDS
  Object exists  : YES
  Actual type    : MESH
  Collections    : ['01_REGION_BOUNDS']

[05] gang_city
  Expected object: REGION_05_GANG_CITY
  Object exists  : NO

[06] central_wilderness
  Expected object: REGION_06_CENTRAL_WILDERNESS
  Object exists  : NO

[07] southern_coastline
  Expected object: REGION_07_SOUTHERN_COASTLINE
  Object exists  : NO

[08] khara_archipelago
  Expected object: REGION_08_KHARA_ARCHIPELAGO
  Object exists  : NO

[09] abyss_atoll
  Expected object: REGION_09_ABYSS_ATOLL
  Object exists  : NO

========================================================================
9. NUMERIC BOUNDS VERIFICATION
========================================================================

[01] karthen_mountains
  JSON region: MISSING

[02] western_timber
  JSON region: MISSING

[03] nova_city
  JSON region: MISSING

[04] mainland_badlands
  JSON region: MISSING

[05] gang_city
  JSON region: MISSING

[06] central_wilderness
  JSON region: MISSING

[07] southern_coastline
  JSON region: MISSING

[08] khara_archipelago
  JSON region: MISSING

[09] abyss_atoll
  JSON region: MISSING

========================================================================
10. DUPLICATE / CONFLICT DETECTION
========================================================================
Object names matching expected region objects:
  REGION_01_KARTHEN_MOUNTAINS: 0 object(s)
  REGION_02_WESTERN_TIMBER: 0 object(s)
  REGION_03_NOVA_CITY: 0 object(s)
  BOUNDS_MAINLAND_BADLANDS: 1 object(s)
  REGION_05_GANG_CITY: 0 object(s)
  REGION_06_CENTRAL_WILDERNESS: 0 object(s)
  REGION_07_SOUTHERN_COASTLINE: 0 object(s)
  REGION_08_KHARA_ARCHIPELAGO: 0 object(s)
  REGION_09_ABYSS_ATOLL: 0 object(s)

Duplicate region_id values:
  NONE

Mainland Badlands conflict check:
  Mainland candidates: 1
    - BOUNDS_MAINLAND_BADLANDS collections=['01_REGION_BOUNDS']
  Mainland conflict: NONE

========================================================================
11. METADATA VERIFICATION
========================================================================

[01] REGION_01_KARTHEN_MOUNTAINS
  OBJECT MISSING

[02] REGION_02_WESTERN_TIMBER
  OBJECT MISSING

[03] REGION_03_NOVA_CITY
  OBJECT MISSING

[04] BOUNDS_MAINLAND_BADLANDS
  region_id: MISSING
  region_key: MISSING
  biome: MISSING
  sotf_generated: PRESENT

[05] REGION_05_GANG_CITY
  OBJECT MISSING

[06] REGION_06_CENTRAL_WILDERNESS
  OBJECT MISSING

[07] REGION_07_SOUTHERN_COASTLINE
  OBJECT MISSING

[08] REGION_08_KHARA_ARCHIPELAGO
  OBJECT MISSING

[09] REGION_09_ABYSS_ATOLL
  OBJECT MISSING

========================================================================
12. REGION ID / KEY CONSISTENCY
========================================================================

========================================================================
13. REGION ELEVATION DATA
========================================================================

========================================================================
14. REGION BOUND OVERLAP DETECTION
========================================================================
No rectangular region overlaps detected.

========================================================================
15. TERRAIN READINESS SNAPSHOT
========================================================================
This is NOT a terrain generator.

Source:
  WORLD_MASTER loaded: NO

Coordinate system:

Region data:
  9 regions present: NO

Region collection:
  01_REGION_BOUNDS exists: YES

Mainland:
  BOUNDS_MAINLAND_BADLANDS exists: YES

Terrain should NOT be generated until the bounds verification passes.

========================================================================
16. FINAL VERIFICATION SUMMARY
========================================================================

WORLD_MASTER loaded        : FAIL
Coordinate system           : FAIL
Region count = 9            : FAIL
01_REGION_BOUNDS exists     : PASS
All 9 expected objects      : FAIL
Numeric bounds match JSON   : FAIL
Required metadata present   : FAIL
Mainland compatibility      : PASS

========================================================================
OVERALL RESULT: FAIL

DO NOT generate terrain yet.
Inspect the failed checks above first.
========================================================================