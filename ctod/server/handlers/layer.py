from ctod.core.layer import generate_layer_json
from morecantile import TileMatrixSet

def get_layer_json(tms: TileMatrixSet, cog: str, max_zoom: int = 18):
    """Generate and return a layer.json based on the COG"""

    layer_json = generate_layer_json(tms, cog, max_zoom)
    return layer_json