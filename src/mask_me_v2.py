import numpy as np
import rasterio
from rasterio import features
from rasterio.mask import mask as rio_mask
import os

import geopandas as gpd
# ********************************************************************

def load_tif_numpy_with_meta(tiff_path):
    with rasterio.open(tiff_path) as dataset:
        image_array = dataset.read()    
        if image_array.ndim == 2:
            image_array = image_array[np.newaxis, ...]
        
        meta = dataset.meta.copy()
        transform = dataset.transform
        crs = dataset.crs
    return image_array, meta, transform, crs

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
    
    print(f"Saved region: {output_path}")

try:
    from compressor import compress
    from PIL import Image
    COMPRESSOR_AVAILABLE = True
except ImportError:
    COMPRESSOR_AVAILABLE = False
    print("Warning: 'compressor' or 'PIL' module not found. PNG saving will not be available.")


def tif_to_aoi_pipeline(tif_path, vector_regions_path, output_dir, region_id_col='region_id', compress_save=False):
    image_array, meta, transform, crs = load_tif_numpy_with_meta(tif_path)
    
    regions_gdf = gpd.read_file(vector_regions_path)
    if regions_gdf.crs != crs:
        print(f"Reprojecting regions from {regions_gdf.crs} to {crs} (image CRS)")
        regions_gdf = regions_gdf.to_crs(crs)
    
    regions_for_processing = []
    for _, row in regions_gdf.iterrows():
        regions_for_processing.append({'label': row[region_id_col], 'geometry': row.geometry})

    base_output_name = os.path.splitext(os.path.basename(tif_path))[0]
    specific_output_dir = os.path.join(output_dir, base_output_name)
    os.makedirs(specific_output_dir, exist_ok=True)

    image_h, image_w = image_array.shape[1], image_array.shape[2]

    for region_info in regions_for_processing:
        label = region_info['label']
        polygon = region_info['geometry']

        # --- Option 1: Save the masked array (full extent, values outside mask are NoData) ---
        mask = create_mask_from_georeferenced_polygon(
            polygon,
            (image_h, image_w),
            transform,
            crs,
            regions_gdf.crs
        )
        
        masked_full_extent_array = apply_mask_to_array(image_array, mask, nodata_value=meta.get('nodata', np.nan))
        file_name_tif = os.path.join(specific_output_dir, f"{label}_VIs.tif")
        
        if compress_save and COMPRESSOR_AVAILABLE:
            try:
                if masked_full_extent_array.ndim == 3:
                    img_to_compress = masked_full_extent_array[0] # Example: compress first band
                else:
                    img_to_compress = masked_full_extent_array

                img_8bit = compress(img_to_compress) # Your custom function
                out_file_png = os.path.join(specific_output_dir, f"region_{label}.png")
                Image.fromarray(img_8bit).save(out_file_png)
                print(f"Saved compressed region (PNG): {out_file_png}")
            except Exception as e:
                print(f"Could not compress and save PNG for {label}: {e}")
                # Fallback to TIF or skip
                save_masked_array_as_tif(masked_full_extent_array, file_name_tif, meta, transform, nodata_value=meta.get('nodata', np.nan))

        else:
            save_masked_array_as_tif(masked_full_extent_array, file_name_tif, meta, transform, nodata_value=meta.get('nodata', np.nan))
        break

        # --- Option 2: Crop to the polygon's extent AND mask (More common for region outputs) ---
        # This would use rasterio.mask.mask
        # from rasterio.mask import mask as rio_mask
        # try:
        #     with rasterio.open(tif_path) as src_for_crop: # Re-open to use with rio_mask
        #         # Ensure polygon is in a list of GeoJSON-like dicts
        #         shapes_for_crop = [polygon.__geo_interface__]
        #         cropped_array, cropped_transform = rio_mask(src_for_crop, shapes_for_crop, crop=True, nodata=src_for_crop.nodata)
            
        #     # Update metadata for the cropped image
        #     cropped_meta = meta.copy()
        #     cropped_meta.update({
        #         "height": cropped_array.shape[1],
        #         "width": cropped_array.shape[2],
        #         "transform": cropped_transform,
        #         "count": cropped_array.shape[0], # Number of bands
        #         "dtype": str(cropped_array.dtype),
        #         "nodata": src_for_crop.nodata # Use original nodata
        #     })
        #     file_name_cropped_tif = os.path.join(specific_output_dir, f"{label}_VIs_cropped.tif")
        #     with rasterio.open(file_name_cropped_tif, "w", **cropped_meta) as dst:
        #         dst.write(cropped_array)
        #     print(f"Saved CROPPED region: {file_name_cropped_tif}")
        # except Exception as e:
        #     print(f"Error cropping region {label}: {e}")

    # *****************************************************************************************

# Example usage:
if __name__ == "__main__":
    input_tif_multiband = '/raid/biplab/souravr/TIH/CROP/data/this_better_work.tif' # Your 8-band VI TIF
    vector_regions_file = '/raid/biplab/souravr/TIH/CROP/data/field_regions.gpkg'
    output_main_dir = '/raid/biplab/souravr/TIH/CROP/mot'
    region_id_attribute_column = 'region_id' 

    tif_to_aoi_pipeline(
        input_tif_multiband,
        vector_regions_file,
        output_main_dir,
        region_id_col=region_id_attribute_column,
        compress_save=False
    )
