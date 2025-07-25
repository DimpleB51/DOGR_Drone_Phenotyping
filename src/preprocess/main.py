import os
import argparse
from tqdm import tqdm

import numpy as np

import preprocess.utils as utils
import mask_me_v2 as mask2
import config as cfg
import geopandas as gpd
import pandas as pd
from datetime import datetime

def combine_bands(folder_path):
    all_tif_data = np.empty((6, 0, 0))
    meta = None
    transform = None
    crs = None
    date = os.path.basename(folder_path)
    for tiffile in tqdm(sorted(os.listdir(folder_path)), 
                            desc=f"Processing {date} Tif Files", 
                            unit="file",
                            leave=False):
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
        if files.endswith('_VIs.tif'):
            cnt += 1
    return cnt >= cfg.NUM_OF_REGIONS

def main():
    parser = argparse.ArgumentParser(description="Process TIF files to compute indices and apply mask.")
    parser.add_argument(
        '--root_folder', type=str, 
        default=os.path.join(cfg.COREG_DIR), 
        help="Input folder containing date wise folders containing bandwise TIF files."
        )
    parser.add_argument(
        '--output_folder', type=str, 
        default=os.path.join(cfg.OUTPUT_DIR, 'regions'), 
        help="Folder to save output files."
        )
    parser.add_argument(
        '--trial_no', type=int,
        required=True,
        help="Trial number for processing."
    )
    parser.add_argument(
        '--trials_details', type=str,
        default=os.path.join(cfg.ALL_DATA_DIR, 'trials_details.csv'),
        help="JSON file with trials details."
        )
    parser.add_argument(
        '--compress_save', 
        action='store_true', 
        help="Enable compression and saving."
        )
    args = parser.parse_args()

    root_folder = args.root_folder
    output_folder = os.path.join(args.output_folder, f'trial_{args.trial_no}')
    mask_json = os.path.join(cfg.ALL_DATA_DIR, 'masks', f'trial_{args.trial_no}.gpkg')
    compress_save = args.compress_save

    region_id_col = 'region_id'
    treatment_id_col = 'treat_id'
    regions_gdf = gpd.read_file(mask_json)
    
    # Read trials details and filter by trial_no
    trials_df = pd.read_csv(args.trials_details)
    trial_row = trials_df[trials_df['Trial_No'] == f'Trial_{args.trial_no}']

    if trial_row.empty:
        print(f"{trials_df['Trial_No']}")

        raise ValueError(f"Trial number {args.trial_no} not found in trials details")

    trial_info = trial_row.iloc[0]
    transplanting_date = pd.to_datetime(trial_info['Date_of_Transplanting']).date()
    harvesting_date = pd.to_datetime(trial_info['Date_of_Harvesting']).date()

    print(f"Processing dates between {transplanting_date} and {harvesting_date} for trial {args.trial_no}")

    # Filter available dates based on transplanting and harvesting dates
    available_dates = []
    
    for date_folder in sorted(os.listdir(root_folder)):
        try:
            folder_date = datetime.strptime(f"20{date_folder}", '%Y_%m_%d').date()
            if transplanting_date <= folder_date <= harvesting_date:
                available_dates.append(date_folder)
        except ValueError:
            # Skip folders that don't match date format
            continue

    available_dates = sorted(available_dates)
    print(f"Found {len(available_dates)} dates to process: {available_dates}")
    
    with tqdm(total=len(available_dates),
                desc="Processing Dates", 
                unit="date",
                position=0) as pbar:
        # for date_folder in sorted(os.listdir(root_folder)):
        for date in sorted(available_dates):
            pbar.set_postfix_str(f"Processing {date}")
            specific_output_dir = os.path.join(output_folder, date)
            if not (os.path.exists(specific_output_dir) and output_exists(specific_output_dir)):
                date_folder_path = os.path.join(root_folder, date)
                
                all_tif_data, meta, transform, crs = combine_bands(date_folder_path)
                if regions_gdf.crs != crs:
                    print(f"Reprojecting regions from {regions_gdf.crs} to {crs} (image CRS)")
                    regions_gdf = regions_gdf.to_crs(crs)
                
                regions_for_processing = []
                for _, row in regions_gdf.iterrows():
                    regions_for_processing.append({ 
                        'label': f'R{row.get(region_id_col)}T{row.get(treatment_id_col)}', 
                        'geometry': row.geometry
                        })

                indices_data = utils.calculate_VIs(all_tif_data)
                os.makedirs(specific_output_dir, exist_ok=True)
                
                with tqdm(total=len(regions_for_processing),
                            desc=f'Processing regions for {date}',
                            unit='region',
                            position=1,
                            leave=False) as regBar:
                    for region_info in regions_for_processing:
                        regBar.set_postfix_str(f"Processing {region_info['label']}")
                        mask2.mask_crop_save(indices_data, 
                                                region_info, 
                                                transform, 
                                                meta,
                                                crs, 
                                                specific_output_dir,
                                                'VIs', 
                                                compress_save)
                        regBar.update(1)
            else:
                print(f"Output folder already exists for {date}. Skipping...")
            pbar.update(1)
                  
if __name__ == "__main__":
    main()