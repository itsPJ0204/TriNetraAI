import os
import tifffile
import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(BASE_DIR, "sih_dataset", "year_1", "default.tif")

# Load multi-band TIFF (512, 512, 4) -> [B4 (Red), B3 (Green), B2 (Blue), B8 (NIR)]
img = tifffile.imread(img_path)

# Extract RGB bands (B04, B03, B02)
rgb = img[:, :, [0, 1, 2]].astype(np.float32)

# Normalize using 2% - 98% percentile stretch
p2, p98 = np.percentile(rgb, (2, 98))
if p98 > p2:
    rgb_stretched = np.clip((rgb - p2) / (p98 - p2), 0, 1)
else:
    rgb_stretched = np.clip(rgb / 10000.0, 0, 1)

plt.figure(figsize=(8, 8))
plt.imshow(rgb_stretched)
plt.title("Sentinel-2 True Color (RGB)")
plt.axis("off")
plt.show()
