import json
import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import Polygon, mapping
from affine import Affine
import os
from compressor import compress
from PIL import Image

def load_tif_numpy_with_meta(tiff_path):
    with rasterio.open(tiff_path) as dataset:
        image_array = dataset.read(1)  # Single band assumed
        meta = dataset.meta.copy()
        transform = dataset.transform
        crs = dataset.crs
    return image_array, meta, transform, crs

def get_polygon_from_json(json_path):
    polygons = []
    with open(json_path, "r") as f:
        data = json.load(f)
    for shape in data["shapes"]:
        label = shape["label"]
        points = shape["points"]
        polygons.append(
            {
                'label': label,  
                'polygon': Polygon(points)
                }
            )
    return polygons

def create_mask_from_polygon(polygon, shape):
    mask = features.rasterize(
        [(mapping(polygon), 1)],
        out_shape=shape,
        transform=Affine.identity(),
        fill=0,
        dtype='uint8'
    )
    return mask

def apply_mask_to_array(array, mask, nodata=np.nan):
    masked_ndarray = array.copy()
    if masked_ndarray.ndim == 2:
        masked_ndarray[mask == 0] = nodata
    else:
        if masked_ndarray.shape[0] > masked_ndarray.shape[-1]:
            print(f'Array shape: {masked_ndarray.shape}')
            print("Transposing array to (bands, height, width)")
            masked_ndarray = np.transpose(masked_ndarray, (2, 0, 1))
            print(f'Array shape after transpose: {masked_ndarray.shape}')
        for i in range(masked_ndarray.shape[0]):
            masked_ndarray[i][mask == 0] = nodata

    return masked_ndarray

def save_masked_array(array, output_path, meta):
    meta = meta.copy()
    meta.update({
        "dtype": "float32",
        "count": 1,
        "nodata": np.nan
    })

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(array, 1)
    
    print(f"Saved region: {output_path}")

def tif_to_aoi_pipeline(tif_path, json_path, output_dir, compress_save=False):
    image_array, meta, transform, crs = load_tif_numpy_with_meta(tif_path)
    regions = get_polygon_from_json(json_path)

    output_path = os.path.join(output_dir, f"{os.path.basename(tif_path).split('.')[0]}")
    os.makedirs(output_path, exist_ok=True)

    for i, region in enumerate(regions):
        mask = create_mask_from_polygon(region['polygon'], image_array.shape)
        masked_array = apply_mask_to_array(image_array, mask)
        file_name = os.path.join(output_path, f"region_{region['label']}.tif")
        if compress_save:
            img_8bit = compress(masked_array)
            out_file = os.path.join(output_path, f"region_{region['label']}.png")
            Image.fromarray(img_8bit).save(out_file)
        else:
            save_masked_array(masked_array, file_name, meta)

# Example usage:
if __name__ == "__main__":
    # input_tif = '/raid/biplab/souravr/TIH/CROP/output/ndvi_output.tif'
    input_tif = '/raid/biplab/souravr/TIH/CROP/output/7Sept23_8_indices.tif'
    aoi_json = '/raid/biplab/souravr/TIH/CROP/data/trail1_regions.json'
    output_dir = '/raid/biplab/souravr/TIH/CROP/output'
    tif_to_aoi_pipeline(input_tif, aoi_json, output_dir)
