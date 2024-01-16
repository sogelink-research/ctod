from enum import Enum, auto

class Direction(Enum):
    """Directions from a tile"""
    
    NORTH = auto()
    NORTHEAST = auto()
    EAST = auto()
    SOUTHEAST = auto()
    SOUTH = auto()
    SOUTHWEST = auto()
    WEST = auto()
    NORTHWEST = auto()
    
def move_in_direction(x: int, y: int, direction: Direction) -> tuple[int, int]:
    """Retrieve the new x and y coordinates when moving in a direction

    Args:
        x (int): x tile index
        y (int): y tile index
        direction (Direction): The direction to move in

    Raises:
        ValueError: Invalid direction

    Returns:
        tuple[int, int]: The new x and y coordinates
    """
    
    if direction == Direction.NORTH:
        return x, y - 1
    elif direction == Direction.NORTHEAST:
        return x + 1, y - 1
    elif direction == Direction.EAST:
        return x + 1, y
    elif direction == Direction.SOUTHEAST:
        return x + 1, y + 1
    elif direction == Direction.SOUTH:
        return x, y + 1
    elif direction == Direction.SOUTHWEST:
        return x - 1, y + 1
    elif direction == Direction.WEST:
        return x - 1, y
    elif direction == Direction.NORTHWEST:
        return x - 1, y - 1
    else:
        raise ValueError("Invalid direction")