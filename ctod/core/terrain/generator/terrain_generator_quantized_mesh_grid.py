import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.direction import Direction
from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.utils import rescale_positions


class TerrainGeneratorQuantizedMeshGrid(TerrainGenerator):
    """A TerrainGenerator for a grid based mesh."""
    
    def __init__(self):
        pass

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """
        
        main_cog = terrain_request.get_main_file()
        
        # should not happen, in case it does return empty tile
        if main_cog.processed_data is None:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile
        
        vertices, triangles, normals = main_cog.processed_data

        n = terrain_request.get_neighbour_file(Direction.NORTH)
        ne = terrain_request.get_neighbour_file(Direction.NORTHEAST)
        e = terrain_request.get_neighbour_file(Direction.EAST)
        se = terrain_request.get_neighbour_file(Direction.SOUTHEAST)
        s = terrain_request.get_neighbour_file(Direction.SOUTH)
        sw = terrain_request.get_neighbour_file(Direction.SOUTHWEST)
        w = terrain_request.get_neighbour_file(Direction.WEST)
        nw = terrain_request.get_neighbour_file(Direction.NORTHWEST)
        
        neighbour_vertices = self._get_neighbour_transformed_edge_vertices(n, ne, e, se, s, sw, w, nw)
        
        if neighbour_vertices is not None:            
            if terrain_request.generate_normals:
                neighbour_normals = self._get_neighbour_normals(n, ne, e, se, s, sw, w, nw)
            
            # for all vertices check if there are neighbour vertices based on x and y coordinate and average the z coordinate
            for i, vertice in enumerate(vertices):
                duplicated_vertices = neighbour_vertices[
                    (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
                ]
                if duplicated_vertices.size > 0:
                    # average the height
                    vertice[2] = np.average(duplicated_vertices[:, 2])
                    
                    # average the normals
                    if terrain_request.generate_normals:                        
                        duplicated_normals = neighbour_normals[
                            (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
                        ]
                        normals[i] = np.average(np.concatenate((duplicated_normals, normals[i].reshape(1, 3)), axis=0), axis=0)

        # Rescale the vertices to the tile bounds and create quantized mesh
        rescaled_vertices = rescale_positions(vertices, main_cog.tile_bounds, flip_y=False)
        quantized = quantize(rescaled_vertices, triangles, normals)
        
        return quantized
    
    def _get_neighbour_transformed_edge_vertices(self, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest) -> np.ndarray:
        """Get the neighbouring tile transformed edge vertices

        Returns:
            vertices (ndarray): edge vertices of neighbour transformed to the correct edges of the local tile
        """
        
        n_v = self._get_transformed_edge_vertices(n, Direction.SOUTH)
        ne_v = self._get_transformed_edge_vertices(ne, Direction.SOUTHWEST)
        e_v = self._get_transformed_edge_vertices(e, Direction.WEST)
        se_v = self._get_transformed_edge_vertices(se, Direction.NORTHWEST)
        s_v = self._get_transformed_edge_vertices(s, Direction.NORTH)
        sw_v = self._get_transformed_edge_vertices(sw, Direction.NORTHEAST)
        w_v = self._get_transformed_edge_vertices(w, Direction.EAST)
        nw_v = self._get_transformed_edge_vertices(nw, Direction.SOUTHEAST)
        
        # concatenate all the vertices and normals
        arrays_v = [n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
        arrays_v = list(filter(lambda x: x is not None, arrays_v))
        
        if len(arrays_v) > 0:
            return np.concatenate(arrays_v, axis=0)
        else:
            return None

    def _get_neighbour_normals(self, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest) -> np.ndarray:
        """Get the neighbouring tile normals

        Returns:
            normals (ndarray): normals of neighbour vertices aligned to the neighbour vertice array
        """
        
        n_n = self._get_edge_normals(n, Direction.SOUTH)
        ne_n = self._get_edge_normals(ne, Direction.SOUTHWEST)
        e_n = self._get_edge_normals(e, Direction.WEST)
        se_n = self._get_edge_normals(se, Direction.NORTHWEST)
        s_n = self._get_edge_normals(s, Direction.NORTH)
        sw_n = self._get_edge_normals(sw, Direction.NORTHEAST)
        w_n = self._get_edge_normals(w, Direction.EAST)
        nw_n = self._get_edge_normals(nw, Direction.SOUTHEAST)
        arrays_n = [n_n, ne_n, e_n, se_n, s_n, sw_n, w_n, nw_n]
        arrays_n = list(filter(lambda x: x is not None, arrays_n))
        
        return np.concatenate(arrays_n, axis=0)
        
    def _get_transformed_edge_vertices(self, cog_request: CogRequest, direction: Direction) -> np.ndarray:
        """Get the edge vertices of the neighbour tile transformed to the correct edges of the local tile

        Args:
            cog_request (CogRequest): The CogRequest of the neighbour tile
            direction (Direction): The edge direction of the neighbour tile

        Returns:
            np.ndarray: The edge vertices of the neighbour tile transformed to the correct edges of the local tile
        """
        
        if cog_request is None or cog_request.data is None or cog_request.is_out_of_bounds:
            return None
        
        vertices = cog_request.processed_data[0].copy()
        condition = self._get_vertice_condition(vertices, direction)
        
        return vertices[condition]

    def _get_edge_normals(self, cog_request: CogRequest, direction: Direction) -> np.ndarray:
        """Get the normals of the edge vertices of the neighbour tile

        Args:
            cog_request (CogRequest): The CogRequest of the neighbour tile
            direction (Direction): What edge to get the normals from

        Returns:
            np.ndarray: The normals of the edge vertices of the neighbour tile
        """
        
        if cog_request is None or cog_request.data is None or cog_request.is_out_of_bounds:
            return None
        
        vertices = cog_request.processed_data[0].copy()
        normals = cog_request.processed_data[2].copy()
        condition = self._get_vertice_condition(vertices, direction)
        
        return normals[condition]
        
    def _get_vertice_condition(self, vertices, direction) -> np.ndarray:
        """Based on vertices and a edge direction return a condition on what vertices to select

        Args:
            vertices (ndarray): vertices of a processed cog
            direction (Direction): direction to select the vertices

        Raises:
            ValueError: Invalid direction

        Returns:
            np.ndarray: Condition on what vertices to select
        """
        
        tile_size = 255 
        
        if direction == Direction.NORTH:
            vertices[:, 1] -= tile_size
            return vertices[:, 1] == 0             
        if direction == Direction.NORTHEAST:
            vertices[:, 0] -= tile_size
            vertices[:, 1] -= tile_size
            return (vertices[:, 0] == 0) & (vertices[:, 1] == 0)            
        elif direction == Direction.NORTHWEST:
            vertices[:, 0] += tile_size            
            vertices[:, 1] -= tile_size
            return (vertices[:, 0] == tile_size) & (vertices[:, 1] == 0)
        elif direction == Direction.EAST:
            vertices[:, 0] -= tile_size
            return vertices[:, 0] == 0
        elif direction == Direction.SOUTHEAST:
            vertices[:, 0] -= tile_size
            vertices[:, 1] += tile_size
            return (vertices[:, 0] == 0) & (vertices[:, 1] == tile_size)
        elif direction == Direction.SOUTH:
            vertices[:, 1] += tile_size
            return vertices[:, 1] == tile_size
        elif direction == Direction.SOUTHWEST:
            vertices[:, 0] += tile_size
            vertices[:, 1] += tile_size
            return (vertices[:, 0] == tile_size) & (vertices[:, 1] == tile_size)
        elif direction == Direction.WEST:
            vertices[:, 0] += tile_size   
            return vertices[:, 0] == tile_size
        else:
            raise ValueError("Invalid direction:", direction)
