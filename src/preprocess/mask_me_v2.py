import numpy as np
import rasterio
from rasterio import features
from rasterio.windows import Window
from rasterio.mask import mask as rio_mask
import os

import utils as utils
import geopandas as gpd
import config as cfg

def get_geometries_from_vector_file(vector_file_path, region_id_column='region_id'):
    """
    Loads geometries and their labels from a georeferenced vector file.

    Args:
        vector_file_path (str): Path to the GeoPackage, Shapefile, or GeoJSON file.
        region_id_column (str): The name of the attribute column in the vector file
                                that contains the region labels/IDs.

    Returns:
        list: A list of dictionaries, where each dictionary has 'label' and 'geometry'.
              Example: [{'label': 'R1T1', 'geometry': <shapely.geometry.Polygon object>}, ...]
    """
    gdf = gpd.read_file(vector_file_path)
    
    geometries_with_labels = []
    for index, row in gdf.iterrows():
        if row.geometry and region_id_column in row:
            geometries_with_labels.append({
                'label': row[region_id_column],
                'geometry': row.geometry
            })
        else:
            print(f"Warning: Skipping row {index} due to missing geometry or region ID column ('{region_id_column}').")
            
    return geometries_with_labels

def create_mask_from_georeferenced_polygon(polygon_geometry, image_shape, image_transform, image_crs, polygon_crs):
    """
    Creates a raster mask from a georeferenced polygon.

    Args:
        polygon_geometry (shapely.geometry.Polygon): The Shapely polygon object.
        image_shape (tuple): The shape of the output mask (height, width).
        image_transform (affine.Affine): The affine transform of the reference image.
        image_crs (rasterio.crs.CRS): The CRS of the reference image.
        polygon_crs (pyproj.CRS or str): The CRS of the input polygon_geometry.

    Returns:
        np.ndarray: A 2D boolean mask array.
    """
    if polygon_crs != image_crs:
        print(f"Reprojecting polygon from {polygon_crs} to {image_crs} (image CRS)")
        temp_gdf = gpd.GeoDataFrame([{'geometry': polygon_geometry}], crs=polygon_crs)
        temp_gdf = temp_gdf.to_crs(image_crs)
        polygon_geometry_transformed = temp_gdf.geometry.iloc[0]
    else:
        polygon_geometry_transformed = polygon_geometry
    

    # Rasterize the polygon. `features.rasterize` uses the __geo_interface__ protocol.
    # The `transform` argument tells rasterize how to map from geographic coordinates
    # of the polygon to the pixel grid of the output mask.
    mask_array = features.rasterize(
        [(polygon_geometry_transformed.__geo_interface__, 1)],
        out_shape=image_shape,
        transform=image_transform,
        fill=0, # Value for pixels outside the polygon
        dtype='uint8',
        all_touched=False # Or True, depending on your preference
    )
    return mask_array

def apply_mask_to_array(array, mask, nodata_value=np.nan):
    """
    Applies a mask to a NumPy array.

    Args:
        array (np.ndarray): Input array, can be (bands, height, width) or (height, width).
        mask (np.ndarray): 2D mask array (height, width), where 0 means mask out.
        nodata_value: Value to fill in masked areas.

    Returns:
        np.ndarray: Masked array.
    """
    masked_ndarray = array.copy()

    if masked_ndarray.ndim == 2: 
        masked_ndarray[mask == 0] = nodata_value
    elif masked_ndarray.ndim == 3: 
        for i in range(masked_ndarray.shape[0]):
            masked_ndarray[i, mask == 0] = nodata_value 
    else:
        raise ValueError(f"Array has unsupported dimensions: {masked_ndarray.ndim}")
        
    return masked_ndarray

def save_masked_array_as_tif(array, output_path, original_meta, original_transform, nodata_value=np.nan):
    """
    Saves a masked array (potentially multi-band) as a GeoTIFF.

    Args:
        array (np.ndarray): Array to save (bands, height, width).
        output_path (str): Path to save the output TIFF.
        original_meta (dict): Metadata from the original full TIFF.
        original_transform (affine.Affine): Affine transform of the original full TIFF.
                                            This will be used for the output.
        nodata_value: The NoData value to set in the output TIFF metadata.
    """
    meta = original_meta.copy()
    
    # The output array from rasterio.mask.mask (if we were to use it directly for cropping)
    # would have its own transform and shape. Here, we are saving the full extent
    # but with masked values. If you want to CROP to the polygon extent,
    # you would use rasterio.mask.mask first, which returns the cropped image AND its new transform.
    # For this pipeline, we are keeping the original extent and transform.
    
    meta.update({
        "driver": "GTiff",
        "height": array.shape[1], # array is (bands, height, width)
        "width": array.shape[2],
        "transform": original_transform,
        "count": array.shape[0],
        "dtype": str(array.dtype),
        "nodata": nodata_value if not (isinstance(nodata_value, float) and np.isnan(nodata_value)) else None
    })
    if isinstance(nodata_value, float) and np.isnan(nodata_value) and 'float' in str(array.dtype):
        meta['nodata'] = None

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(array)
    
    # print(f"Saved region: {output_path}")

def mask_crop_save(array, region_info, transform, meta, crs, output_dir, post_title, compress_save=False):
    # --- Option 1: Save the masked array (full extent, values outside mask are NoData) ---
    label = region_info.get('label')
    polygon = region_info['geometry']
    image_h, image_w = array.shape[1], array.shape[2]

    mask = create_mask_from_georeferenced_polygon(
        polygon,
        (image_h, image_w),
        transform,
        crs,
        crs
    )
    
    masked_full_extent_array = apply_mask_to_array(array, mask, nodata_value=meta.get('nodata', np.nan))
    
    true_points = np.argwhere(mask == 1)
    if true_points.size == 0:
        raise Exception(f"No true points found in the mask for '{label}.")

    min_row, min_col = true_points.min(axis=0)
    max_row, max_col = true_points.max(axis=0)

    crop_window = Window(min_col, min_row, (max_col - min_col + 1), (max_row - min_row + 1))
    cropped_transform = rasterio.windows.transform(crop_window, transform)
    # Crop the 8-Band VI Array
    array_cropped = masked_full_extent_array[
        :,
        crop_window.row_off : crop_window.row_off + crop_window.height,
        crop_window.col_off : crop_window.col_off + crop_window.width,
    ]

    # Crop the 2D pixel mask to the same window
    mask_cropped = mask[
        crop_window.row_off : crop_window.row_off + crop_window.height,
        crop_window.col_off : crop_window.col_off + crop_window.width
    ]

    num_vi_bands = array_cropped.shape[0]
    for i in range(num_vi_bands):
        array_cropped[i, :, :][mask_cropped == 0] = meta.get('nodata', np.nan)
    
    file_name_tif = os.path.join(output_dir, f"{label}_{post_title}.tif")
    save_masked_array_as_tif(array_cropped, file_name_tif, meta, cropped_transform, nodata_value=meta.get('nodata', np.nan))
    
    # file_name_tif = os.path.join(output_dir, f"u_{label}_VIs.tif")
    # utils.save_numpy_as_geotiff(file_name_tif, array_cropped, meta, transform, crs)
    
    if compress_save and COMPRESSOR_AVAILABLE:
        try:
            if array_cropped.ndim == 3:
                img_to_compress = array_cropped[0] # Example: compress first band
            else:
                img_to_compress = array_cropped

            img_directory = os.path.join(output_dir, 'compressed')
            os.makedirs(img_directory, exist_ok=True)

            img_8bit = compress(img_to_compress) # Your custom function
            out_file_png = os.path.join(img_directory, f"{label}.png")
            Image.fromarray(img_8bit).save(out_file_png)
            # print(f"Saved compressed region (PNG): {out_file_png}")
        except Exception as e:
            print(f"Could not compress and save PNG for {label}: {e}")

try:
    from compressor import compress
    from PIL import Image
    COMPRESSOR_AVAILABLE = True
except ImportError:
    COMPRESSOR_AVAILABLE = False
    print("Warning: 'compressor' or 'PIL' module not found. PNG saving will not be available.")

# Example usage:
if __name__ == "__main__":
    tif_file_path = 'PATH/TO/TIF/FILE.TIF' # Should be coregistered
    vector_file_path = os.path.join(cfg.ALL_DATA_DIR, 'field_regions.gpkg')
    output_dir = os.path.join(cfg.OUTPUT_DIR, 'regions')
    os.makedirs(output_dir, exist_ok=True)
    array, meta, transform, crs = utils.load_tif_numpy_with_meta(tif_file_path)
    
    regions_gdf = gpd.read_file(vector_file_path)
    if regions_gdf.crs != crs:
        print(f"Reprojecting regions from {regions_gdf.crs} to {crs} (image CRS)")
        regions_gdf = regions_gdf.to_crs(crs)
    
    regions_for_processing = []
    for _, row in regions_gdf.iterrows():
        regions_for_processing.append({'label': row['region_id'], 'geometry': row.geometry})

    for region in regions_for_processing:
        mask_crop_save(
            array,
            region,
            transform,
            meta,
            crs,
            output_dir,
            'test',
            True
        )