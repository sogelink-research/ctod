import os
import uvicorn
from ctod.args import parse_args, get_value


def get_port() -> int:
    args = parse_args()
    port = get_value(args, "port", int(os.environ.get("CTOD_PORT", 5000)), 5000)

    return port


def main():
    uvicorn.run(
        "ctod.server.fastapi:app",
        host="0.0.0.0",
        port=get_port(),
        log_config=None,
        workers=1,
    )


def main_dev():
    uvicorn.run(
        "ctod.server.fastapi:app",
        host="0.0.0.0",
        port=get_port(),
        reload=True,
        workers=1,
    )

if __name__ == "__main__":
    main()