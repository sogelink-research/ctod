from fastapi import Query


query_cog = Query(
    None,
    title="Path to cog",
    description="Path to cog (.tif, .tiff, .vrt, .json, .mosaic) file, can be local or over http",
)

query_min_zoom = Query(
    None,
    title="Minimum Zoomlevel",
    description="When set CTOD returns empty tiles for zoom < minZoom, Default (1)",
)

query_max_zoom = Query(
    None,
    title="Max Zoom",
    description="Maximum zoom level that will be requested by the client, Default (18)",
)

query_resampling_method = Query(
    None,
    title="Resampling Method",
    description="Resampling method for COG: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss', 'rms'. Default ('none')",
)

query_meshing_method = Query(
    None,
    title="Meshing Method",
    description="Meshing method to use: grid, martini, delatin, Default (grid)",
)

query_skip_cache = Query(
    None,
    title="Skip Cache",
    description="Set to true to prevent loading tiles from the cache. Default (False)",
)

query_default_grid_size = Query(
    None,
    title="Default Grid Size",
    description="The default grid size (amount of rows/cols) to use if there is no specific zoomGridSizes defined for a requested tile, Default (20)",
)

query_zoom_grid_sizes = Query(
    None, title="Default Grid Size", description="Default grid size for terrain tiles"
)

query_default_max_error = Query(
    None,
    title="Default Max Error",
    description="The default max triangulation error in meters to use, Default (4)",
)

query_zoom_max_errors = Query(
    None,
    title="Default Grid Size",
    description="Per level defined max error, when requested zoom for tile not specified use defaultMaxError. Default (`{'15': 8, '16': 5, '17': 3, '18': 2, '19': 1, '20': 0.5, '21': 0.3, '22': 0.1}`)",
)

query_extensions = Query(
    None,
    title="Quantized Mesh Extensions",
    description="Normally supplied trough Accept header but can be set and overridden here, by multiple extensions user separator '-' (octvertexnormals-watermask) Currently only octvertexnormals is supported",
)


class QueryParameters:
    """
    Query parameters for the /tile endpoint
    """

    def __init__(
        self,
        cog: str,
        minZoom: int,
        maxZoom: int,
        resamplingMethod: str,
        meshingMethod: str,
        skipCache: bool,
        defaultGridSize: int,
        zoomGridSizes: str,
        defaultMaxError: int,
        zoomMaxErrors: str,
        extensions: str,
    ):
        self.cog = cog
        self.minZoom = minZoom
        self.maxZoom = maxZoom
        self.resamplingMethod = resamplingMethod
        self.meshingMethod = meshingMethod
        self.skipCache = skipCache
        self.defaultGridSize = defaultGridSize
        self.zoomGridSizes = zoomGridSizes
        self.defaultMaxError = defaultMaxError
        self.zoomMaxErrors = zoomMaxErrors
        self.extensions = extensions

    def get_cog(self) -> str:
        """Returns the cog if it's not None, otherwise returns a default value"""

        return self.cog if self.cog is not None else "./ctod/files/test_cog.tif"

    def get_min_zoom(self) -> int:
        """Returns the minZoom if it's not None, otherwise returns a default value"""

        return self.minZoom if self.minZoom is not None else 1

    def get_max_zoom(self) -> int:
        """Returns the maxZoom if it's not None, otherwise returns a default value"""

        return self.maxZoom if self.maxZoom is not None else 18

    def get_resampling_method(self) -> str:
        """Returns the resamplingMethod"""

        return self.resamplingMethod

    def get_meshing_method(self) -> str:
        """Returns the meshingMethod if it's not None, otherwise returns a default value"""

        return self.meshingMethod if self.meshingMethod is not None else "grid"

    def get_skip_cache(self) -> bool:
        """Returns the skipCache if it's not None, otherwise returns a default value"""

        return self.skipCache if self.skipCache is not None else False

    def get_default_grid_size(self) -> int:
        """Returns the defaultGridSize if it's not None, otherwise returns a default value"""

        return self.defaultGridSize if self.defaultGridSize is not None else 18

    def get_zoom_grid_sizes(self) -> str:
        """Returns the zoomGridSizes if it's not None, otherwise returns a default value"""

        return (
            self.zoomGridSizes
            if self.zoomGridSizes is not None
            else (
                '{"15": 25, "16": 25, "17": 30, "18": 35, "19": 35, "20": 35, "21": 35, "22": 35}'
                if self.defaultGridSize is None
                else None
            )
        )

    def get_default_max_error(self) -> int:
        """Returns the defaultMaxError if it's not None, otherwise returns a default value"""

        return self.defaultMaxError if self.defaultMaxError is not None else 4

    def get_zoom_max_errors(self) -> str:
        """Returns the zoomMaxErrors if it's not None, otherwise returns a default value"""

        return (
            self.zoomMaxErrors
            if self.zoomMaxErrors is not None
            else (
                '{"15": 8, "16": 5, "17": 3, "18": 2, "19": 1, "20": 0.5, "21": 0.3, "22": 0.1}'
                if self.defaultMaxError is None
                else None
            )
        )

    def get_extensions(self) -> str:
        """Returns the extensions if it's not None, otherwise returns a default value"""

        return self.extensions if self.extensions is not None else None

    def get_query_url(self, base_url: str) -> str:
        """Add query parameters to a base URL and return the final URL."""

        query_params = [
            f"{attr}={getattr(self, attr)}"
            for attr in vars(self)
            if getattr(self, attr) is not None
        ]
        query_string = "&".join(query_params)

        if "?" in base_url:
            final_url = f"{base_url}&{query_string}"
        else:
            final_url = f"{base_url}?{query_string}"

        return final_url
