import logging
import numpy as np
import triangle
#import time

from ctod.core.normals import calculate_normals
from ctod.core.cog.cog_request import CogRequest
from ctod.core.direction import Direction
from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.utils import rescale_positions
from shapely.geometry import LineString, MultiLineString, Point, MultiPoint, GeometryCollection
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid

class TerrainGeneratorQuantizedMeshDelatin(TerrainGenerator):
    """A TerrainGenerator for a delatin based mesh."""
    
    def __init__(self):
        self.ellipsoid: Ellipsoid = WGS84

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """
        
        #start_time = time.time()
        
        main_cog = terrain_request.get_main_file()
        
        # should not happen, in case it does return empty tile
        if main_cog is None or main_cog.data is None or main_cog.is_out_of_bounds:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile
        
        n = terrain_request.get_neighbour_file(Direction.NORTH)
        ne = terrain_request.get_neighbour_file(Direction.NORTHEAST)
        e = terrain_request.get_neighbour_file(Direction.EAST)
        se = terrain_request.get_neighbour_file(Direction.SOUTHEAST)
        s = terrain_request.get_neighbour_file(Direction.SOUTH)
        sw = terrain_request.get_neighbour_file(Direction.SOUTHWEST)
        w = terrain_request.get_neighbour_file(Direction.WEST)
        nw = terrain_request.get_neighbour_file(Direction.NORTHWEST)
        
        #quantized = self.triangulate_over_tiles(main_cog, n, ne, e, se, s, sw, w, nw)                        
        #rescaled_vertices = rescale_positions(vertices, main_cog.tile_bounds, flip_y=False)
        #quantized = quantize(rescaled_vertices, triangles, normals)
        
        # remesh neighbours
        n_v, n_t, n_n = self._remesh(n, e=ne, se=e, s=main_cog, sw=w, w=nw)
        ne_v, ne_t, ne_n = self._remesh(ne, s=e, sw=main_cog, w=n)
        e_v, e_t, e_n = self._remesh(e, n=ne, s=se, sw=s, w=main_cog, nw=n)
        se_v, se_t, se_n = self._remesh(se, n=e, nw=main_cog, w=s)
        s_v, s_t, s_n = self._remesh(s, e=se, ne=e, n=main_cog, nw=w, w=sw)
        sw_v, sw_t, sw_n = self._remesh(sw, e=s, ne=main_cog, n=w)
        w_v, w_t, w_n = self._remesh(w, s=sw, se=s, e=main_cog, ne=n, n=nw)
        nw_v, nw_t, nw_n = self._remesh(nw, s=w, e=n, se=main_cog)
        main_v, main_t, main_n = self._remesh(main_cog, n=n, ne=ne, e=e, se=se, s=s, sw=sw, w=w, nw=nw)
 
        neighbour_vertices = self._get_neighbour_transformed_edge_vertices_from_array(n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v)
        
        if neighbour_vertices is not None:    
               
            if terrain_request.generate_normals:
                neighbour_normals = self._get_neighbour_normals_from_array(n_v, n_n, ne_v, ne_n, e_v, e_n, se_v, se_n, s_v, s_n, sw_v, sw_n, w_v, w_n, nw_v, nw_n)
            
            # for all vertices check if there are neighbour vertices based on x and y coordinate and average the z coordinate
            for i, vertice in enumerate(main_v):
                duplicated_vertices = neighbour_vertices[
                    (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
                ]
                
                # add the main vertice to the duplicated vertices
                duplicated_vertices = np.concatenate((duplicated_vertices, vertice.reshape(1, 3)), axis=0)
                
                if len(duplicated_vertices) > 1:
                    # average the height
                    vertice[2] = np.average(duplicated_vertices[:, 2])
                    
                    # average the normals
                    if terrain_request.generate_normals:                        
                        duplicated_normals = neighbour_normals[
                           (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
                        ]
                        main_n[i] = np.average(np.concatenate((duplicated_normals, main_n[i].reshape(1, 3)), axis=0), axis=0)

        rescaled = rescale_positions(main_v, main_cog.tile_bounds, flip_y=False)
        quantized = quantize(rescaled, main_t, main_n)
        
        #print("%s ms" % ((time.time() - start_time) * 1000))
        
        return quantized

    def _remesh(self, main_cog: CogRequest, n: CogRequest = None, ne: CogRequest = None, e: CogRequest = None, se: CogRequest = None, s: CogRequest = None, sw: CogRequest = None, w: CogRequest = None, nw: CogRequest = None):
        """To get the correct normals and height we first need to remesh the neighbour tiles 
        and recalculate the normals since we introduced new vertices.
        """
        
        if main_cog is None or main_cog.data is None or main_cog.is_out_of_bounds:
            return (None, None, None)
        
        # get the transformed vertices of the neighbouring tiles
        arrays_v = self._get_neighbour_transformed_edge_vertices(n, ne, e, se, s, sw, w, nw)

        # combine tile vertices with arrays_v
        if arrays_v is None:
            vertices = main_cog.processed_data[0]
        else:            
            vertices = np.concatenate((main_cog.processed_data[0], arrays_v), axis=0)
        
        # filter out duplicate vertices ending up with uniques
        vertices = np.unique(vertices, axis=0)
        
        # make our 3d vertices 2d before triangulation
        vertices2d = vertices[:, :2]
        
        # run constrained delaunay triangulation
        triangulation = triangle.triangulate({'vertices': vertices2d, 'segments': [[0, 0], [255, 0], [255, 255], [0, 255], [0, 0]]})
        new_vertices = triangulation['vertices']
        new_triangles = triangulation['triangles']
        
        # We got some new vertices so resample the height and make new_vertices 3d
        height_data_indices = np.floor(vertices2d).astype(int)
        height_data = main_cog.data.data[0][255 - height_data_indices[:, 1], height_data_indices[:, 0]]
        new_vertices = np.column_stack((vertices2d, height_data))
        
        # rescale and create cartesion to calculate normals
        rescaled = rescale_positions(new_vertices, main_cog.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, new_triangles) if main_cog.generate_normals else None
        
        return (new_vertices, new_triangles, normals)

    def _get_neighbour_transformed_edge_vertices_from_array(self, north: np.ndarray, north_east: np.ndarray, east: np.ndarray, south_east: np.ndarray, south: np.ndarray, south_west: np.ndarray, west: np.ndarray, north_west: np.ndarray) -> np.ndarray:
        """Get the neighbouring tile transformed edge vertices

        Returns:
            vertices (ndarray): edge vertices of neighbour transformed to the correct edges of the local tile
        """
        n_v = ne_v = e_v = se_v = s_v = sw_v = w_v = nw_v = None
        
        if north is not None:
            n_v = self._get_transformed_edge_vertices(north, Direction.SOUTH)
        if north_east is not None:
            ne_v = self._get_transformed_edge_vertices(north_east, Direction.SOUTHWEST)
        if east is not None:
            e_v = self._get_transformed_edge_vertices(east, Direction.WEST)            
        if south_east is not None:
            se_v = self._get_transformed_edge_vertices(south_east, Direction.NORTHWEST)       
        if south is not None:
            s_v = self._get_transformed_edge_vertices(south, Direction.NORTH)          
        if south_west is not None:
            sw_v = self._get_transformed_edge_vertices(south_west, Direction.NORTHEAST)             
        if west is not None:
            w_v = self._get_transformed_edge_vertices(west, Direction.EAST)  
        if north_west is not None:
            nw_v = self._get_transformed_edge_vertices(north_west, Direction.SOUTHEAST) 
        
        # concatenate all the vertices and normals
        arrays_v = [n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
        arrays_v = list(filter(lambda x: x is not None, arrays_v))
        
        if len(arrays_v) > 0:
            return np.concatenate(arrays_v, axis=0)
        else:
            return None

    def _get_neighbour_transformed_edge_vertices(self, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest) -> np.ndarray:
        """Get the neighbouring tile transformed edge vertices

        Returns:
            vertices (ndarray): edge vertices of neighbour transformed to the correct edges of the local tile
        """
        n_v = ne_v = e_v = se_v = s_v = sw_v = w_v = nw_v = None
        
        if n is not None and n.data is not None and not n.is_out_of_bounds:
            n_v = self._get_transformed_edge_vertices(n.processed_data[0], Direction.SOUTH)
        if ne is not None and ne.data is not None and not ne.is_out_of_bounds:
            ne_v = self._get_transformed_edge_vertices(ne.processed_data[0], Direction.SOUTHWEST)
        if e is not None and e.data is not None and not e.is_out_of_bounds:
            e_v = self._get_transformed_edge_vertices(e.processed_data[0], Direction.WEST)            
        if se is not None and se.data is not None and not se.is_out_of_bounds:
            se_v = self._get_transformed_edge_vertices(se.processed_data[0], Direction.NORTHWEST)       
        if s is not None and s.data is not None and not s.is_out_of_bounds:
            s_v = self._get_transformed_edge_vertices(s.processed_data[0], Direction.NORTH)          
        if sw is not None and sw.data is not None and not sw.is_out_of_bounds:
            sw_v = self._get_transformed_edge_vertices(sw.processed_data[0], Direction.NORTHEAST)             
        if w is not None and w.data is not None and not w.is_out_of_bounds:
            w_v = self._get_transformed_edge_vertices(w.processed_data[0], Direction.EAST)  
        if nw is not None and nw.data is not None and not nw.is_out_of_bounds:
            nw_v = self._get_transformed_edge_vertices(nw.processed_data[0], Direction.SOUTHEAST) 
        
        # concatenate all the vertices and normals
        arrays_v = [n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
        arrays_v = list(filter(lambda x: x is not None, arrays_v))
        
        if len(arrays_v) > 0:
            return np.concatenate(arrays_v, axis=0)
        else:
            return None
        
    def _get_neighbour_normals_from_array(self, 
                                            north_v: np.ndarray, north_n: np.ndarray, 
                                            north_east_v: np.ndarray, north_east_n: np.ndarray,
                                            east_v: np.ndarray, east_n: np.ndarray,
                                            south_east_v: np.ndarray, south_east_n: np.ndarray,
                                            south_v: np.ndarray, south_n: np.ndarray,
                                            south_west_v: np.ndarray, south_west_n: np.ndarray,
                                            west_v: np.ndarray, west_n: np.ndarray,
                                            north_west_v: np.ndarray, north_west_n: np.ndarray) -> np.ndarray:

        """Get the neighbouring tile normals

        Returns:
            normals (ndarray): normals of neighbour vertices aligned to the neighbour vertice array
        """
        
        n_n = ne_n = e_n = se_n = s_n = sw_n = w_n = nw_n = None
        
        if north_v is not None:
            n_n = self._get_edge_normals(north_v, north_n, Direction.SOUTH)
        if north_east_v is not None:
            ne_n = self._get_edge_normals(north_east_v, north_east_n, Direction.SOUTHWEST)
        if east_v is not None:
            e_n = self._get_edge_normals(east_v, east_n, Direction.WEST)            
        if south_east_v is not None:
            se_n = self._get_edge_normals(south_east_v, south_east_n, Direction.NORTHWEST)       
        if south_v is not None:
            s_n = self._get_edge_normals(south_v, south_n, Direction.NORTH)          
        if south_west_v is not None:
            sw_n = self._get_edge_normals(south_west_v, south_west_n, Direction.NORTHEAST)             
        if west_v is not None:
            w_n = self._get_edge_normals(west_v, west_n, Direction.EAST)  
        if north_west_v is not None:
            nw_n = self._get_edge_normals(north_west_v, north_west_n, Direction.SOUTHEAST) 
        
        # concatenate all the vertices and normals
        arrays_v = [n_n, ne_n, e_n, se_n, s_n, sw_n, w_n, nw_n]
        arrays_v = list(filter(lambda x: x is not None, arrays_v))
        
        if len(arrays_v) > 0:
            return np.concatenate(arrays_v, axis=0)
        else:
            return None
    
    def _get_edge_normals(self, cog_vertices: np.ndarray, cog_normals: np.ndarray, direction: Direction) -> np.ndarray:
        """Get the normals of the edge vertices of the neighbour tile

        Args:
            cog_request (CogRequest): The CogRequest of the neighbour tile
            direction (Direction): What edge to get the normals from

        Returns:
            np.ndarray: The normals of the edge vertices of the neighbour tile
        """
        
        vertices = cog_vertices.copy()
        normals = cog_normals.copy()
        condition = self._get_vertice_condition(vertices, direction)
        
        return normals[condition]
    
    def _get_transformed_edge_vertices(self, vertices, direction: Direction) -> np.ndarray:
        """
        Get edge vertices from a direction and transform them to the correct edge of the local tile
        """

        vertices_copy = vertices.copy()
        condition = self._get_vertice_condition(vertices_copy, direction)
        
        return vertices_copy[condition]
    
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
        elif direction == Direction.NORTHEAST:
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
        
    def triangulate_over_tiles(self, main_cog: CogRequest, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest):
        """
        This is one of multiple solutions to create shared edge vertices for delatin generated cog data.
        
        We virtually create 1 big tile with all available data by transforming neighbouring
        vertices around the main tile we want to generating a mesh for. If we have all vertices
        we filter out duplicates and create a new triangulation over the virtual tile.
        
        We now end up with 1 big mesh where we need to introduce new vertices where the main
        tile edges cut trough the new triangles.
        
        The next step is to gather all vertices on the edge en inside the main tile. We now
        need to do another triangulation.
        
        """
        
        # get the transformed vertices of the neighbouring tiles
        n_v = self.get_transformed_vertices(n, Direction.NORTH)
        ne_v = self.get_transformed_vertices(ne, Direction.NORTHEAST)
        e_v = self.get_transformed_vertices(e, Direction.EAST)
        se_v = self.get_transformed_vertices(se, Direction.SOUTHEAST)
        s_v = self.get_transformed_vertices(s, Direction.SOUTH)
        sw_v = self.get_transformed_vertices(sw, Direction.SOUTHWEST)
        w_v = self.get_transformed_vertices(w, Direction.WEST)
        nw_v = self.get_transformed_vertices(nw, Direction.NORTHWEST)
        
        # concatenate all the vertices for available neighbouring tiles
        arrays_v = [main_cog.processed_data[0], n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
        arrays_v = list(filter(lambda x: x is not None, arrays_v))
        
        # concatenate all the vertices in arrays_v
        vertices = np.concatenate(arrays_v, axis=0)
        
        # filter out duplicate vertices ending up with uniques
        vertices = np.unique(vertices, axis=0)
        
        # make our 3d vertices 2d before triangulation
        vertices = vertices[:, :2]
        
        # run constrained delaunay triangulation so we end up with 1 big mesh
        #triangulation = triangle.triangulate({'vertices': vertices, 'segments': [[0, 0], [255, 0], [255, 255], [0, 255], [0, 0]]})
        triangulation = triangle.triangulate({'vertices': vertices})
        
        # gather all vertices inside the main tile bounds including new vertices
        # where triangle goes over the edge
        bounds = np.array([[0, 0], [255, 0], [255, 255], [0, 255], [0, 0]])
        inside_vertices = self.get_vertices_inside_bounds(triangulation['vertices'], triangulation['triangles'], bounds)
        #print("inside_vertices: %s" % inside_vertices)
        
        # sample height for vertices
        height_data_indices = np.floor(inside_vertices).astype(int)
        height_data = main_cog.data.data[0][255 - height_data_indices[:, 1], height_data_indices[:, 0]]
        vertices_3d = np.column_stack((inside_vertices, height_data))
        
        # create new triangulation for the inside vertices
        triangulation = triangle.triangulate({'vertices': vertices_3d[:, :2], 'segments': [[0, 0], [255, 0], [255, 255], [0, 255], [0, 0]]})
        
        # create normals
        vertices_new = np.array(vertices_3d, dtype=np.float64)
        triangles_new = np.array(triangulation['triangles'], dtype=np.uint16)
        rescaled = rescale_positions(vertices_new, main_cog.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, triangles_new) if main_cog.generate_normals else None
        
        # quantize
        quantized = quantize(rescaled, triangles_new, normals)
        
        return quantized

    def get_vertices_inside_bounds(self, vertices, triangles, tile_bounds):
        """Function to get vertices inside bounds and generate vertices for overlapping triangles"""
        
        # Find vertices inside or touching the north_tile_bounds
        inside_vertices = []

        for point in vertices:
            if np.all((point >= np.min(tile_bounds, axis=0)) & (point <= np.max(tile_bounds, axis=0))):
                inside_vertices.append(point)

        inside_vertices = np.array(inside_vertices)
        bounds_geom = LineString(tile_bounds)

        # Find and add vertices where triangles intersect with bounds
        for triangle_indices in triangles:
            triangle_vertices = vertices[triangle_indices]
            # close triangle
            triangle_vertices = np.append(triangle_vertices, [triangle_vertices[0]], axis=0)
            triangle_line = LineString(triangle_vertices)

            intersection_geometry = triangle_line.intersection(bounds_geom)

            if intersection_geometry.is_empty:
                continue
            elif isinstance(intersection_geometry, GeometryCollection):
                # Handle GeometryCollection
                for geom in intersection_geometry.geoms:
                    inside_vertices = np.vstack([inside_vertices, self.extract_coords(geom)])
            else:
                # Handle individual geometries
                inside_vertices = np.vstack([inside_vertices, self.extract_coords(intersection_geometry)])

        # Remove duplicates from inside_vertices
        inside_vertices = np.unique(inside_vertices, axis=0)
        return inside_vertices

    def extract_coords(self, geometry):
        """function to get the coordinates of a shapely geometry"""
        
        if isinstance(geometry, Point):
            return np.array([list(geometry.coords)[0]])
        elif isinstance(geometry, LineString):
            return np.array(list(geometry.coords))
        elif isinstance(geometry, MultiPoint):
            return np.array([list(point.coords)[0] for point in geometry.geoms])
        elif isinstance(geometry, MultiLineString):
            return np.vstack([list(line.coords) for line in geometry.geoms])
        else:
            raise ValueError("Unhandled geometry type:", type(geometry))
    
    def get_transformed_vertices(self, cog_request: CogRequest, direction) -> np.ndarray:
        """Get the transformed vertices of a neighbouring tile"""
        
        if cog_request is None or cog_request.processed_data is None:
            return None
        
        vertices = cog_request.processed_data[0].copy()        
        tile_size = 255 
        
        if direction == Direction.NORTH:
            vertices[:, 1] += tile_size
        elif direction == Direction.NORTHEAST:
            vertices[:, 0] += tile_size
            vertices[:, 1] += tile_size         
        elif direction == Direction.NORTHWEST:
            vertices[:, 0] -= tile_size            
            vertices[:, 1] += tile_size
        elif direction == Direction.EAST:
            vertices[:, 0] += tile_size
        elif direction == Direction.SOUTHEAST:
            vertices[:, 0] += tile_size
            vertices[:, 1] -= tile_size
        elif direction == Direction.SOUTH:
            vertices[:, 1] -= tile_size
        elif direction == Direction.SOUTHWEST:
            vertices[:, 0] -= tile_size
            vertices[:, 1] -= tile_size
        elif direction == Direction.WEST:
            vertices[:, 0] -= tile_size
        
        return vertices
        
