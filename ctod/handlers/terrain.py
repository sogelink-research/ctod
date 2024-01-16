from asyncio import ensure_future
from ctod.core import utils
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.generator.terrain_generator_quantized_mesh_grid import TerrainGeneratorQuantizedMeshGrid
from ctod.handlers.base import BaseHandler
from ctod.core.tile_cache import get_tile_from_disk, save_tile_to_disk
from morecantile import TileMatrixSet
from rio_tiler.errors import TileOutsideBounds
from tornado.web import HTTPError


class TerrainHandler(BaseHandler):
    """Handle Cesium terrain requests using a grid based system 
    returning quantized mesh tiles.
    
    Heights and normals are averaged between adjecent tiles to 
    create a smooth transition between tiles.
    """
    
    def __init__(self, application, request, **kwargs):
        self.terrain_factory = kwargs.pop('terrain_factory')
        self.cog_processor = kwargs.pop('cog_processor')
        self.tile_caching_path = kwargs.pop('tile_caching_path')
        super(TerrainHandler, self).__init__(application, request, **kwargs)

    async def get(self, z: int, x: int, y: int):
        """Handle a terrain request

        Args:
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
        """        
                
        try:
            cog = self.get_cog()
            extensions = self.get_extensions()
            meshing_method = self.get_meshing_method()
            min_zoom = self.get_min_zoom()
            resampling_method = self.get_resampling_method()
            skip_cache = self.get_skip_cache()
            tms = utils.get_tms()
                        
            x, y, z = utils.tile_index_from_cesium(tms, int(x), int(y), int(z))

            # Try handling the request from the cache
            if not skip_cache:
                if self._try_handle_cached_tile(cog, meshing_method, resampling_method, z, x, y):
                    return

            try:
                utils.get_tile_bounds(tms, x, y, z)
            except TileOutsideBounds:
                print("outside bounds, this should never be reached, fix if it does")
                return self.return_empty_terrain()
            
            # Always return an empty tile at 0 or requested zoom level is lower than min_zoom
            if z == 0 or z < min_zoom:
                self._return_empty_terrain(tms, cog, meshing_method, resampling_method, z, x, y)
                return
            
            terrain_generator = self._get_terrain_generator(meshing_method)            
            self.terrain_request = TerrainRequest(tms, cog, z, x, y, resampling_method, self.cog_processor, terrain_generator, extensions["octvertexnormals"])
            quantized = await self.terrain_factory.handle_request(self.terrain_request)
            
            self._try_save_tile_to_cache(cog, meshing_method, resampling_method, z, x, y, quantized)                
            self._write_output(quantized)
            
        except HTTPError as e:
                if e.status_code == 599:
                    await self.handle_cancelled_request()
                else:
                    self.set_status(e.status_code)
                    self.finish(f"Error: {e.reason}")
                
    async def handle_cancelled_request(self):
        """Handle a cancelled request"""
        
        if self.terrain_request is not None:
            await self.terrain_request.cancel()
    
    def on_connection_close(self):
        """Handle the connection being closed by the client"""
        
        ensure_future(self.handle_cancelled_request())

    def _get_terrain_generator(self, meshing_method: str):
        if meshing_method == "grid":
            return TerrainGeneratorQuantizedMeshGrid()
        
        return TerrainGeneratorQuantizedMeshGrid()
    
    def _return_empty_terrain(self, tms: TileMatrixSet, cog: str, meshing_method: str, resampling_method, z: int, x: int, y: int):
        """Return an empty terrain tile
        generated based on the tile index including geodetic surface normals

        Args:
            tms (TileMatrixSet): The tile matrix set
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
        """

        quantized_empty_tile = generate_empty_tile(tms, z, x, y)
        self._try_save_tile_to_cache(cog, meshing_method, resampling_method, z, x, y, quantized_empty_tile) 
        self._write_output(quantized_empty_tile)   
          
    def _try_handle_cached_tile(self, cog: str, meshing_method: str, resampling_method: str, z: int, x: int, y: int) -> bool:
        """Try handling the request from the cache if the path is set

        Args:
            cog (str): Path or url to cog file
            meshing_method (str): The meshing method to use
            resampling_method (str): the resampling method used
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index

        Returns:
            bool: True if the tile was handled from the cache, False otherwise
        """
        
        if self.tile_caching_path is not None:
            cached_tile = get_tile_from_disk(self.tile_caching_path, cog, meshing_method, resampling_method, z, x, y)
            if cached_tile is not None:
                self._write_output(cached_tile)
                return True
            
        return False
    
    def _try_save_tile_to_cache(self, cog: str, meshing_method: str, resampling_method: str, z: int, x: int, y: int, data: bytes):
        """Try saving the tile to the cache if the path is set

        Args:
            cog (str): Path or url to cog file
            meshing_method (str): The meshing method to use
            resampling_method (str): the resampling method used
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
            data (bytes): bytes of the .terrain tile (quantized mesh)
        """
        
        if self.tile_caching_path is not None:
            save_tile_to_disk(self.tile_caching_path, cog, meshing_method, resampling_method, z, x, y, data)     
    
    def _return_empty_terrain_tile_file(self):
        """Return an empty terrain tile from a file"""
        
        empty_terrain_path = utils.get_empty_terrain_path()
        with open(empty_terrain_path, 'rb') as f:
            self._write_output(f.read())            
            return
        
    def _write_output(self, output: bytes):
        """Write the output to the response

        Args:
            output (bytes): The output to write to the response
        """
        
        self.set_header('Content-Type', 'application/octet-stream')
        self.write(output)
        self.finish()