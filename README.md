# Cesium Terrain On Demand (CTOD)

CTOD is a service designed to fetch Cesium terrain tiles (quantized mesh) dynamically generated from a Cloud Optimized Geotif (COG) file. The core concept behind this service is to eliminate the need for creating an extensive cache, thereby saving time and storage space. Traditional caching methods often involve generating and storing numerous files, many of which may never be requested, resulting in unnecessary resource consumption. CTOD addresses this issue by generating terrain tiles on the fly, optimizing efficiency and reducing the burden on file storage.

![CTOD](./img/ctod.jpg)

## TL;DR

```sh
docker run -p 5000:5000 -v ./ctod_cache:/cache -e CTOD_TILE_CACHING_PATH=/cache ghcr.io/sogelink-research/ctod:latest
```

[Open demo viewer](http://localhost:5000)

## Features

- Generate and fetch a layer.json derived from COG, accommodating all projections.
- Retrieve .terrain tiles by tile index, currently supporting grid-based mesh.
- Support for extension octvertexnormals
- Averaging of heights and normals on shared edge vertices among terrain tiles.
- Empty tiles with geodetic surface normals.
- In-memory cache for seamlessly stitching neighboring tiles and preventing redundant requests.
- CogProcessor and TerrainGenerator for diverse terrain serving implementations (Grid, Pydelatin, custom).
- Simple tile caching implementation
- Basic Cesium viewer included for debugging and result visualization.

## ToDo

### V1.0

- Pass processor options
- Add skipCache to viewer
- Pydelatin and/or Martini support
- Refactoring
- Logging
- Cleanup viewer code
- Smaller docker image if possible

### V1.1

- Fill Nodata values on the fly
- Scripts to seed the cache
- Extension support: Metadata, Watermask
- Serverless functions

## Used libraries

- rio-tiler: Read data from COG files. (BSD-3-Clause)
- pydelatin: Terrain mesh generation from COG data. (MIT)
- quantized-mesh-encoder: Encode a mesh to a Quantized Mesh. (MIT)
- morecantile: Tile Matrix Sets. (MIT)

## Run CTOD with Docker

Example running CTOD using the docker image with a mounted volume and caching enabled.

```sh
docker run -p 5000:5000 -v ./ctod_cache:/cache -e CTOD_TILE_CACHING_PATH=/cache ghcr.io/sogelink-research/ctod:latest
```

## Run CTOD from source

Create a virtual environment, install and run CTOD.

```sh
python -m venv venv
source venv/bin/activate
pip install poetry
poetry install
python app.py
```

To enable caching start the service with a path to the cache.

```sh
python app.py ./ctod_cache
```

## Example adding TerrainProvider to Cesium

To use the CTOD terrain tiles in Cesium, create and set a `CesiumTerrainProvider` initialized with the url to the CTOD service. The layer.json file will be requested on the /tiles endpoint first followed by .terrain requests while passing the options to the endpoints.

```js
viewer.terrainProvider = new Cesium.CesiumTerrainProvider({
    url: `https://ctod-service/tiles?minZoom=1&maxZoom=21&cog=MyCogPath`,
    requestVertexNormals: true
});
```

## Example preparing COG

ToDo

## Caching

The CTOD service has a very basic tile caching option, tiles can be retrieved and saved by supplying a cache path when starting app.py or setting the environment variable `CTOD_TILE_CACHING_PATH`. Based on this path and the requested cog, meshing method and resampling method a tile can be saved and retrieved from disk. the cog path/url will be encoded into a hex string. When a service is started with caching the cache can be circumvented by adding `ignoreCache=True` to the terrain request.

## Nodata

Nodata values in the COG are automatically set to 0 else it is likely that the meshing will go wrong, for now nodata should be handled in the source data (COG) In a future version we can try to fill up the nodata values based on surounding pixels.

## Stitching tiles

With all the available methods to generate a mesh for a tiff we are facing the problem that we do not have shared vertices at tile edges as described by the quantized mesh standard. This results in seems between tiles because of possible height difference but also because the normals are only calculated for a tile and don't take adjecent tiles into account. In CTOD we solve this by requesting neighbouring tiles and make sure we have shared vertices and if needed average the height and normals. The terrain factory makes sure we download all needed data without duplicate request, the COG Processor processes the COG data making a mesh and normals, the Terrain Processor makes sure we have have shared edge vertices and the heights and normals are correct on the edges.

![CTOD: Non stitched tile](./img/normals.jpg)

*Stitching: Averaged normals between adjecent tiles*

### TerrainFactory

When requesting neighbouring tiles we want to prevent duplicate requests to the COG, this is handled in the TerrainFactory.

1) Terrain request comes in
2) Spawn cog request for terrain and adjecent tiles for each terrain request
3) Check if Processed COG is in cache, yes -> set cog data in terrain request, no -> add to requests queue if not added yet.
4) Download COG data and process using a COG processor
5) Add data to cache
6) Set COG data for all terrain requests that need this data
7) Check if a terrain requests has all the COG data it needs
8) Run the terrain processor
9) Return Quantized Mesh

![CTOD: TerrainFactory](./img/ctod_terrain_factory.jpg)

### CogProcessor

ToDo

### TerrainProcessor

ToDo

## Endpoints

### Endpoint: `/`

Returns a sample Cesium viewer

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000`

#### Parameters

- **minZoom** : The min zoomlevel for the terrain. Default (0)
- **maxZoom** : The max zoomlevel for the terrain. Default (20)
- **resamplingMethod** : Resampling method for COG: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss', 'rms'. Default 'bilinear'
- **cog** (required): Path or URL to COG file.
- **ignoreCache** : Set to true to prevent loading tiles from the cache. Default (False)

#### Example

```sh
http://localhost:5000?minZoom=1&maxZoom=20&cog=./ctod/files/test_cog.tif
```

### Endpoint: `/tiles/layer.json`

Dynamically generates a layer.json based on the COG.

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000/tiles/layer.json`

#### Parameters

- **maxZoom** : The max zoomlevel for the terrain. Default (20)
- **cog** (required): Path or URL to COG file.

#### Example

```sh
http://localhost:5000/tiles/layer.json?minZoom=14&maxZoom=20&cog=./ctod/files/test_cog.tif
```

### Endpoint: `/tiles/{z}/{x}/{y}.terrain`

Get a quantized mesh for tile index z, x, y. Set the minZoom value to retrieve empty tiles. maxZoom is handled in the generated layer.json.

#### Request

- **Method:** GET
- **URL:** `http://localhost:5000/tiles/{z}/{x}/{y}.terrain`

#### Parameters

- **minZoom** : The min zoomlevel for the terrain. Default (0)
- **maxZoom** : The max zoomlevel for the terrain, when lower than maxZoom for layer.json the service returns an empty terrain tile. Default (20)
- **resamplingMethod** : Resampling method for COG: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss', 'rms'. Default 'bilinear'
- **cog** (required): Path or URL to COG file.
- **ignoreCache** : Set to true to prevent loading tiles from the cache. Default (False)

#### Example

```sh
http://localhost:5000/tiles/17/134972/21614.terrain?minZoom=1&maxZoom=20&cog=./ctod/files/test_cog.tif
```
