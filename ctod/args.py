import argparse

def parse_args():
    try:
        parser = argparse.ArgumentParser(description="CTOD Application")
        parser.add_argument("--tile-cache-path", help="Path to the tile cache")
        parser.add_argument(
            "--logging-level",
            choices=["debug", "info", "warning", "error", "critical"],
            default="info",
            help="Logging level",
        )
        parser.add_argument(
            "--port", type=int, default=5000, help="Port to run the application on"
        )
        parser.add_argument(
            "--dev",
            action="store_true",
            help="Start in dev mode",
        )
        parser.add_argument(
            "--unsafe",
            action="store_true",
            help="When unsafe all tiles will be loaded, even if there are not enough overviews",
        )

        return parser.parse_args()
    except:
        return None
        


def get_value(args, option, environment, default):
    return (
        getattr(args, option)
        if args is not None and hasattr(args, option) and getattr(args, option) is not None
        else environment if environment is not None else default
    )