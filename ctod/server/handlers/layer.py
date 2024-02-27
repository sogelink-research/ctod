from ctod.core.layer import generate_layer_json
from morecantile import TileMatrixSet

from ctod.server.queries import QueryParameters

def get_layer_json(tms: TileMatrixSet, qp: QueryParameters,):
    """Generate and return a layer.json based on the COG"""

    layer_json = generate_layer_json(tms, qp)
    return layer_json