import os


def get_tile_path(path: str, cog: str, meshing_method: str, resampling_method: str, z: int, x: int) -> str:
    """Get the path to the tile folder

    Args:
        path (str): path to cache on disk
        cog (str): parh or url to cog file
        meshing_method (str): the meshing method used
        resampling_method (str): the resampling method used
        z (int): z tile index
        x (int): x tile index

    Returns:
        str: path to the tile folder
    """
    
    cog = cog.encode("utf-8").hex()
    resampling_method = resampling_method if resampling_method is not None else ""
    return os.path.join(path, cog, meshing_method, resampling_method, str(z), str(x))

def get_tile_filepath(path: str, cog: str, meshing_method: str, resampling_method: str, z: int, x: int, y: int) -> str:
    """Get the path to the tile file

    Args:
        path (str): path to cache on disk
        cog (str): parh or url to cog file
        meshing_method (str): the meshing method used
        resampling_method (str): the resampling method used
        z (int): z tile index
        x (int): x tile index
        y (int): y tile index

    Returns:
        str: path to the tile file
    """
    
    tile_path = get_tile_path(path, cog, meshing_method, resampling_method, z, x)
    return os.path.join(tile_path, f"{y}.terrain")
    
def get_tile_from_disk(path: str, cog: str, meshing_method: str, resampling_method: str, z: int, x: int, y: int) -> bytes:
    """Get a terrain tile from disk, filepath is based on path, cog, mesding_method, z, x, y

    Args:
        path (str): path to cache on disk
        cog (str): parh or url to cog file
        meshing_method (str): the meshing method used
        resampling_method (str): the resampling method used
        z (int): z tile index
        x (int): x tile index
        y (int): y tile index
    Returns:
        data (bytes): bytes of the .terrain tile (quantized mesh)
    """
    
    file_path = get_tile_filepath(path, cog, meshing_method, resampling_method, z, x, y)
    
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return f.read()
    else:
        return None
    

def save_tile_to_disk(path: str, cog: str, meshing_method: str, resampling_method: str, z: int, x: int, y: int, data: bytes):
    """Save a terrain tile to disk, filepath is based on path, cog, mesding_method, z, x, y

    Args:
        path (str): path to cache on disk
        cog (str): parh or url to cog file
        meshing_method (str): the meshing method used
        resampling_method (str): the resampling method used
        z (int): z tile index
        x (int): x tile index
        y (int): y tile index
        data (bytes): bytes of the .terrain tile (quantized mesh)
    """
    
    tile_path = get_tile_path(path, cog, meshing_method, resampling_method, z, x)
    file_path = get_tile_filepath(path, cog, meshing_method, resampling_method, z, x, y)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(tile_path):
        os.makedirs(tile_path)

    with open(file_path, "wb") as f:
        f.write(data)