import os
import numpy as np
from tqdm import tqdm

from utils import *
from mask_me import *
from affine import Affine
from compressor import *
import argparse
'''
Currently this file will take a root_folder containing 6 single spectral .tif file
representing [R, G, B, NIR, RE, PANCHRO]
and a .json file containing the polygon coordinates
as input and will create a masked .tif file
based on the polygon in the .json file
This new .tif file will have multiple bands representing defferent VIs
'''

def main():
    parser = argparse.ArgumentParser(description="Process TIF files to compute indices and apply mask.")
    parser.add_argument(
        '--root_folder', type=str, 
        default='/raid/biplab/souravr/TIH/CROP/data/28Aug23', 
        help="Input folder containing TIF files."
        )
    parser.add_argument(
        '--output_folder', type=str, 
        default='/raid/biplab/souravr/TIH/CROP/output2/trial_1', 
        help="Folder to save output files."
        )
    parser.add_argument(
        '--mask_json', type=str, 
        default='/raid/biplab/souravr/TIH/CROP/data/trial1_regions.json', 
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

    all_tif_data = np.empty((0, 0, 6))
    meta = None
    transform = None
    crs = None

    for tiffile in tqdm(sorted(os.listdir(root_folder)), desc="Processing TIF files", unit="file"):
        # [B, G, NIR, PANCHRO, RE, R]
        print(f'Processing {tiffile}')
        tif_path = os.path.join(root_folder, tiffile)
        tif_data, meta, transform, crs = load_tif_numpy_with_meta(tif_path)
        
        if tif_data is not None:
            tif_data = clean_tif(tif_data)
            # print_stats(tif_data)
            # title = f"Histogram of {tiffile}"
            # hist_plot(tif_data, title)
            
            # Extract the band identifier from the file name (expecting it to be the last part before the extension)
            band = os.path.splitext(tiffile)[0].split('_')[-1]
            # Define the mapping for desired channel order: [R, G, B, NIR, RE, PANCHRO]
            band_mapping = {"red": 0, "green": 1, "blue": 2, "nir": 3, "edge": 4, "panchro": 5}

            if band in band_mapping:
                channel_idx = band_mapping[band]
                # Initialize all_tif_data with the correct spatial shape on the first assignment
                if all_tif_data.size == 0:
                    all_tif_data = np.empty((tif_data.shape[0], tif_data.shape[1], 6))
                all_tif_data[:, :, channel_idx] = tif_data
            else:
                print(f"Unexpected band identifier: {band}")
                break
        else:
            print(f"Failed to load {tiffile}")

    indices_data = calculate_VIs(all_tif_data)
    
    # Masking area of interest
    polygon = get_polygon_from_json(mask_json)
    if indices_data.shape[0] > indices_data.shape[-1]:
        mask_shape = indices_data.shape[:-1]
    else:
        mask_shape = indices_data.shape[1:]   
    for i, region in enumerate(polygon):
        mask = create_mask_from_polygon(region['polygon'], mask_shape)
        masked_indices_data = apply_mask_to_array(indices_data, mask, meta['nodata'])

        out_folder = os.path.join(
            output_folder,
            f'{base_file}'
            )

        os.makedirs(out_folder, exist_ok=True)

        output_tiffile = os.path.join(
            out_folder,
            f'{region["label"]}_VIs.tif'
            )
        save_numpy_as_geotiff(
            output_tiffile,
            masked_indices_data,
            meta,
            transform,
            crs
            )
        print(f'Masked indices saved as {output_tiffile}')

        if compress_save:
            print("Compressing and saving...")
            print('This is for visual purpose and testing only, Should be set to False in production')
            compress_multi(
                output_tiffile,
                os.path.join(out_folder, 'compressed')
            )


if __name__ == "__main__":
    main()