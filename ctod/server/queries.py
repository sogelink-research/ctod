from fastapi import Query

query_cog = Query(
    "./ctod/files/test_cog.tif",
    title="Path to cog",
    description="Path to cog (.tif, .tiff, .vrt, .json, .mosaic) file, can be local or over http",
)

query_min_zoom = Query(
    1, title="Min Zoom", description="Minimum zoom level can be set to skip zoom levels"
)

query_max_zoom = Query(
    18,
    title="Max Zoom",
    description="Maximum zoom level that will be requested by the client",
)

query_resampling_method = Query(
    None, title="Resampling Method", description="Resampling method"
)

query_meshing_method = Query(
    "grid",
    title="Meshing Method",
    description="Meshing method to use: grid, martini, delatin",
)

query_skip_cache = Query(
    False, 
    title="Skip Cache", 
    description="Set to true to prevent loading tiles from the cache. Default (False)"
)

query_default_grid_size = Query(
    20, 
    title="Default Grid Size", 
    description="The default grid size (amount of rows/cols) to use if there is no specific zoomGridSizes defined for a requested tile, Default (20)"
)

query_zoom_grid_sizes = Query(
    '{"15": 25, "16": 25, "17": 30, "18": 35, "19": 35, "20": 35, "21": 35, "22": 35}', 
    title="Default Grid Size", 
    description="Default grid size for terrain tiles"
)

query_default_max_error = Query(
    4, 
    title="Default Max Error", 
    description="The default max triangulation error in meters to use, Default (4)"
)

query_zoom_max_errors = Query(
    '{"15": 8, "16": 5, "17": 3, "18": 2, "19": 1, "20": 0.5, "21": 0.3, "22": 0.1}', 
    title="Default Grid Size", 
    description="Per level defined max error, when requested zoom for tile not specified use defaultMaxError. Default (`{'15': 8, '16': 5, '17': 3, '18': 2, '19': 1, '20': 0.5, '21': 0.3, '22': 0.1}`)"
)