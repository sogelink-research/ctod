<p align="center" style="background-color: #202020;">
  <img src="./img/ctod_logo.jpg" alt="CTOD">
</p>
    
CTOD is a service designed to fetch Cesium terrain tiles (quantized mesh) dynamically generated from a Cloud Optimized GeoTIFF (COG). The core concept behind this service is to eliminate the need for creating an extensive cache, thereby saving time and storage space. Traditional caching methods often involve generating and storing numerous files, many of which may never be requested, resulting in unnecessary resource consumption. CTOD addresses this issue by generating terrain tiles on the fly, optimizing efficiency and reducing the burden on file storage.

![CTOD](./img/ctod.jpg)

## TL;DR

```sh
docker run -p 5000:5000 -v ./ctod_cache:/cache -e CTOD_PORT=5000 -e CTOD_LOGGING_LEVEL=info -e CTOD_TILE_CACHE_PATH=/cache ghcr.io/sogelink-research/ctod:latest
```

[Open the local running demo viewer](http://localhost:5000)

## Features

- Generate and fetch a layer.json derived from COG, accommodating all projections.
- Retrieve .terrain tiles by tile index, currently supporting grid and martini based mesh.
- Support for extension octvertexnormals
- Averaging of heights and normals on shared edge vertices among terrain tiles.
- Empty tiles with geodetic surface normals.
- In-memory cache for seamlessly stitching neighboring tiles and preventing redundant requests.
- CogProcessor and TerrainGenerator for diverse terrain serving implementations (grid, martini, custom).
- Basic tile caching implementation
- Basic Cesium viewer included for debugging and result visualization.
- Scripts to partly seed cache and generate mosaic dataset.

## Wiki

- [Meshing methods](https://github.com/sogelink-research/ctod/wiki/Meshing-methods)
- [Tile stitching](https://github.com/sogelink-research/ctod/wiki/Tile-stitching)
- [COG Optimization](https://github.com/sogelink-research/ctod/wiki/COG-Optimization) ToDo
- [Seeding the cache](https://github.com/sogelink-research/ctod/wiki/Seeding-the-cache) ToDo
- [VRT and Mosaic](https://github.com/sogelink-research/ctod/wiki/VRT-and-Mosaic) ToDo

## ToDo

### V1.0 (In progress)

- Refactoring
- Cleanup viewer code
- Update Wiki

### Future work (V1.1)

- Fill Nodata values on the fly
- Extension support: Metadata, Watermask

## Settings

The following options can be set by supplying args to app.py or setting the environment variables.

|argument|environment variable|description|default|
|-|-|-|-|
|--tile-cache-path|CTOD_TILE_CACHE_PATH|Cache dir, not set = cache disabled|None|
|--logging-level|CTOD_LOGGING_LEVEL|debug, info, warning, error, critical|info|
|--port|CTOD_PORT|Port to run the service on|5000|
|--unsafe|CTOD_UNSAFE|Load unsafe tiles (not enough COG overviews or too many datasets in 1 tile), can result in huge and or stuck requests||

## Run CTOD

Run CTOD using docker or from source, see `Settings` for configuration options.

### Using Docker

Example running CTOD using the docker image with a mounted volume and caching enabled.

```sh
docker run -p 5000:5000 -v ./ctod_cache:/cache -e CTOD_TILE_CACHE_PATH=/cache ghcr.io/sogelink-research/ctod:latest
```

### From source

Create a virtual environment, install and run CTOD.

```sh
python -m venv venv
source venv/bin/activate
pip install poetry
poetry install
python app.py
```

To enable caching, supply --tile-cache-path path to app.py.

```sh
python app.py --tile-cache-path ./ctod_cache
```

## Endpoints

### Endpoint: `/`

Returns a sample Cesium viewer, all values can be changed using the control panel, default settings can be overwritten on startup of the viewer with the below parameters, see the example aswell.

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000`

#### Parameters

- **minZoom** : The min zoomlevel for the terrain. Default (0)
- **maxZoom** : The max zoomlevel for the terrain. Default (18)
- **resamplingMethod** : Resampling method for COG: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss', 'rms'. Default 'none'
- **cog** (required): Path or URL to COG file.
- **ignoreCache** : Set to true to prevent loading tiles from the cache. Default (False)
- **meshingMethod**: The Meshing method to use: 'grid', 'martini', 'delatin'

#### Example

```sh
http://localhost:5000?minZoom=1&maxZoom=18&cog=./ctod/files/test_cog.tif
```

### Endpoint: `/tiles/layer.json`

Dynamically generates a layer.json based on the COG.

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000/tiles/layer.json`

#### Parameters

- **maxZoom** : The max zoomlevel for the terrain. Default (18)
- **cog** (required): Path or URL to COG file.

#### Example

```sh
http://localhost:5000/tiles/layer.json?maxZoom=18&cog=./ctod/files/test_cog.tif
```

### Endpoint: `/tiles/{z}/{x}/{y}.terrain`

Get a quantized mesh for tile index z, x, y. Set the minZoom value to retrieve empty tiles for zoom levels lower than minZoom. maxZoom is handled in the generated layer.json.

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000/tiles/{z}/{x}/{y}.terrain`

#### Parameters

- **minZoom** : The min zoomlevel for the terrain. Default (0)
- **resamplingMethod** : Resampling method for COG: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss', 'rms'. Default 'none'
- **cog** (required): Path or URL to COG file.
- **ignoreCache** : Set to true to prevent loading tiles from the cache. Default (False)
- **meshingMethod**: The Meshing method to use: 'grid', 'martini', 'delatin'

#### Parameters for meshing method: grid

- **defaultGridSize**: The default grid size (amount of rows/cols) to use if there is no specific zoomGridSizes defined for a requested tile, Default (20)
- **zoomGridSizes**: Per level defined grid size, when requested zoom for tile not specified use defaultGridSize. Default (`{"15": 25, "16": 25, "17": 30, "18": 35, "19": 35, "20": 35, "21": 35, "22": 35}`)

#### Parameters for meshing method: martini

- **defaultMaxError**: The default max triangulation error in meters to use, Default (4)
- **zoomMaxErrors**: Per level defined max error, when requested zoom for tile not specified use defaultMaxError. Default (`{"15": 8, "16": 5, "17": 3, "18": 2, "19": 1, "20": 0.5, "21": 0.3, "22": 0.1}`)

#### Example

```sh
http://localhost:5000/tiles/17/134972/21614.terrain?minZoom=1&cog=./ctod/files/test_cog.tif
```

## More info

### How to use in Cesium

To use the CTOD terrain tiles in Cesium, create and set a `CesiumTerrainProvider` initialized with the url to the CTOD service. The layer.json file will be requested on the /tiles endpoint followed by .terrain requests while passing the options to the endpoints.

```js
viewer.terrainProvider = new Cesium.CesiumTerrainProvider({
    url: `https://ctod-service/tiles?minZoom=1&maxZoom=18&cog=MyCogPath`,
    requestVertexNormals: true
});
```

### Caching

The CTOD service has a very basic tile caching option, tiles can be retrieved and saved by supplying a cache path when starting app.py or setting the environment variable `CTOD_TILE_CACHE_PATH`. Based on this path and the requested cog, meshing method and resampling method a tile can be saved and retrieved from disk. the cog path/url will be encoded into a hex string. When a service is started with caching the cache can be circumvented by adding `ignoreCache=True` to the terrain request.

### Nodata

Nodata values in the COG are automatically set to 0 else it is likely that the meshing will go wrong, for now nodata should be handled in the source data (COG) In a future version we can try to fill up the nodata values based on surrounding pixels.

### Used libraries

- [rio-tiler](https://github.com/cogeotiff/rio-tiler): Rasterio plugin to read raster datasets. (BSD-3-Clause)
- [pydelatin](https://github.com/kylebarron/pydelatin): Terrain mesh generation. (MIT)
- [pymartini](https://github.com/kylebarron/pymartini): Terrain mesh generation. (MIT/ISC)
- [quantized-mesh-encoder](https://github.com/kylebarron/quantized-mesh-encoder): A fast Python Quantized Mesh encoder. (MIT)
- [morecantile](https://github.com/developmentseed/morecantile): Construct and use OGC TileMatrixSets. (MIT)
