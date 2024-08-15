import os
import argparse


class Settings:
    """
    Class representing the settings for the CTOD application.

    Args:
        args (argparse.Namespace, optional): Command-line arguments. If not provided, the arguments will be parsed from the command line.
    """

    def __init__(self, args=None):
        # If args is not provided, parse from command line
        if args is None:
            parser = argparse.ArgumentParser(description="CTOD Application")
            parser.add_argument("--tile-cache-path",
                                help="Path to the tile cache")
            parser.add_argument(
                "--dataset-config-path", help="Path to the dataset config, default ./config/datasets.json")
            parser.add_argument("--logging-level", choices=[
                                "debug", "info", "warning", "error", "critical"], help="Logging level")
            parser.add_argument("--db-name", help="Name of the caching db")
            parser.add_argument("--port", help="Port to run the application o")
            parser.add_argument("--dev", action="store_true",
                                help="Start in dev mode")
            parser.add_argument("--unsafe", action="store_true",
                                help="When unsafe all tiles will be loaded, even if there are not enough overviews")
            parser.add_argument("--no-dynamic", action="store_true",
                                help="Disable the endpoints for dynamic terrain based on query parameters")
            args = parser.parse_args()

        # Get values from command-line arguments or environment variables
        self.tile_cache_path = args.tile_cache_path or os.getenv(
            "CTOD_TILE_CACHE_PATH", None)
        self.dataset_config_path = args.dataset_config_path or os.getenv(
            "CTOD_DATASET_CONFIG_PATH", "./config/datasets.json")
        self.logging_level = args.logging_level or os.getenv(
            "CTOD_LOGGING_LEVEL", "info")
        self.db_name = args.db_name or os.getenv(
            "CTOD_DB_NAME", "factory_cache.db")
        self.port = args.port or int(os.getenv("CTOD_PORT", 5000))

        # Handle boolean flags
        self.dev = args.dev if args.dev else os.getenv(
            "CTOD_DEV", "False").lower() in ("true", "1", "t")
        self.unsafe = args.unsafe if args.unsafe else os.getenv(
            "CTOD_UNSAFE", "False").lower() in ("true", "1", "t")
        self.no_dynamic = args.no_dynamic if args.no_dynamic else os.getenv(
            "CTOD_NO_DYNAMIC", "False").lower() in ("true", "1", "t")
        self.factory_cache_ttl = 15
