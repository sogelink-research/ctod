from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.cog.processor.cog_processor_quantized_mesh_grid import CogProcessorQuantizedMeshGrid
from ctod.core.cog.processor.cog_processor_quantized_mesh_delatin import CogProcessorQuantizedMeshDelatin
from ctod.core.cog.processor.cog_processor_quantized_mesh_martini import CogProcessorQuantizedMeshMartini

MESH_PROCESSORS = dict(
    grid = CogProcessorQuantizedMeshGrid(),
    delatin = CogProcessorQuantizedMeshDelatin(),
    martini = CogProcessorQuantizedMeshMartini()
)

def get_cog_processor_for_method(mesh_processor: str) -> CogProcessor:
    # todo: there really should be a more elegant way of doing this...
    return MESH_PROCESSORS.get(mesh_processor, MESH_PROCESSORS['grid'])

