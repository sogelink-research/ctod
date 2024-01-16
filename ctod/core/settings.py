def get_mesh_max_error(z):
    zoom_to_error = {
        0:  20.0, 
        1:  20.0, 
        2:  20.0, 
        3:  20, 
        4:  15, 
        5:  15, 
        6:  15, 
        7:  15, 
        8:  15, 
        9:  15, 
        10: 7, 
        11: 6, 
        12: 5, 
        13: 4, 
        14: 3.5, 
        15: 3.0, 
        16: 2.5, 
        17: 1.0, 
        18: 0.5, 
        19: 0.5, 
        20: 0.5,
        21: 0.3,
        22: 0.2,
        23: 0.1
    }

    # Ensure that the provided zoom level is within bounds
    z = max(0, min(z, 23))

    # Retrieve the corresponding mesh_max_error from the lookup table
    return zoom_to_error[z]