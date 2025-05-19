import numpy as np
import os
import rasterio

import matplotlib.pyplot as plt

import numpy as np

def load_tif_numpy_with_meta(tiff_path):
    """
    Load a TIFF file as a NumPy array using rasterio.
    returns the image array, metadata, transform, and CRS.
    """
    with rasterio.open(tiff_path) as dataset:
        image_array = dataset.read()
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
    '''
    # Assuming the data is in the format [R, G, B, NIR, RE, PANCHRO]
    
    # calculate VIs
    ndvi = (data[:, :, 3] - data[:, :, 0]) / (data[:, :, 3] + data[:, :, 0])
    gndvi = (data[..., 3] - data[..., 1]) / (data[..., 3] + data[..., 1])
    ndre = (data[..., 3] - data[..., 4]) / (data[..., 3] + data[..., 4])
    ci_re = (data[..., 3] - data[..., 4]) - 1
    vari = (data[..., 1] - data[..., 0]) / (data[..., 1] + data[..., 0] - data[..., 2])
    evi2 = 2.5 * (data[..., 3] - data[..., 0]) / (data[..., 3] + 2.4 * data[..., 0] + 1)
    # MCARI = [(RedEdge - Red) - 0.2 * (RedEdge - Green)] * (RedEdge / Red)
    mcari = ((data[..., 4] - data[..., 0]) - 0.2 * (data[..., 4] - data[..., 1])) * (data[..., 4] / data[..., 0])
    norm2 = (data[..., 0] - data[..., 1]) / (data[..., 0] + data[..., 1])
    
    vis = np.stack((ndvi, gndvi, ndre, ci_re, vari, evi2, mcari, norm2), axis=0)
    print("VIs shape:", vis.shape)
    return vis

def save_numpy_as_geotiff(output_path, image_array, meta, transform, crs):
    # Update metadata if needed (e.g. shape, data type)
    meta.update({
        "transform": transform,
        "crs": crs,
        "dtype": image_array.dtype,
        "count": image_array.shape[0] if image_array.ndim == 3 else 1
    })

    with rasterio.open(output_path, 'w', **meta) as dst:
        if image_array.ndim == 2:
            dst.write(image_array, 1)  # Single band
        else:
            dst.write(image_array)     # Multi-band

