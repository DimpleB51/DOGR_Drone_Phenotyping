import os
'''
This module contains configuration settings for the project.
It includes paths to various directories and files used in the project.
Make sure that this file is in the root directory of the project.
'''

# Directory paths
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ALL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'all_data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

# Some constants
CRS = 'EPSG:32643'  # Coordinate Reference System
NUM_OF_REGIONS = 15  # Number of regions to process