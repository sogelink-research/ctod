from ctod.core import utils
from ctod.handlers.base import BaseHandler
from ctod.core.layer import generate_layer_json


class LayerJsonHandler(BaseHandler):
    """Request handler for layer.json"""
    
    def get(self):
        """Generate and return a layer.json based on the COG"""
        
        tms = utils.get_tms()
        max_zoom = self.get_max_zoom()
        cog = self.get_cog()        
        json_data = generate_layer_json(tms, cog, max_zoom)
        
        self.set_header('Content-Type', 'application/json')
        self.set_header('Content-Disposition', 'attachment; filename=layer.json')
        self.write(json_data)