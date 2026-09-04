import rasterio
import numpy as np
import matplotlib.pyplot as plt

# Paths to your downloaded Landsat / Sentinel bands
red_band_path = "LC09_L2SP_138044_20260109_20260110_02_T1_SR_B4.TIF"    # Red
green_band_path = "LC09_L2SP_138044_20260109_20260110_02_T1_SR_B3.TIF"  # Green
blue_band_path = "LC09_L2SP_138044_20260109_20260110_02_T1_SR_B2.TIF"   # Blue

def read_and_normalize(band_path):
    with rasterio.open(band_path) as src:
        band = src.read(1).astype(np.float32)
        
        # Mask out nodata / invalid pixels
        band[band <= 0] = np.nan
        
        # 2% to 98% percentile stretch to remove the darkness
        p2, p98 = np.nanpercentile(band, (2, 98))
        stretched = np.clip((band - p2) / (p98 - p2), 0, 1)
        
        # Replace NaNs with 0
        stretched = np.nan_to_num(stretched)
        return stretched

# Read and stretch each band
r = read_and_normalize(red_band_path)
g = read_and_normalize(green_band_path)
b = read_and_normalize(blue_band_path)

# Stack into an RGB array
rgb_image = np.dstack((r, g, b))

# Display the true-color image
plt.figure(figsize=(10, 10))
plt.imshow(rgb_image)
plt.axis("off")
plt.title("True Color Satellite View")
plt.show()