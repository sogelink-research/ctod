import logging
import quantized_mesh_encoder.occlusion

from ctod.core.math import compute_magnitude


def patch_occlusion():
    """monkey patch quantized_mesh_encoder.occlusion with our own compute_magnitude"""

    quantized_mesh_encoder.occlusion.compute_magnitude = compute_magnitude


def setup_logging(log_level=logging.INFO):
    """Set up logging for the application."""

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.disabled = True

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()],
    )


def log_ctod_start(port: int, tile_cache_path: str):
    """Log message when starting the service

    Args:
        port (int): Port the service is running on
        tile_cache_path (str): Path to the tile cache
    """

    logging.info("-----------------------")
    logging.info(f"CTOD Started")
    logging.info("-----------------------")
    logging.info(f"Port: {port}")
    logging.info(f"Caching: {'enabled' if tile_cache_path else 'disabled'}")
    if tile_cache_path:
        logging.info(f"Caching Path: {tile_cache_path}")
    logging.info("-----------------------")
