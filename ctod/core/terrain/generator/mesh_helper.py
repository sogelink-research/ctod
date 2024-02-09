import numpy as np
import triangle

from ctod.core.cog.cog_request import CogRequest
from ctod.core.direction import Direction
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions
from quantized_mesh_encoder.ecef import to_ecef


def get_neighbor_files(terrain_request: TerrainRequest):
    """
    Get the neighbor files for the given terrain request.

    Args:
        terrain_request (TerrainRequest): The terrain request object.

    Returns:
        Tuple[str]: A tuple containing the neighbor file paths in the order of [n, ne, e, se, s, sw, w, nw].
    """
    
    n = terrain_request.get_neighbour_file(Direction.NORTH)
    ne = terrain_request.get_neighbour_file(Direction.NORTHEAST)
    e = terrain_request.get_neighbour_file(Direction.EAST)
    se = terrain_request.get_neighbour_file(Direction.SOUTHEAST)
    s = terrain_request.get_neighbour_file(Direction.SOUTH)
    sw = terrain_request.get_neighbour_file(Direction.SOUTHWEST)
    w = terrain_request.get_neighbour_file(Direction.WEST)
    nw = terrain_request.get_neighbour_file(Direction.NORTHWEST)

    return n, ne, e, se, s, sw, w, nw

def average_height_and_normals_to_neighbours(vertices: np.ndarray, normals: np.ndarray, neighbour_vertices: np.ndarray, neighbour_normals: np.ndarray):
    """
    Calculates the average height and normals to the neighbouring vertices.

    Args:
        vertices (np.ndarray): Array of vertices.
        normals (np.ndarray): Array of normals.
        neighbour_vertices (np.ndarray): Array of neighbouring vertices.
        neighbour_normals (np.ndarray): Array of neighbouring normals.

    Returns:
        None, in place operation.
    """
    
    if neighbour_vertices is not None:
        # for all vertices check if there are neighbour vertices based on x and y coordinate and average the z coordinate
        for i, vertice in enumerate(vertices):
            duplicated_vertices = neighbour_vertices[
                (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
            ]
            duplicated_vertices = np.concatenate((duplicated_vertices, vertice.reshape(1, 3)), axis=0)
            
            if len(duplicated_vertices) > 1:
                # average the height
                vertice[2] = np.average(duplicated_vertices[:, 2])
                
                # average the normals
                if neighbour_normals is not None:                        
                    duplicated_normals = neighbour_normals[
                        (neighbour_vertices[:, 0] == vertice[0]) & (neighbour_vertices[:, 1] == vertice[1])
                    ]
                    normals[i] = np.average(np.concatenate((duplicated_normals, normals[i].reshape(1, 3)), axis=0), axis=0)

                  
def merge_shared_vertices(tile_size: int, main_cog: CogRequest, n: CogRequest = None, ne: CogRequest = None, e: CogRequest = None, se: CogRequest = None, s: CogRequest = None, sw: CogRequest = None, w: CogRequest = None, nw: CogRequest = None):
    """
    Merge shared vertices from neighboring tiles and remesh using constrained delaunay 
    triangulation and recalculation of normals.

    Args:
        tile_size (int): The size of the tile.
        main_cog (CogRequest): The main tile containing the vertices.
        n (CogRequest, optional): The neighboring tile to the north. Defaults to None.
        ne (CogRequest, optional): The neighboring tile to the northeast. Defaults to None.
        e (CogRequest, optional): The neighboring tile to the east. Defaults to None.
        se (CogRequest, optional): The neighboring tile to the southeast. Defaults to None.
        s (CogRequest, optional): The neighboring tile to the south. Defaults to None.
        sw (CogRequest, optional): The neighboring tile to the southwest. Defaults to None.
        w (CogRequest, optional): The neighboring tile to the west. Defaults to None.
        nw (CogRequest, optional): The neighboring tile to the northwest. Defaults to None.

    Returns:
        tuple: A tuple containing the new vertices, new triangles, and normals (if generated).
    """
    
    if main_cog is None or main_cog.data is None or main_cog.is_out_of_bounds:
        return (None, None, None)
    
    # get the transformed vertices of the neighbouring tiles
    arrays_v = get_neighbour_transformed_edge_vertices(tile_size, n, ne, e, se, s, sw, w, nw)

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
    triangulation = triangle.triangulate({'vertices': vertices2d})
    new_vertices = triangulation['vertices']
    new_triangles = triangulation['triangles']
    
    # We got some new vertices , resample the height and make make vertices 3d
    height_data_indices = np.floor(vertices2d).astype(int)
    
    height_data = main_cog.data.data[0][tile_size - height_data_indices[:, 1], height_data_indices[:, 0]]
    new_vertices = np.column_stack((vertices2d, height_data))
    
    # rescale and create cartesian to calculate normals
    rescaled = rescale_positions(new_vertices, main_cog.tile_bounds, flip_y=False)
    cartesian = to_ecef(rescaled)
    normals = calculate_normals(cartesian, new_triangles) if main_cog.generate_normals else None
    
    return (new_vertices, new_triangles, normals)

def get_neighbour_transformed_edge_vertices_from_array(tile_size: int, north: np.ndarray, north_east: np.ndarray, east: np.ndarray, south_east: np.ndarray, south: np.ndarray, south_west: np.ndarray, west: np.ndarray, north_west: np.ndarray) -> np.ndarray:
    """
    Get edge vertices from all neighbouring tiles and transform them to the correct edge of the local tile

    Args:
        tile_size (int): The size of the tile.
        north (np.ndarray): The vertices of the northern tile.
        north_east (np.ndarray): The vertices of the northeastern tile.
        east (np.ndarray): The vertices of the eastern tile.
        south_east (np.ndarray): The vertices of the southeastern tile.
        south (np.ndarray): The vertices of the southern tile.
        south_west (np.ndarray): The vertices of the southwestern tile.
        west (np.ndarray): The vertices of the western tile.
        north_west (np.ndarray): The vertices of the northwestern tile.

    Returns:
        np.ndarray: The concatenated array of transformed edge vertices.
    """
    
    n_v = ne_v = e_v = se_v = s_v = sw_v = w_v = nw_v = None
    
    if north is not None:
        n_v = get_transformed_edge_vertices(north, Direction.SOUTH, tile_size)
    if north_east is not None:
        ne_v = get_transformed_edge_vertices(north_east, Direction.SOUTHWEST, tile_size)
    if east is not None:
        e_v = get_transformed_edge_vertices(east, Direction.WEST, tile_size)            
    if south_east is not None:
        se_v = get_transformed_edge_vertices(south_east, Direction.NORTHWEST, tile_size)       
    if south is not None:
        s_v = get_transformed_edge_vertices(south, Direction.NORTH, tile_size)          
    if south_west is not None:
        sw_v = get_transformed_edge_vertices(south_west, Direction.NORTHEAST, tile_size)             
    if west is not None:
        w_v = get_transformed_edge_vertices(west, Direction.EAST, tile_size)  
    if north_west is not None:
        nw_v = get_transformed_edge_vertices(north_west, Direction.SOUTHEAST, tile_size) 
    
    # concatenate all the vertices and normals when available
    arrays_v = [n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
    arrays_v = list(filter(lambda x: x is not None, arrays_v))
    
    if len(arrays_v) > 0:
        return np.concatenate(arrays_v, axis=0)
    else:
        return None

def get_neighbour_transformed_edge_vertices(tile_size: int, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest) -> np.ndarray:
    """
    Get the transformed edge vertices from the neighboring tiles.

    Args:
        tile_size (int): The size of the tile.
        n (CogRequest): The north neighboring tile.
        ne (CogRequest): The northeast neighboring tile.
        e (CogRequest): The east neighboring tile.
        se (CogRequest): The southeast neighboring tile.
        s (CogRequest): The south neighboring tile.
        sw (CogRequest): The southwest neighboring tile.
        w (CogRequest): The west neighboring tile.
        nw (CogRequest): The northwest neighboring tile.

    Returns:
        np.ndarray: The concatenated array of transformed edge vertices.
    """
    n_v = ne_v = e_v = se_v = s_v = sw_v = w_v = nw_v = None
    
    if n is not None and n.data is not None and not n.is_out_of_bounds:
        n_v = get_transformed_edge_vertices(n.processed_data[0], Direction.SOUTH, tile_size)
    if ne is not None and ne.data is not None and not ne.is_out_of_bounds:
        ne_v = get_transformed_edge_vertices(ne.processed_data[0], Direction.SOUTHWEST, tile_size)
    if e is not None and e.data is not None and not e.is_out_of_bounds:
        e_v = get_transformed_edge_vertices(e.processed_data[0], Direction.WEST, tile_size)            
    if se is not None and se.data is not None and not se.is_out_of_bounds:
        se_v = get_transformed_edge_vertices(se.processed_data[0], Direction.NORTHWEST, tile_size)       
    if s is not None and s.data is not None and not s.is_out_of_bounds:
        s_v = get_transformed_edge_vertices(s.processed_data[0], Direction.NORTH, tile_size)          
    if sw is not None and sw.data is not None and not sw.is_out_of_bounds:
        sw_v = get_transformed_edge_vertices(sw.processed_data[0], Direction.NORTHEAST, tile_size)             
    if w is not None and w.data is not None and not w.is_out_of_bounds:
        w_v = get_transformed_edge_vertices(w.processed_data[0], Direction.EAST, tile_size)  
    if nw is not None and nw.data is not None and not nw.is_out_of_bounds:
        nw_v = get_transformed_edge_vertices(nw.processed_data[0], Direction.SOUTHEAST, tile_size) 
    
    # concatenate all the vertices and normals
    arrays_v = [n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v]
    arrays_v = list(filter(lambda x: x is not None, arrays_v))
    
    if len(arrays_v) > 0:
        return np.concatenate(arrays_v, axis=0)
    else:
        return None

def get_neighbour_normals(tile_size: int, n: CogRequest, ne: CogRequest, e: CogRequest, se: CogRequest, s: CogRequest, sw: CogRequest, w: CogRequest, nw: CogRequest) -> np.ndarray:
    """Get the neighbouring tile normals

    Returns:
        normals (ndarray): normals of neighbour vertices aligned to the neighbour vertice array
    """
    n_v = ne_v = e_v = se_v = s_v = sw_v = w_v = nw_v = None
    n_n = ne_n = e_n = se_n = s_n = sw_n = w_n = nw_n = None
    
    if n is not None and n.data is not None and not n.is_out_of_bounds:
        n_v = n.processed_data[0]
        n_n = n.processed_data[2]
    if ne is not None and ne.data is not None and not ne.is_out_of_bounds:
        ne_v = ne.processed_data[0]
        ne_n = ne.processed_data[2]
    if e is not None and e.data is not None and not e.is_out_of_bounds:
        e_v = e.processed_data[0]
        e_n = e.processed_data[2]
    if se is not None and se.data is not None and not se.is_out_of_bounds:
        se_v = se.processed_data[0]
        se_n = se.processed_data[2]
    if s is not None and s.data is not None and not s.is_out_of_bounds:
        s_v = s.processed_data[0]
        s_n = s.processed_data[2]
    if sw is not None and sw.data is not None and not sw.is_out_of_bounds:
        sw_v = sw.processed_data[0]
        sw_n = sw.processed_data[2]
    if w is not None and w.data is not None and not w.is_out_of_bounds:
        w_v = w.processed_data[0]
        w_n = w.processed_data[2]
    if nw is not None and nw.data is not None and not nw.is_out_of_bounds:
        nw_v = nw.processed_data[0]
        nw_n = nw.processed_data[2]    
    
    return get_neighbour_normals_from_array(tile_size, n_v, n_n, ne_v, ne_n, e_v, e_n, se_v, se_n, s_v, s_n, sw_v, sw_n, w_v, w_n, nw_v, nw_n)

def get_neighbour_normals_from_array(tile_size: int, 
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
        n_n = get_edge_normals(north_v, north_n, Direction.SOUTH, tile_size)
    if north_east_v is not None:
        ne_n = get_edge_normals(north_east_v, north_east_n, Direction.SOUTHWEST, tile_size)
    if east_v is not None:
        e_n = get_edge_normals(east_v, east_n, Direction.WEST, tile_size)            
    if south_east_v is not None:
        se_n = get_edge_normals(south_east_v, south_east_n, Direction.NORTHWEST, tile_size)       
    if south_v is not None:
        s_n = get_edge_normals(south_v, south_n, Direction.NORTH, tile_size)          
    if south_west_v is not None:
        sw_n = get_edge_normals(south_west_v, south_west_n, Direction.NORTHEAST, tile_size)             
    if west_v is not None:
        w_n = get_edge_normals(west_v, west_n, Direction.EAST, tile_size)  
    if north_west_v is not None:
        nw_n = get_edge_normals(north_west_v, north_west_n, Direction.SOUTHEAST, tile_size) 
    
    # concatenate all the vertices and normals
    arrays_v = [n_n, ne_n, e_n, se_n, s_n, sw_n, w_n, nw_n]
    arrays_v = list(filter(lambda x: x is not None, arrays_v))
    
    if len(arrays_v) > 0:
        return np.concatenate(arrays_v, axis=0)
    else:
        return None

def get_edge_normals(cog_vertices: np.ndarray, cog_normals: np.ndarray, direction: Direction, tile_size) -> np.ndarray:
    """Get the normals of the edge vertices

    Args:
        cog_request (CogRequest): The CogRequest
        direction (Direction): What edge to get the normals from

    Returns:
        np.ndarray: The normals of the edge vertices
    """
    
    vertices = cog_vertices.copy()
    normals = cog_normals.copy()
    condition = get_vertice_condition(vertices, direction, tile_size)
    
    return normals[condition]

def get_transformed_edge_vertices(vertices, direction: Direction, tile_size) -> np.ndarray:
    """Get edge vertices from a direction and transform them to the correct edge of the local tile
    """

    vertices_copy = vertices.copy()
    condition = get_vertice_condition(vertices_copy, direction, tile_size)
    
    return vertices_copy[condition]

def get_vertice_condition(vertices, direction, tile_size) -> np.ndarray:
    """Based on vertices and an edge direction return a condition on what vertices to select

    Args:
        vertices (ndarray): vertices of a processed cog
        direction (Direction): direction to select the vertices

    Raises:
        ValueError: Invalid direction

    Returns:
        np.ndarray: Condition on what vertices to select
    """

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
