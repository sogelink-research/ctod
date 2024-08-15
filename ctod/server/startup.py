import logging
import quantized_mesh_encoder.occlusion

from ctod.core.math import compute_magnitude
from ctod.server.settings import Settings


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


def log_ctod_start(settings: Settings):
    """Log message when starting the service

    Args:
        settings (Settings): CTOD settings loaded from args or environment variables
    """

    logging.info("-----------------------")
    logging.info(f"CTOD Started")
    logging.info("-----------------------")
    logging.info(f"Port:\t\t {settings.port}")
    logging.info(
        f"Caching:\t\t {'enabled' if settings.tile_cache_path else 'disabled'}")
    if settings.tile_cache_path:
        logging.info(f"Caching Path:\t {settings.tile_cache_path}")
    logging.info(f"Dataset Config:\t {settings.dataset_config_path}")
    logging.info(f"Logging Level:\t {settings.logging_level}")
    logging.info(f"DB Name:\t\t {settings.db_name}")
    logging.info(f"Dev Mode:\t\t {settings.dev}")
    logging.info(f"Unsafe:\t\t {settings.unsafe}")
    logging.info(f"No Dynamic:\t\t {settings.no_dynamic}")
    logging.info("-----------------------")
