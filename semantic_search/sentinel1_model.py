"""Sentinel-1 SAR feature extractor and embedding pipeline.

This module provides a dedicated, isolated feature extraction and embedding model
for Sentinel-1 dual-polarization (VV/VH/ratio) SAR composites.
Produces 512-dimensional normalized vectors compatible with Qdrant cosine similarity.
"""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any

import numpy as np
import open_clip
from PIL import Image
import torch


MODEL_NAME = "ViT-B-32"
CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "sentinel1"
    / "sentinel1_sar_model.pt"
)

_SAR_MODEL_CACHE_LOCK = threading.Lock()
_CACHED_SAR_MODEL_BUNDLE: dict[str, tuple[Any, Any, Any]] = {}


def clear_sentinel1_model_cache() -> None:
    """Clear in-memory cached Sentinel-1 model instances."""
    with _SAR_MODEL_CACHE_LOCK:
        _CACHED_SAR_MODEL_BUNDLE.clear()


def load_sentinel1_model(
    device: str | torch.device = "cpu",
    reload: bool = False,
) -> tuple[Any, Any, Any]:
    """Load Sentinel-1 SAR embedding model (ViT-B-32 backbone) for 512-D vector extraction.

    Thread-safe and cached. Falls back to pretrained weights if dedicated SAR weights are not present.
    """
    dev_key = str(device)
    with _SAR_MODEL_CACHE_LOCK:
        if not reload and dev_key in _CACHED_SAR_MODEL_BUNDLE:
            return _CACHED_SAR_MODEL_BUNDLE[dev_key]

        checkpoint_candidates = [
            CHECKPOINT_PATH,
            Path(__file__).resolve().parents[1] / "models" / "remoteclip" / "RemoteCLIP-ViT-B-32.pt",
            Path(__file__).resolve().parents[1] / "checkpoints" / "RemoteCLIP-ViT-B-32.pt",
        ]
        ckpt_path = next((p for p in checkpoint_candidates if p.is_file()), None)

        if ckpt_path is not None:
            model, _, preprocess = open_clip.create_model_and_transforms(
                MODEL_NAME, pretrained=None, device=device
            )
            tokenizer = open_clip.get_tokenizer(MODEL_NAME)
            checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
            model.load_state_dict(checkpoint, strict=True)
        else:
            model, _, preprocess = open_clip.create_model_and_transforms(
                MODEL_NAME, pretrained="laion2b_s34b_b79k", device=device
            )
            tokenizer = open_clip.get_tokenizer(MODEL_NAME)

        model.eval()
        bundle = (model, tokenizer, preprocess)
        _CACHED_SAR_MODEL_BUNDLE[dev_key] = bundle
        return bundle


def extract_sentinel1_image_embedding(
    image: Image.Image | np.ndarray | str | Path,
    device: str | torch.device = "cpu",
) -> np.ndarray:
    """Extract a unit-normalized 512-D embedding from a Sentinel-1 SAR tile/image.

    Accepts PIL Image, uint8 NumPy array (H, W, 3), or file path.
    """
    if image is None:
        raise ValueError("Image cannot be None")

    if isinstance(image, (str, Path)):
        p = Path(image)
        if not p.is_file():
            raise FileNotFoundError(f"Image file not found: {p}")
        import rasterio
        try:
            with rasterio.open(p) as src:
                if src.count >= 3:
                    bands = [src.read(i) for i in (1, 2, 3)]
                    arr = np.stack(bands, axis=-1)
                elif src.count == 2:
                    b1 = src.read(1)
                    b2 = src.read(2)
                    arr = np.stack([b1, b2, b1], axis=-1)
                else:
                    b1 = src.read(1)
                    arr = np.stack([b1, b1, b1], axis=-1)
                if arr.dtype != np.uint8:
                    from semantic_search.sentinel1 import normalize_sar_to_uint8
                    arr = normalize_sar_to_uint8(arr)
                pil_img = Image.fromarray(arr.astype(np.uint8))
        except Exception:
            pil_img = Image.open(p).convert("RGB")
    elif isinstance(image, np.ndarray):
        if image.dtype != np.uint8:
            from semantic_search.sentinel1 import normalize_sar_to_uint8
            image = normalize_sar_to_uint8(image)
        pil_img = Image.fromarray(image.astype(np.uint8))
    elif isinstance(image, Image.Image):
        pil_img = image.convert("RGB")
    else:
        raise TypeError(f"Unsupported image type: {type(image)}")

    model, _, preprocess = load_sentinel1_model(device=device)
    tensor = preprocess(pil_img).unsqueeze(0).to(device)

    with torch.inference_mode():
        features = model.encode_image(tensor)
        normalized = torch.nn.functional.normalize(features, p=2, dim=-1)

    return normalized.squeeze(0).cpu().numpy().astype(np.float32)


def extract_sentinel1_text_embedding(
    query: str,
    device: str | torch.device = "cpu",
) -> np.ndarray:
    """Extract a unit-normalized 512-D embedding for natural language search queries against SAR data using prompt ensembling."""
    cleaned = " ".join(query.strip().split())
    if not cleaned:
        raise ValueError("Search query must be a non-empty string.")

    model, tokenizer, _ = load_sentinel1_model(device=device)
    prompts = [
        f"synthetic aperture radar satellite imagery of {cleaned}",
        f"SAR satellite view of {cleaned}",
        f"radar backscatter satellite photo of {cleaned}",
        cleaned,
    ]
    tokens = tokenizer(prompts).to(device)

    with torch.inference_mode():
        features = model.encode_text(tokens)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)
        mean_feature = normalized_features.mean(dim=0, keepdim=True)
        final_embedding = torch.nn.functional.normalize(mean_feature, p=2, dim=-1)

    return final_embedding.squeeze(0).cpu().numpy().astype(np.float32)
