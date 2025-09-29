import os
'''
This module contains configuration settings for the project.
It includes paths to various directories and files used in the project.
Make sure that this file is in the root directory of the project.
'''

# Directory paths
ROOT_DIR = os.path.join(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
ALL_DATA_DIR = os.path.join(ROOT_DIR)
NEW_DATA_DIR = os.path.join(ROOT_DIR, 'new_data')
COREG_DIR = os.path.join(ROOT_DIR, 'coreg')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'outputs')

# Some constants
CRS = 'EPSG:32643'  # Coordinate Reference System
NUM_OF_REGIONS = 15  # Number of regions to process

# Some dictionaries
VI_TO_IDX = {
    'ndvi': 0, 
    'ndre': 1, 
    'gndvi': 2, 
    'ci_re': 3, 
    'vari': 4, 
    'evi2': 5, 
    'ngrdi': 6, 
    'bgi_custom': 7, 
    'gli_custom': 8, 
    'dvi': 9, 
    'sr_re': 10, 
    'norm2': 11, 
    'norm3': 12, 
    'savi': 13, 
    'lai': 14,
    'psri': 15
}