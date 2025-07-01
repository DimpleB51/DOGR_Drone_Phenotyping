import os
from PIL import Image
import numpy as np
import tifffile

def compress(single_band_array):
    # Handle NaNs and negatives
    single_band_array = np.nan_to_num(single_band_array, nan=0.0)
    single_band_array[single_band_array < 0] = 0

    # Normalize safely
    min_val = single_band_array.min()
    range_val = np.ptp(single_band_array)

    if range_val == 0:
        img_8bit = np.zeros_like(single_band_array, dtype=np.uint8)
    else:
        img_8bit = ((single_band_array - min_val) / (range_val + 1e-8) * 255).astype(np.uint8)
    
    return img_8bit


def compress_multi(tiffile, output_folder):
    base_file = os.path.basename(tiffile).split('.')[0]
    img = tifffile.imread(tiffile)  # Supports multi-band better than PIL

    if img.ndim == 2:  # Single band
        img = np.expand_dims(img, axis=0)  # Make it (1, H, W)
    elif img.ndim == 3 and img.shape[0] > img.shape[-1]:
        img = img.transpose(2, 0, 1)  # Ensure shape is (bands, H, W)

    output_folder = os.path.join(output_folder, f'{base_file}')
    os.makedirs(output_folder, exist_ok=True)
    print(f'Found {img.shape[0]} bands')
    for i, band in enumerate(img):
        img_8bit = compress(band)
        # Save preview
        out_file = os.path.join(output_folder, f'{str(i).zfill(2)}.png')
        try:
            Image.fromarray(img_8bit).save(out_file)
            print(f"Preview saved as {out_file}")
        except Exception as e:
            print(f"Error saving preview: {e}")
            print("Failed to save preview due to:", e)


def main():
    tiff_file = 'path/to/tiff_file'
    output_folder = 'path/to/output_folder'
    print(f'Processing {tiff_file}')
    compress_multi(
        tiff_file, 
        output_folder
    )

if __name__ == "__main__":
    main()