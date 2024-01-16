from ctod.handlers.base import BaseHandler


class IndexHandler(BaseHandler):
    """Request handler for the index page"""

    def get(self):
        """Render the index.html template with a basic Cesium viewer"""
        
        self.render('index.html')
