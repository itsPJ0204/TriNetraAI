import os
import cv2
import numpy as np
import rasterio

def read_satellite_image(file_path: str) -> np.ndarray:
    """
    Reads standard images or multi-band GeoTIFFs (.tif).
    Normalizes 16-bit satellite reflectances to standard 8-bit RGB (H, W, 3).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image not found at path: {file_path}")

    if file_path.lower().endswith(('.tif', '.tiff')):
        with rasterio.open(file_path) as src:
            if src.count >= 3:
                arr = src.read([1, 2, 3])
                arr = np.transpose(arr, (1, 2, 0))
            else:
                arr = src.read(1)
                arr = np.stack([arr, arr, arr], axis=-1)

            if arr.dtype == np.uint16 or arr.max() > 255:
                p2, p98 = np.percentile(arr, (2, 98))
                arr = np.clip((arr - p2) / (p98 - p2 + 1e-5) * 255.0, 0, 255).astype(np.uint8)
            else:
                arr = arr.astype(np.uint8)
            return arr

    img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to decode image: {file_path}")
    
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    return img

def to_tensor(img_arr: np.ndarray, target_size: tuple = (256, 256), device: str = "cpu"):
    import torch
    resized = cv2.resize(img_arr, target_size, interpolation=cv2.INTER_LINEAR)
    tensor = torch.from_numpy(resized).permute(2, 0, 1).unsqueeze(0).float() / 255.0
    
    mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    tensor = (tensor - mean) / std

    return tensor.to(device)
