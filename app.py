import argparse
import logging
import os
import tornado.ioloop

from ctod.server import make_server


def main():
    # Parse command line arguments and environment variables
    args = _parse_args()
    port = _get_value(args.port, int(os.environ.get('CTOD_PORT', 5000)), 5000)
    tile_cache_path = _get_value(args.tile_cache_path, os.environ.get('CTOD_TILE_CACHE_PATH', None), None)
    logging_level = _get_value(args.logging_level, os.environ.get('CTOD_LOGGING_LEVEL', 'info'), 'info')

    # Setup logging
    _setup_logging(log_level=getattr(logging, logging_level.upper()))

    # Set up asyncio event loop integration with Tornado
    #AsyncIOMainLoop().install()

    # Create the Tornado application using the make_server function from server.py
    app = make_server(tile_cache_path)
    app.listen(port)
    
    _log_ctod_start(port, tile_cache_path)
    
    tornado.ioloop.IOLoop.current().start()

def _parse_args():
    parser = argparse.ArgumentParser(description="CTOD Application")
    parser.add_argument('--tile-cache-path', help="Path to the tile cache")
    parser.add_argument('--logging-level', choices=['debug', 'info', 'warning', 'error', 'critical'],
                        default='info', help="Logging level")
    parser.add_argument('--port', type=int, default=5000, help="Port to run the application on")
    return parser.parse_args()

def _get_value(command_line, environment, default):
    return command_line if command_line is not None else environment if environment is not None else default

def _log_ctod_start(port: int, tile_cache_path: str):
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
    
def _setup_logging(log_level=logging.INFO):
    """Set up logging for the application."""
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

if __name__ == "__main__":
    main()