from tornado import web

class BaseHandler(web.RequestHandler):
    """The base handler for all requests
    Make sure we don't have problems with CORS by allowing all origins
    """
    
    def set_default_headers(self):
        """Set the default headers for all requests"""
        
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, content-type")
        
    def get_min_zoom(self) -> int:
        """Get the minimum zoom level from the request

        Returns:
            min_zoom (int): The minimum zoom level. Defaults to 1
        """
        
        min_zoom = int(self.get_argument("minZoom", default=1))

        if min_zoom < 1:
            min_zoom = 1
            
        return min_zoom

    def get_max_zoom(self) -> int:
        """Get the maximum zoom level from the request

        Returns:
            max_zoom (int): The maximum zoom level. Defaults to 21
        """
        
        return int(self.get_argument("maxZoom", default=21))

    def get_resampling_method(self) -> str:
        """Get the resampling method from the request

        Returns:
            resampling_method (str): COG resampling method. Defaults to bilinear
        """
        
        return self.get_argument("resamplingMethod", default="bilinear")
    
    def get_cog(self) -> str:
        """Get the COG path from the request

        Returns:
            str: The COG path. Defaults to ./ctod/files/test_cog.tif
        """
        
        return self.get_argument("cog", default="./ctod/files/test_cog.tif")

    def get_meshing_method(self) -> str:
        """Get the method used for meshing

        Returns:
            str: The meshing method. Defaults grid
        """
        
        return self.get_argument("meshingMethod", default="grid")
    
    def get_skip_cache(self) -> str:
        """Get if the cache should be skipped

        Returns:
            bool: True if the cache should be skipped, False otherwise
        """
        
        return self.get_argument("skipCache", default=False)
    
    def get_extensions(self) -> str:
        """Get the accept header from the request

        Returns:
            str: The accept header. Defaults to image/png
        """
        
       
        extensions = self._check_extensions(["octvertexnormals", "watermask", "metadata"])

        return extensions

    def _check_extensions(self, extensions_to_check: list) -> dict:
        """Check the extensions in the accept header

        Args:
            extensions_to_check (list): list of extensions to check

        Returns:
            dict: extensions found in the accept header
        """

        accept_header = self.request.headers.get('Accept')
        content_types = accept_header.split(',')

        found_extensions = {}
        for extension in extensions_to_check:
            found_extensions[extension] = False

        for content_type in content_types:
            if 'extensions=' in content_type:
                for part in content_type.split(';'):
                    if 'extensions=' in part:
                        extension = part.split('=')[1]
                        if extension in extensions_to_check:
                            found_extensions[extension] = True

        return found_extensions
