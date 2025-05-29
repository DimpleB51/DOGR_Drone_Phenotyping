from osgeo import gdal, osr
import os
import glob
import numpy as np
from tqdm import tqdm

def my_coreg(
    source_tif_path,
    points_file_path,
    output_tif_path,
):
    import subprocess

    with open(points_file_path, 'r') as f:
        lines = f.readlines()

    if len(lines) != 1:
        raise ValueError("pointsFile must contain exactly two lines with gdal_translate and gdalwarp commands.")

    # Replace placeholders with actual paths
    temp_tif_file = os.path.join(TEMP_FOLDER, os.path.splitext(os.path.basename(source_tif_path))[0] + '_temp.tif')
    
    line1 = lines[0][:-1] + ' ' + f'"{source_tif_path}"' + ' ' + f'"{temp_tif_file}"'
    line2 = 'gdalwarp -r near -order 1 -co COMPRESS=LZW  -t_srs EPSG:32643' + ' ' + f'"{temp_tif_file}"' + ' ' + f'"{output_tif_path}"'

    print(f"Executing command 1: {line1}")
    # Execute the commands
    subprocess.run(line1, shell=True, check=True)

    print(f"Executing command 2: {line2}")
    subprocess.run(line2, shell=True, check=True)



import config as cfg
# --- Main Script Logic ---
if __name__ == "__main__":
    SLAVE_DATE_LABEL = 'YY_MM_DD' # Example slave date
    QGIS_GCP_POINTS_FILE = os.path.join(cfg.ALL_DATA_DIR, 'name_of_points_file.points')
    TEMP_FOLDER = os.path.join(cfg.ALL_DATA_DIR, 'temp')
    FINAL_COREG_OUTPUT_DIR = os.path.join(cfg.OUTPUT_DIR, 'coreg', SLAVE_DATE_LABEL)
    os.makedirs(FINAL_COREG_OUTPUT_DIR, exist_ok=True)

    # --- Process ---
    if not os.path.exists(QGIS_GCP_POINTS_FILE):
        print(f"FATAL: QGIS GCP .points file not found: {QGIS_GCP_POINTS_FILE}")
    else:
        for tif_band in tqdm(sorted(os.listdir(os.path.join(cfg.DATA_DIR, SLAVE_DATE_LABEL)))):
            if tif_band.endswith('.tif'):
                source_tif_path = os.path.join(cfg.DATA_DIR, SLAVE_DATE_LABEL, tif_band)
                coregistered_tif_path = os.path.join(FINAL_COREG_OUTPUT_DIR, tif_band)
                try:
                    my_coreg(
                        source_tif_path=source_tif_path,
                        points_file_path=QGIS_GCP_POINTS_FILE,
                        output_tif_path=coregistered_tif_path
                    )
                    print(f"Coregistered {tif_band} successfully.")
                except Exception as e:
                    print(f"Error processing {tif_band}: {e}")
                    continue
        print(f"Coregistration completed. Output saved to: {FINAL_COREG_OUTPUT_DIR}")