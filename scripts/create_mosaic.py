#!/usr/bin/env python3
import os
import argparse
import json
import subprocess
import rasterio
import numpy as np
from typing import Optional, Dict, Any

def get_gdalinfo(tiff_file: str) -> Optional[Dict[str, Any]]:
    """Extract information using gdalinfo.
    
    Args:
        tiff_file (str): The path to the GeoTIFF file.
    
    Returns:
        dict or None: A dictionary containing the extracted information from gdalinfo.
                      Returns None if there was an error extracting the information.
    """
    
    try:
        info = subprocess.check_output(['gdalinfo', '-json', tiff_file], text=True)
        info_json = json.loads(info)
        return info_json
    except Exception as e:
        print(f"Error extracting information from {tiff_file}: {e}")
        return None

def get_extent(tiff_path):
    """Extract extent from GeoTIFF file.
    
    Args:
        tiff_path (str): The path to the GeoTIFF file.
    
    Returns:
        tuple: A tuple containing the left, bottom, right, and top coordinates of the extent.
               Returns None if the extent information is not available.
    """
    
    info_json = get_gdalinfo(tiff_path)
    if info_json is None:
        return None
    extent = info_json.get('wgs84Extent')
    if extent is None:
        return None
    coordinates = extent.get('coordinates')[0]
    left = min(coord[0] for coord in coordinates)
    right = max(coord[0] for coord in coordinates)
    bottom = min(coord[1] for coord in coordinates)
    top = max(coord[1] for coord in coordinates)
    
    return (left, bottom, right, top)

def get_extent_ignore_nodata(tiff_path):
    """Extract extent from GeoTIFF file ignoring nodata values."""
    
    with rasterio.open(tiff_path) as src:
        # Initialize variables to hold the extent
        left, bottom, right, top = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        # Get nodata value
        nodata = src.nodatavals[0]  # Assuming a single nodata value for simplicity

        # Iterate over chunks
        for _, window in src.block_windows():
            # Read chunk of raster data as numpy array
            data_array = src.read(1, window=window)
            
            # Mask nodata values
            data_array_masked = np.ma.masked_equal(data_array, nodata)

            # Find indices where data is not nodata
            indices = np.where(~np.atleast_1d(data_array_masked.mask))

            # If there are no valid data points in the chunk, skip it
            if len(indices) < 2 or len(indices[0]) == 0 or len(indices[1]) == 0:
                continue

            # Calculate bounding box
            xmin = np.min(indices[1]) + window.col_off
            xmax = np.max(indices[1]) + window.col_off
            ymin = np.min(indices[0]) + window.row_off
            ymax = np.max(indices[0]) + window.row_off

            # Get affine transform to convert pixel coordinates to geographic coordinates
            transform = src.transform

            # Calculate bounding box in geographic coordinates
            chunk_left, chunk_bottom = transform * (xmin, ymax)
            chunk_right, chunk_top = transform * (xmax, ymin)

            # Update overall extent
            left = min(left, chunk_left)
            bottom = min(bottom, chunk_bottom)
            right = max(right, chunk_right)
            top = max(top, chunk_top)

    return (left, bottom, right, top)

def calculate_extent(tiff_file, ignore_nodata):
    """Calculate extent using parsed extent information."""
    
    if not ignore_nodata:
        print(f"Calculating extent including nodata: {tiff_file}")
        return get_extent(tiff_file)
    else:
        print(f"Calculating extent excluding nodata, this can take some time: {tiff_file}")
        return get_extent_ignore_nodata(tiff_file)

def create_json(input_folder, output_json, ignore_nodata):
    """Create JSON file from GeoTIFF files."""
    
    min_lon, min_lat, max_lon, max_lat = 180, 90, -180, -90
    
    datasets = []
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.tif', '.tiff')):
            tiff_file = os.path.join(input_folder, filename)
            
            left, bottom, right, top = calculate_extent(tiff_file, ignore_nodata)
            if None in [left, bottom, right, top]:
                continue
            
            min_lon = min(left, min_lon)
            min_lat = min(bottom, min_lat)
            max_lon = max(right, max_lon)
            max_lat = max(top, max_lat)
            
            relative_path = os.path.relpath(tiff_file, input_folder)
            datasets.append({
                "path": relative_path,
                "extent": [left, bottom, right, top]
            })
    
    overall_extent = [min_lon, min_lat, max_lon, max_lat]
    output_json["extent"] = overall_extent
    output_json["datasets"] = datasets
    
    with open(output_json["path"], 'w') as json_file:
        json.dump(output_json, json_file, indent=2)
    
    print(f"file created: {output_json['path']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JSON file from Cloud Optimized GeoTIFFs.")
    parser.add_argument("-i", "--input", metavar="input_folder", required=True,
                        help="Specify the input folder containing GeoTIFF files.")
    parser.add_argument("-o", "--output", metavar="output_file", default="dataset.ctod",
                        help="Specify the output JSON file name.")
    parser.add_argument("--ignore-nodata", action="store_true",
                        help="Ignore nodata values when calculating extent, getting tighter bounds which can result in better performing CTOD.")
    args = parser.parse_args()
    
    output_json = { "path": args.output , "extent": None, "datasets": [] }
    
    create_json(args.input, output_json, args.ignore_nodata)
