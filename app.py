import asyncio
import os
import logging
import quantized_mesh_encoder.occlusion

from ctod.args import parse_args, get_value
from ctod.core.math import compute_magnitude
from uvicorn import Config, Server


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


async def main():
    args = parse_args()
    port = get_value(args, "port", int(os.environ.get("CTOD_PORT", 5000)), 5000)
    tile_cache_path = get_value(
        args, "tile_cache_path", os.environ.get("CTOD_TILE_CACHE_PATH", None), None
    )
    logging_level = get_value(
        args, "logging_level", os.environ.get("CTOD_LOGGING_LEVEL", "info"), "info"
    )

    patch_occlusion()
    setup_logging(log_level=getattr(logging, logging_level.upper()))
    log_ctod_start(port, tile_cache_path)

    config = Config(
        "ctod.server.server:app",
        host="0.0.0.0",
        port=port,
        log_config=None,
        reload=False,
        workers=1,
    )
    server = Server(config)

    await asyncio.create_task(server.serve())


if __name__ == "__main__":
    asyncio.run(main())
