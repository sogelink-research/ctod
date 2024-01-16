import math
import numpy as np

from quantized_mesh_encoder.occlusion import squared_norm

def geodetic_surface_normal(lon: float, lat: float) -> tuple:
    """Calculate the geodetic surface normal for a given lon/lat

    Args:
        lon (float): longitude
        lat (float): latitude

    Returns:
        tuple: geodetic surface normal
    """
    
    cos_latitude = math.cos(lat)
    return cos_latitude * math.cos(lon), cos_latitude * math.sin(lon), math.sin(lat)

def compute_magnitude(positions: np.ndarray, bounding_center: np.ndarray) -> np.ndarray:
    magnitude_squared = squared_norm(positions)
    magnitude = np.sqrt(magnitude_squared)

    # Can make this cleaner by broadcasting division
    direction = positions.copy()
    direction[:, 0] /= magnitude
    direction[:, 1] /= magnitude
    direction[:, 2] /= magnitude

    magnitude_squared = np.maximum(magnitude_squared, 1)
    magnitude = np.maximum(magnitude, 1)

    cos_alpha = np.dot(direction, bounding_center.T)
    sin_alpha = np.linalg.norm(np.cross(direction, bounding_center), axis=1)
    cos_beta = 1 / magnitude
    sin_beta = np.sqrt(magnitude_squared - 1.0) * cos_beta

    denominator = cos_alpha * cos_beta - sin_alpha * sin_beta

    # Check for zero denominator
    denominator[denominator == 0] = np.finfo(float).eps

    return 1 / denominator