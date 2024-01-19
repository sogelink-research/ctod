
# Test data

1.1GB DTM tiff of a small part in Norway downloaded from hoydedata.

# Script

To benchmark we use a python script which returns the average time in milliseconds it took to get a tile from a COG, the script can be found under `benchmark/scripts/test_cog_get_tile.py`.

Start the script with `-config` to use a json config or use `-cog -z -x -y`, to run in parallel add `-p`

|argument|description|
|-|-|
|-config|Path to json config|
|-p|Run download cog in parallel|
|-cog|Path/url to cog|
|-z|Tile index z|
|-x|Tile index x|
|-y|Tile index y|

## Benchmark 1

|||
|-|-|
|projection|ETRS89 (EPSG:4258)|
|overviews|2 4 8 16|
|compression|lzw|

### Prepare COG

```sh
gdaladdo -r average norway.tif 2 4 8 16
gdal_translate norway.tif norway_4258_lzw_16.tif -co COMPRESS=LZW -co TILED=YES -co COPY_SRC_OVERVIEWS=YES
```

### Run

```sh
python ./benchmark/scripts/test_cog_get_tile.py -p -config ./benchmark/configs/get_tile_norway_4258_lzw_16.json
```

### Result running in series

```sh
--------------------------------------------------
Get tile for /home/time/Downloads/dtm_norway/norway_4258_lzw_16.tif
--------------------------------------------------
Z        X        Y            avg (ms)
--------------------------------------------------
8        270      43           139ms
19       553588   88725        7ms
```

### Result running in parallel

```sh
--------------------------------------------------
Get tile for /home/time/Downloads/dtm_norway/norway_4258_lzw_16.tif
--------------------------------------------------
Z        X        Y            avg (ms)
--------------------------------------------------
8        270      43           779ms
19       553588   88725        142ms
```
