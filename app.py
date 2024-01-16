import sys
import tornado.ioloop

from tornado.platform.asyncio import AsyncIOMainLoop
from ctod.server import make_server


def main():
    tile_cache_path = None
    if len(sys.argv) > 1:
        tile_cache_path = sys.argv[1]
        
    # Set up asyncio event loop integration with Tornado
    AsyncIOMainLoop().install()

    # Create the Tornado application using the make_server function from server.py
    app = make_server(tile_cache_path)

    # Start the Tornado application
    app.listen(5000)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()