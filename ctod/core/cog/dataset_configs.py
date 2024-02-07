import copy
import json
import os
import requests
import logging

from ctod.core.utils import get_dataset_type
from urllib.parse import urlparse, urljoin
from lxml import etree

class DatasetConfigs:
    """
    ToDo: Make classes for config and add error checking
    """
    
    def __init__(self):
        self.cached_configs = {}
        
    def get_config(self, dataset_path: str):
        if dataset_path not in self.cached_configs:
            config = self._create_config(dataset_path)
            self.cached_configs[dataset_path] = config           
        
        return copy.deepcopy(self.cached_configs[dataset_path])
    
    def _create_config(self, dataset_path: str):
        type = get_dataset_type(dataset_path)
        if type == "mosaic":
            return self._create_mosaic_config(dataset_path)
        elif type == "vrt":
            return self._create_vrt_config(dataset_path)
        else:
            return self._create_default_config(dataset_path)
        
    def _create_default_config(self, dataset_path: str):
        return { "type": "cog", "path": dataset_path }

    def _create_vrt_config(self, dataset_path: str):
        if dataset_path.startswith(('http://', 'https://')):
            # Fetch the VRT content
            response = requests.get(dataset_path)
            vrt_content = response.text

            # Parse the VRT content
            vrt_tree = etree.fromstring(vrt_content)

            # Iterate over SourceFilename elements and modify them
            for source_filename_elem in vrt_tree.xpath("//SourceFilename"):
                # Set relativeToVRT attribute to 0
                source_filename_elem.set("relativeToVRT", "0")
                
                if source_filename_elem.text and not ("/vsicurl/" in source_filename_elem.text):
                    # Get the path of the source filename
                    source_path = source_filename_elem.text.strip()
                    base_url = self._get_base_url(dataset_path)
                    full_url = urljoin(base_url, source_path)
                    
                    # Replace the path with the full URL using /vsicurl/
                    source_filename_elem.text = f"/vsicurl/{full_url}"

            # Serialize the modified XML content back to string
            modified_vrt_content = etree.tostring(vrt_tree, pretty_print=True, encoding='utf-8').decode()

            return { "type": "vrt", "path": dataset_path, "vrt": modified_vrt_content }

        else:
            # Read the VRT content from a local file
            with open(dataset_path, "r") as f:
                vrt_content = f.read()

            # Parse the VRT content
            vrt_tree = etree.fromstring(vrt_content)

            # Iterate over SourceFilename elements and modify them
            for source_filename_elem in vrt_tree.xpath("//SourceFilename"):
                # If source_filename_elem contains http or https, add /vsicurl/ in front of it
                if source_filename_elem.text and not ("/vsicurl/" in source_filename_elem.text) and ("http://" in source_filename_elem.text or "https://" in source_filename_elem.text):
                    source_filename_elem.text = f"/vsicurl/{source_filename_elem.text.strip()}"

            # Serialize the modified XML content back to string
            modified_vrt_content = etree.tostring(vrt_tree, pretty_print=True, encoding='utf-8').decode()

            return { "type": "vrt", "path": dataset_path, "vrt": modified_vrt_content }
    
    def _create_mosaic_config(self, dataset_path: str):
        if dataset_path.startswith(('http://', 'https://')):
            try:
                response = requests.get(dataset_path)
                response.raise_for_status()  # Raise an exception for HTTP errors
                datasets_json = response.json()
            except requests.RequestException as e:
                print(f"Error fetching mosaic settings from {dataset_path}: {e}")
                return {} 
        else:
            # It's a local file, attempt to read JSON from it
            if not os.path.exists(dataset_path):
                print(f"Error: Local file {dataset_path} does not exist")
                return {} 
            try:
                with open(dataset_path, 'r') as f:
                    datasets_json = json.load(f)
            except Exception as e:
                print(f"Error reading mosaic settings from {dataset_path}: {e}")
                return {} 
        
        # Alter paths if dataset is a URL
        if dataset_path.startswith(('http://', 'https://')):
            base_url = self._get_base_url(dataset_path)
            for dataset in datasets_json.get("datasets", []):
                path = dataset.get('path')
                if path and not path.startswith(('http://', 'https://')):
                    absolute_path = urljoin(base_url, path)
                    dataset["path"] = absolute_path
        
        datasets_json["type"] = "mosaic"
        return datasets_json
        
    def _get_base_url(self, url):
        parsed_url = urlparse(url)
        if parsed_url.path.endswith('/'):
            return url
        else:
            return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path.rsplit('/', 1)[0]}/"
