import uvicorn

from ctod.server.settings import Settings


def get_port() -> int:
    settings = Settings()
    port = settings.port

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
