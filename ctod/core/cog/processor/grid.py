import numpy as np

def generate_grid(width, height, num_rows, num_cols):
        # Create the grid using NumPy
    grid_x, grid_y = np.meshgrid(np.linspace(0, width, num_cols + 1), np.linspace(0, height, num_rows + 1))

    # Stack the x and y coordinates into a single array
    vertices = np.vstack((grid_x.flatten(), grid_y.flatten())).T
    
    # make vertices integers
    vertices = vertices.astype(int)
    
    triangles = []
    for i in range(num_rows):
        for j in range(num_cols):
            # Define the indices for the current quad
            top_left = i * (num_cols + 1) + j
            top_right = top_left + 1
            bottom_left = (i + 1) * (num_cols + 1) + j
            bottom_right = bottom_left + 1

            # Create two triangles for the quad with counterclockwise winding
            triangles.append([top_left, top_right, bottom_left])
            triangles.append([bottom_left, top_right, bottom_right])
    
    result = (vertices, triangles)
    return result