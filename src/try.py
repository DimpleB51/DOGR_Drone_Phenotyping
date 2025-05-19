import json
import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import Polygon, mapping

def load_tif_numpy_with_meta(tiff_path):
    with rasterio.open(tiff_path) as dataset:
        image_array = dataset.read(1)  # Single band assumed
        meta = dataset.meta.copy()
        transform = dataset.transform
        crs = dataset.crs
    return image_array, meta, transform, crs

def get_polygon_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    points = data["shapes"][0]["points"]
    return Polygon(points)

def create_mask_from_polygon(polygon, shape, transform):
    mask = features.rasterize(
        [(mapping(polygon), 1)],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype='uint8'
    )
    return mask

def apply_mask_to_array(array, mask):
    masked_array = array.copy().astype("float32")
    masked_array[mask == 0] = np.nan
    return masked_array

def save_masked_array(array, output_path, meta):
    meta = meta.copy()
    meta.update({
        "dtype": "float32",
        "count": 1,
        "nodata": np.nan
    })

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(array, 1)

def tif_to_aoi_pipeline(tif_path, json_path, output_path):
    image_array, meta, transform, crs = load_tif_numpy_with_meta(tif_path)
    polygon = get_polygon_from_json(json_path)
    mask = create_mask_from_polygon(polygon, image_array.shape, transform)
    masked_array = apply_mask_to_array(image_array, mask)
    save_masked_array(masked_array, output_path, meta)

# Example usage:
input_tif = '/raid/biplab/souravr/TIH/CROP/data/7Spet23/R1_7Sept23_index_blue.tif'
aoi_json = '/raid/biplab/souravr/TIH/CROP/data/bound_box.json'
output_tif = '/raid/biplab/souravr/TIH/CROP/output/try_ndvi.tif'
# tif_to_aoi_pipeline(input_tif, aoi_json, output_tif)

img, meta, transform, crs = load_tif_numpy_with_meta(input_tif)

# from rasterio.transform import from_origin

# transform = from_origin(382620.6114300000481308,2083649.6792300001252443)  # top-left x, top-left y, x-res, y-res
# crs = "EPSG:4326"  # WGS84 as dummy CRS

if crs is None:
    print ("CRS is None, setting to EPSG:4326")
    
meta.update({
    "transform": transform,
    "crs": 'EPSG:4326' if crs is None else crs,
})


with rasterio.open(output_tif, "w", **meta) as dst:
    dst.write(img, 1)
