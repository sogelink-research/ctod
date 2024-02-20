import argparse

def parse_args():
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


def get_value(command_line, environment, default):
    return (
        command_line
        if command_line is not None
        else environment if environment is not None else default
    )