import numpy as np


def calculate_normals(vertices: np.ndarray, triangles:  np.ndarray) -> np.ndarray:
    """Calculate vertex normals for a quantized mesh tile

    Args:
        vertices (np.ndarray): List of vertices
        triangles (np.ndarray): List of triangle indices

    Returns:
        np.ndarray: list of vertex normals
    """
    
    # Make sure indices and positions are both arrays of shape (-1, 3)
    vertices = vertices.reshape(-1, 3).astype('float64')
    triangles = triangles.reshape(-1, 3)

    # Perform coordinate lookup in positions using indices
    tri_coords = vertices[triangles]

    a = tri_coords[:, 0, :]
    b = tri_coords[:, 1, :]
    c = tri_coords[:, 2, :]

    # Compute face normals for each triangle
    face_normals = np.cross(b - a, c - a)
    
    # Compute the area of each triangle using the face normals
    tri_areas = 0.5 * np.linalg.norm(face_normals, axis=1)

    # Weight each face normal by the area of the corresponding triangle
    weighted_face_normals = tri_areas[:, np.newaxis] * face_normals

    # Sum up each vertex normal
    vertex_normals = np.zeros(vertices.shape, dtype=np.float64)
    __add_vertex_normals(triangles, weighted_face_normals, vertex_normals)

    # Normalize vertex normals by dividing by each vector's length
    norm_lengths = np.linalg.norm(vertex_normals, axis=1)
    tolerance = 1e-8
    nonzero_indices = norm_lengths > tolerance
    vertex_normals[nonzero_indices] /= norm_lengths[nonzero_indices][:, np.newaxis]
            
    return vertex_normals

def generate_geodetic_normals(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Generate geocentric normals for a quantized mesh tile

    Args:
        vertices (np.ndarray): list of vertices in ecef
        triangles (np.ndarray): list of triangle indices

    Returns:
        np.ndarray: list of geocentric normals
    """
    
    vertices = vertices.reshape(-1, 3).astype('float64')
    triangles = triangles.reshape(-1, 3)
    
    vertex_normals = np.zeros(vertices.shape, dtype=np.float64)
 
    for i, values in enumerate(vertices):        
        gradient = np.array([values[0], values[1], values[2]])
        normal = gradient / np.linalg.norm(gradient)
        vertex_normals[i] = normal
    
    return vertex_normals

def __add_vertex_normals(indices: np.ndarray, weighted_face_normals: np.ndarray, vertex_normals: np.ndarray):
    """Add the weighted face normals to the corresponding vertex normals"""
    
    # Iterate over each triangle
    for i in range(indices.shape[0]):
        # Iterate over each vertex in the triangle
        for j in range(3):
            # Get the index of the vertex
            vertex_index = indices[i, j]

            # Add the weighted face normal to the corresponding vertex normal
            vertex_normals[vertex_index] += weighted_face_normals[i]