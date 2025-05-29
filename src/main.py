import os
import argparse
from tqdm import tqdm

import numpy as np
from rasterio.windows import Window

import utils
import mask_me_v2 as mask2
from affine import Affine
import compressor
import sys
import config as cfg
import geopandas as gpd

'''
Currently this file will take a root_folder containing 6 single spectral .tif file
representing [R, G, B, NIR, RE, PANCHRO]
and a .json file containing the polygon coordinates
as input and will create a masked .tif file
based on the polygon in the .json file
This new .tif file will have multiple bands representing defferent VIs
'''

def combine_bands(folder_path):
    all_tif_data = np.empty((6, 0, 0))
    meta = None
    transform = None
    crs = None
    date = os.path.basename(folder_path)
    for tiffile in tqdm(sorted(os.listdir(folder_path)), 
                            desc=f"Processing {date} Tif Files", 
                            unit="file"):
        # [B, G, NIR, PANCHRO, RE, R]
        tif_path = os.path.join(folder_path, tiffile)
        tif_data, meta, transform, t_crs = utils.load_tif_numpy_with_meta(tif_path)
        if (crs is None) or (t_crs == crs):
            crs = t_crs
        else:
            if t_crs != crs:
                raise ValueError(f"CRS mismatch: {t_crs} vs {crs}")

        if tif_data is not None:
            if tif_data.ndim == 3:
                tif_data = tif_data[0]  # Using first band only
            
            # Extract the band identifier from the file name (expecting it to be the last part before the extension)
            band = os.path.splitext(tiffile)[0].split('_')[-1]
            # Define the mapping for desired channel order: [R, G, B, NIR, RE, PANCHRO]
            band_mapping = {"red": 0, "green": 1, "blue": 2, "nir": 3, "edge": 4, "panchro": 5}

            if band in band_mapping:
                channel_idx = band_mapping[band]
                # Initialize all_tif_data with the correct spatial shape on the first assignment
                if all_tif_data.size == 0:
                    all_tif_data = np.empty((6, tif_data.shape[0], tif_data.shape[1]))
                all_tif_data[channel_idx, :, :] = tif_data
            else:
                raise ValueError(f"Unknown band identifier in file name: {band}")
        else:
            raise ValueError(f"Failed to load TIF data from {tif_path}")

    return all_tif_data, meta, transform, crs 

def output_exists(output_dir):
    cnt = 0
    for files in os.listdir(output_dir):
        if files.endswith('.tif'):
            cnt += 1
    return cnt >= 15

def main():
    parser = argparse.ArgumentParser(description="Process TIF files to compute indices and apply mask.")
    parser.add_argument(
        '--root_folder', type=str, 
        default=os.path.join(cfg.DATA_DIR, 'coreg'), 
        help="Input folder containing date wise folders containing bandwise TIF files."
        )
    parser.add_argument(
        '--output_folder', type=str, 
        default=os.path.join(cfg.OUTPUT_DIR, 'regions'), 
        help="Folder to save output files."
        )
    parser.add_argument(
        '--mask_json', type=str, 
        default=os.path.join(cfg.ALL_DATA_DIR, 'field_regions.gpkg'), 
        help="JSON file with polygon coordinates."
        )
    parser.add_argument(
        '--compress_save', 
        action='store_true', 
        help="Enable compression and saving."
        )
    args = parser.parse_args()

    root_folder = args.root_folder
    base_file = os.path.basename(root_folder)
    output_folder = args.output_folder
    mask_json = args.mask_json
    compress_save = args.compress_save

    region_id_col = 'region_id'
    regions_gdf = gpd.read_file(mask_json)
    
    with tqdm(total=len(os.listdir(root_folder)),
                desc="Processing Dates", 
                unit="date") as pbar:
        # for date_folder in sorted(os.listdir(root_folder)):
        for date_folder in sorted(os.listdir(root_folder)):
            pbar.set_postfix_str(f"Processing {date_folder}")
            specific_output_dir = os.path.join(output_folder, date_folder)
            if not (os.path.exists(specific_output_dir) and output_exists(specific_output_dir)):
                date_folder_path = os.path.join(root_folder, date_folder)
                
                all_tif_data, meta, transform, crs = combine_bands(date_folder_path)
                if regions_gdf.crs != crs:
                    print(f"Reprojecting regions from {regions_gdf.crs} to {crs} (image CRS)")
                    regions_gdf = regions_gdf.to_crs(crs)
                
                regions_for_processing = []
                for _, row in regions_gdf.iterrows():
                    regions_for_processing.append({'label': row[region_id_col], 'geometry': row.geometry})
                    
                
                indices_data = utils.calculate_VIs(all_tif_data)
                os.makedirs(specific_output_dir, exist_ok=True)
                
                for region_info in regions_for_processing:
                    mask2.mask_crop_save(indices_data, 
                                            region_info, 
                                            transform, 
                                            meta,
                                            crs, 
                                            specific_output_dir, 
                                            compress_save)
            else:
                print(f"Output folder already exists for {date_folder}. Skipping...")
            pbar.update(1)
                  
if __name__ == "__main__":
    main()