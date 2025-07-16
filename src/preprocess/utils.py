import numpy as np
import os
import rasterio
from rasterio.warp import reproject, Resampling
import matplotlib.pyplot as plt

import numpy as np

def load_tif_numpy_with_meta(tiff_path):
    """
    Load a TIFF file as a NumPy array using rasterio.
    returns the image array, metadata, transform, and CRS.
    """
    with rasterio.open(tiff_path) as dataset:
        image_array = dataset.read()
        if image_array.ndim == 3 and (image_array.shape[0] > image_array.shape[-1]):
            image_array = image_array.transpose(2, 0, 1)  # Change to HWC format
        if image_array.ndim == 2:
            image_array = image_array[np.newaxis, ...]
        meta = dataset.meta.copy()  # Save metadata
        trasnform = meta['transform']
        crs = meta['crs']
    return image_array, meta, trasnform, crs

def hist_plot(data, title='Histogram'):
    """
    Plot a histogram of the pixel values in the image.
    """
    plt.hist(data.ravel(), bins=100)
    plt.ylim(0, 1e7)
    plt.title(title)
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.show()

def print_stats(data):
    """
    Print statistics of the pixel values in the image.
    """
    import numpy as np
    print("Min value:", np.nanmin(data))
    print("Max value:", np.nanmax(data))
    print("Mean value:", np.nanmean(data))
    print("Median value:", np.nanmedian(data))
    print("Standard deviation:", np.nanstd(data))

def clean_tif(tif_data):
    tif_data[tif_data < 0] = np.nan
    nan_count = np.isnan(tif_data).sum()
    total_count = tif_data.size
    nan_percentage = 100 * nan_count / total_count
    print(f"Percentage of NaN values: {nan_percentage:.2f}%")
    return tif_data

import numpy as np

def calculate_VIs(data_6channel_bands_first):
    """
    Calculates various vegetation indices from 6-channel image data.

    The input data is expected to have bands in the following order:
    0: Red (R)
    1: Green (G)
    2: Blue (B)
    3: Near-Infrared (NIR)
    4: RedEdge (RE)
    5: Panchromatic (PAN) - This channel is not used for these VIs.

    The input array should have shape (num_channels, height, width).
    Reflectance values should ideally be between 0 and 1.

    Returns:
        np.ndarray: A NumPy array of shape (15, height, width) containing the calculated VIs.
                    Handles division by zero by returning NaN or Inf where appropriate based on NumPy's behavior.
    """
    
    R = data_6channel_bands_first[0].astype(np.float32)
    G = data_6channel_bands_first[1].astype(np.float32)
    B = data_6channel_bands_first[2].astype(np.float32)
    NIR = data_6channel_bands_first[3].astype(np.float32)
    RE = data_6channel_bands_first[4].astype(np.float32)
    # PAN = data_6channel_bands_first[5] # Not used

    epsilon = 1e-8 

    with np.errstate(divide='ignore', invalid='ignore'):
        # 0. NDVI
        ndvi = (NIR - R) / (NIR + R + epsilon)
        
        # 1. NDRE
        ndre = (NIR - RE) / (NIR + RE + epsilon)
        
        # 2. GNDVI
        gndvi = (NIR - G) / (NIR + G + epsilon)
        
        # 3. Red Edge Chlorophyll Index (CI-RE)
        ci_re = (NIR / (RE + epsilon)) - 1
        
        # 4. Visible Atmospherically Resistant Index (VARI)
        vari = (G - R) / (G + R - B + epsilon)
        
        # 5. Enhanced Vegetation Index 2 (EVI2)
        evi2 = 2.5 * (NIR - R) / (NIR + 2.4 * R + 1.0 + epsilon) # Added epsilon to denominator sum part
        
        # 6. NGRDI (Normalized Green Red Difference Index)
        ngrdi = (G - R) / (G + R + epsilon)
        
        # 7. BGI (Blue Green Index - assuming typical formulation, yours is different)
        # Your formula: (NIR + Red) / Green
        # Common BGI for soil: B / G. For vegetation health, sometimes (G-B)/(G+B) or similar.
        # Implementing your formula:
        bgi_custom = (NIR + R) / (G + epsilon)
        
        # 8. GLI (Green Leaf Index - assuming typical formulation, yours is different)
        # Your formula: Green / (NIR + Red)
        # Common GLI: (2*G - R - B) / (2*G + R + B)
        # Implementing your formula:
        gli_custom = G / (NIR + R + epsilon)

        # 9. DVI (Difference Vegetation Index)
        dvi = NIR - R
        
        # 10. SR (Simple Ratio - using Red Edge as per your table)
        sr_re = NIR / (RE + epsilon) # Your table says NIR / Red Edge
        
        # 11. NORM2 ( (Red - Green) / (Red + Green) )
        norm2 = (R - G) / (R + G + epsilon)
        
        # 12. NORM3 ( (Red - Blue) / (Red + Blue) )
        norm3 = (R - B) / (R + B + epsilon)
        
        # 13. SAVI (Soil Adjusted Vegetation Index)
        L_savi = 0.5 # Common value for L
        savi = ((NIR - R) / (NIR + R + L_savi + epsilon)) * (1 + L_savi)
        
        # 14. LAI (Leaf Area Index - using the provided empirical formula)
        # (3.618 * 2.5 * (NIR - R)) / (NIR + 6 * R - 7.5 * B + 1) - 0.118
        # This formula is specific and might be from a particular study/sensor.
        # Note: EVI often used as a base for LAI, this formula resembles EVI structure.
        # Denominator: NIR + C1*R - C2*B + L_evi
        # Original EVI: G_factor * (NIR - R) / (NIR + C1*R - C2*B + L_evi)
        # LAI formula: k * EVI_like_term + c
        # where EVI_like_term is (NIR - R) / (NIR + 6R - 7.5B + 1)
        # and k = 3.618 * 2.5
        # and c = -0.118
        
        lai_numerator = 3.618 * 2.5 * (NIR - R)
        lai_denominator = NIR + 6.0 * R - 7.5 * B + 1.0 + epsilon # Added epsilon
        lai = (lai_numerator / lai_denominator) - 0.118

        # 15. Reflective Index (PSRI) Blight -> Higher PSRI value
        psri = (R - B) / RE

    vis_all = np.stack((
        ndvi, ndre, gndvi, ci_re, vari, evi2, ngrdi, 
        bgi_custom, gli_custom, dvi, sr_re, norm2, norm3, savi, lai, psri
    ), axis=0)
    
    return vis_all

def save_numpy_as_geotiff(output_path, image_array, meta, transform, crs):
    # Update metadata if needed (e.g. shape, data type)
    meta.update({
        "transform": transform,
        "crs": crs,
        "dtype": image_array.dtype,
        "count": image_array.shape[0] if image_array.ndim == 3 else 1,
        "nodata": meta.get('nodata', None)  # Keep existing nodata value if present
    })

    with rasterio.open(output_path, 'w', **meta) as dst:
        if image_array.ndim == 2:
            dst.write(image_array, 1)  # Single band
        else:
            dst.write(image_array)     # Multi-band

def resample_rgb_to_master_grid(master_path, # Path to master Red band for grid info
                                slave_folder,
                                output_folder):
    """
    Resamples slave bands to match the grid of the master band.
    """
    output_paths = [os.path.join(output_folder, os.path.basename(slave_band_path))
                    for slave_band_path in sorted(os.listdir(slave_folder))]
    
    os.makedirs(output_folder, exist_ok=True) # Create output folder if it doesn't exist
    
    try:
        with rasterio.open(master_path) as master_ds_ref: # For grid definition
            dst_crs = master_ds_ref.crs
            dst_transform = master_ds_ref.transform
            dst_height = master_ds_ref.height
            dst_width = master_ds_ref.width

        resampled_bands_data = []

        for i, slave_band_file in enumerate(sorted(os.listdir(slave_folder))):
            slave_band_path = os.path.join(slave_folder, slave_band_file)
            with rasterio.open(slave_band_path) as slave_ds:
                dst_profile = slave_ds.profile.copy() # Start with slave's profile
                dst_profile.update({ # Override geometric properties with master's
                    'crs': dst_crs,
                    'transform': dst_transform,
                    'width': dst_width,
                    'height': dst_height,
                    'count': 1, # Resampling band by band
                    # 'nodata': slave_ds.nodata # Keep slave's nodata
                })

                resampled_band_array = np.empty((dst_height, dst_width), dtype=slave_ds.dtypes[0])
                
                reproject(
                    source=rasterio.band(slave_ds, 1), # Read the first band of this slave TIF
                    destination=resampled_band_array,
                    src_transform=slave_ds.transform,
                    src_crs=slave_ds.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest
                )
                
                # Save individual resampled band
                with rasterio.open(output_paths[i], 'w', **dst_profile) as dst:
                    dst.write(resampled_band_array, 1)
                print(f"Resampled slave band saved to: {output_paths[i]}")
                resampled_bands_data.append(resampled_band_array)
        return
    
    except Exception as e:
        raise Exception(f"Error during resampling: {e}")
