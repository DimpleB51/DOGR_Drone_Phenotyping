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

def calculate_VIs(data):
    ''' 
    Calculate Vegetation Indices (VIs) from the data.
    make sure data has channels in the order: [R, G, B, NIR, RE, PANCHRO]
                                               0  1  2   3    4      5

    Returns: a numpy array of shape (8, height, width) containing the VIs
    '''
    # Assuming the data is in the format [R, G, B, NIR, RE, PANCHRO]
    
    # calculate VIs
    # ndvi = (data[:, :, 3] - data[:, :, 0]) / (data[:, :, 3] + data[:, :, 0])
    # gndvi = (data[..., 3] - data[..., 1]) / (data[..., 3] + data[..., 1])
    # ndre = (data[..., 3] - data[..., 4]) / (data[..., 3] + data[..., 4])
    # ci_re = (data[..., 3] - data[..., 4]) - 1
    # vari = (data[..., 1] - data[..., 0]) / (data[..., 1] + data[..., 0] - data[..., 2])
    # evi2 = 2.5 * (data[..., 3] - data[..., 0]) / (data[..., 3] + 2.4 * data[..., 0] + 1)
    # # MCARI = [(RedEdge - Red) - 0.2 * (RedEdge - Green)] * (RedEdge / Red)
    # mcari = ((data[..., 4] - data[..., 0]) - 0.2 * (data[..., 4] - data[..., 1])) * (data[..., 4] / data[..., 0])
    # norm2 = (data[..., 0] - data[..., 1]) / (data[..., 0] + data[..., 1])


    # calculate VIs
    ndvi = (data[3] - data[0]) / (data[3] + data[0])
    gndvi = (data[3] - data[1]) / (data[3] + data[1])
    ndre = (data[3] - data[4]) / (data[3] + data[4])
    ci_re = (data[3] - data[4]) - 1
    vari = (data[1] - data[0]) / (data[1] + data[0] - data[2])
    evi2 = 2.5 * (data[3] - data[0]) / (data[3] + 2.4 * data[0] + 1)
    # MCARI = [(RedEdge - Red) - 0.2 * (RedEdge - Green)] * (RedEdge / Red)
    mcari = ((data[4] - data[0]) - 0.2 * (data[4] - data[1])) * (data[4] / data[0])
    norm2 = (data[0] - data[1]) / (data[0] + data[1])
    
    vis = np.stack((ndvi, gndvi, ndre, ci_re, vari, evi2, mcari, norm2), axis=0)
    print("VIs shape:", vis.shape)
    return vis

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
