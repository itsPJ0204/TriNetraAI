"""
semantic_classifier.py — Semantic Change Classification Module
==============================================================
Determines WHAT the actual change is in each detected region using:
1. RemoteCLIP Zero-Shot Vision-Language Classifier (Rahim's Semantic AI architecture).
2. Robust Spectral & Morphological Transition Profiler (Zero-dependency fallback).
"""

import os
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

try:
    import torch
    import open_clip
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False

# Candidate remote-sensing land-cover categories and their natural prompt descriptions
CANDIDATE_CLASSES = [
    ("Building / Construction", "a satellite photo of a newly built building, concrete structure, or construction site"),
    ("Vegetation / Forest", "a satellite photo of dense trees, forest, or green vegetation"),
    ("Agricultural Land", "a satellite photo of cultivated farmland or agricultural crop field"),
    ("Bare Ground / Soil", "a satellite photo of barren soil, sand, or cleared dirt ground"),
    ("Road / Infrastructure", "a satellite photo of a paved asphalt road, highway, or runway"),
    ("Water Body / Flood", "a satellite photo of a river, lake, or flooded water body"),
    ("Industrial / Solar Farm", "a satellite photo of an industrial facility, factory, or solar panel farm"),
]

_CACHED_CLIP_BUNDLE = None

def get_clip_bundle(device="cpu"):
    """Loads RemoteCLIP / OpenCLIP model with caching."""
    global _CACHED_CLIP_BUNDLE
    if not HAS_CLIP:
        return None, None, None

    if _CACHED_CLIP_BUNDLE is not None:
        return _CACHED_CLIP_BUNDLE

    # Look for local RemoteCLIP checkpoint (from Rahim's Semantic AI path)
    checkpoint_candidates = [
        Path("models/remoteclip/RemoteCLIP-ViT-B-32.pt"),
        Path("../models/remoteclip/RemoteCLIP-ViT-B-32.pt"),
        Path("checkpoints/RemoteCLIP-ViT-B-32.pt"),
    ]
    ckpt_path = next((p for p in checkpoint_candidates if p.is_file()), None)

    try:
        if ckpt_path:
            print(f"[Semantic AI] Loading RemoteCLIP from {ckpt_path} on {device}...")
            model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained=None, device=device)
            tokenizer = open_clip.get_tokenizer("ViT-B-32")
            checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
            model.load_state_dict(checkpoint, strict=True)
        else:
            # Fallback to standard pretrained OpenCLIP ViT-B-32 (laion2b_s34b_b79k)
            print(f"[Semantic AI] Initializing OpenCLIP ViT-B-32 on {device}...")
            model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k", device=device)
            tokenizer = open_clip.get_tokenizer("ViT-B-32")

        model.eval()
        _CACHED_CLIP_BUNDLE = (model, tokenizer, preprocess)
        return _CACHED_CLIP_BUNDLE
    except Exception as e:
        print(f"[Warning] Could not initialize CLIP model ({e}). Using spectral classifier.")
        return None, None, None


def classify_patch_clip(patch_rgb: np.ndarray, model, tokenizer, preprocess, device="cpu") -> tuple[str, float]:
    """Zero-shot classification of a single image patch using RemoteCLIP."""
    pil_img = Image.fromarray(patch_rgb)
    img_tensor = preprocess(pil_img).unsqueeze(0).to(device)

    prompts = [desc for _, desc in CANDIDATE_CLASSES]
    text_tokens = tokenizer(prompts).to(device)

    with torch.no_grad():
        image_features = model.encode_image(img_tensor)
        text_features = model.encode_text(text_tokens)

        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1).squeeze(0)
        best_idx = similarity.argmax().item()
        confidence = float(similarity[best_idx].item())

    return CANDIDATE_CLASSES[best_idx][0], round(confidence, 3)


def classify_patch_spectral(patch_t1: np.ndarray, patch_t2: np.ndarray, bbox: dict) -> tuple[str, str, float, str]:
    """
    Fallback spectral & morphological transition classifier:
    Calculates greenness, brightness, edge density, and geometry.
    """
    # 1. Compute Brightness
    gray1 = cv2.cvtColor(patch_t1, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray2 = cv2.cvtColor(patch_t2, cv2.COLOR_RGB2GRAY).astype(np.float32)
    mean_bright_1 = float(np.mean(gray1))
    mean_bright_2 = float(np.mean(gray2))
    bright_diff = mean_bright_2 - mean_bright_1

    # 2. Compute Visible Greenness Index: (2*G - R - B) / (2*G + R + B + 1e-5)
    def greenness_index(img_rgb):
        r, g, b = img_rgb[:, :, 0].astype(float), img_rgb[:, :, 1].astype(float), img_rgb[:, :, 2].astype(float)
        return (2.0 * g - r - b) / (2.0 * g + r + b + 1e-5)

    vgi1 = float(np.mean(greenness_index(patch_t1)))
    vgi2 = float(np.mean(greenness_index(patch_t2)))
    vgi_diff = vgi2 - vgi1

    # 3. High Edge Density (indicative of built structures/foundations)
    edges2 = cv2.Canny(patch_t2, 50, 150)
    edge_density = float(np.sum(edges2 > 0) / (edges2.size + 1e-5))

    # 4. Aspect ratio (linear features like roads)
    aspect_ratio = max(bbox['w'], bbox['h']) / (min(bbox['w'], bbox['h']) + 1e-5)

    # Classification Rules
    if vgi1 > 0.05 and vgi_diff < -0.08:
        if bright_diff > 25 or edge_density > 0.12:
            return "Vegetation / Field", "New Construction / Building", 0.91, "Vegetation cleared and replaced by new structural building."
        else:
            return "Vegetation / Forest", "Cleared / Bare Land", 0.88, "Vegetation or tree canopy removed, exposing bare ground."

    elif bright_diff > 35 and edge_density > 0.10:
        return "Open Land / Soil", "New Construction / Built Structure", 0.92, "High-reflectance new building foundation or concrete structure erected."

    elif aspect_ratio > 3.5 and (bright_diff > 15 or bright_diff < -15):
        return "Open Terrain", "Road / Infrastructure", 0.86, "Linear corridor development or paved road expansion."

    elif mean_bright_2 < 30 and mean_bright_1 > 50:
        return "Land Surface", "Water Body / Flooding", 0.85, "Significant drop in reflectance indicative of water accumulation or flood."

    elif vgi_diff > 0.10:
        return "Bare Ground / Fallow", "Vegetation / Crops", 0.87, "Vegetation growth, crop plantation, or reforestation observed."

    elif abs(bright_diff) > 20:
        return "Ground Surface", "Surface Modification / Earthwork", 0.82, "Surface excavation, grading, or ground disturbance."

    else:
        return "Initial State", "Material / Structural Change", 0.78, "Physical change detected in surface texture and spectral reflectance."


def determine_semantic_change(
    img_t1: np.ndarray, 
    img_t2: np.ndarray, 
    bbox: dict,
    pad: int = 8
) -> dict:
    """
    Given full T1 and T2 images and a bounding box dict {x, y, w, h},
    determines WHAT the actual change is.
    """
    H, W = img_t2.shape[:2]
    x0 = max(0, bbox['x'] - pad)
    y0 = max(0, bbox['y'] - pad)
    x1 = min(W, bbox['x'] + bbox['w'] + pad)
    y1 = min(H, bbox['y'] + bbox['h'] + pad)

    crop_t1 = img_t1[y0:y1, x0:x1]
    crop_t2 = img_t2[y0:y1, x0:x1]

    if crop_t1.size == 0 or crop_t2.size == 0:
        return {
            "from_class": "Unknown",
            "to_class": "Modified Area",
            "transition": "Unknown -> Modified Area",
            "category": "Surface Modification",
            "confidence": 0.50,
            "description": "Area changed."
        }

    # Try RemoteCLIP
    model, tokenizer, preprocess = get_clip_bundle()
    if model is not None and tokenizer is not None and preprocess is not None:
        try:
            from_class, conf1 = classify_patch_clip(crop_t1, model, tokenizer, preprocess)
            to_class, conf2 = classify_patch_clip(crop_t2, model, tokenizer, preprocess)
            conf = round(float((conf1 + conf2) / 2.0), 2)

            if from_class == to_class:
                to_class = f"Modified {to_class}"

            # High-level category
            if "Building" in to_class:
                category = "New Construction / Built Structure"
                desc = f"Area transitioned from {from_class.lower()} into new structural construction / building."
            elif "Vegetation" in from_class and ("Bare" in to_class or "Building" in to_class):
                category = "Vegetation Loss / Land Clearing"
                desc = f"Vegetation or tree canopy removed ({from_class} -> {to_class})."
            elif "Water" in to_class:
                category = "Water Body / Flooding"
                desc = f"Water body expansion or flood accumulation ({from_class} -> {to_class})."
            elif "Road" in to_class:
                category = "Road / Infrastructure"
                desc = f"Linear transport infrastructure or paved road detected."
            elif "Vegetation" in to_class:
                category = "Vegetation Growth / Reforestation"
                desc = f"Green vegetation or crop growth observed ({from_class} -> {to_class})."
            else:
                category = f"{from_class} to {to_class}"
                desc = f"Semantic transition from {from_class} to {to_class}."

            return {
                "from_class": from_class,
                "to_class": to_class,
                "transition": f"{from_class} -> {to_class}",
                "category": category,
                "confidence": conf,
                "description": desc,
                "method": "RemoteCLIP_ZeroShot"
            }
        except Exception as e:
            print(f"[Semantic AI] RemoteCLIP classification error ({e}), falling back to spectral...")

    # Fallback to Spectral & Geometry Classifier
    from_class, to_class, conf, desc = classify_patch_spectral(crop_t1, crop_t2, bbox)
    return {
        "from_class": from_class,
        "to_class": to_class,
        "transition": f"{from_class} -> {to_class}",
        "category": to_class,
        "confidence": conf,
        "description": desc,
        "method": "Spectral_Geometry_Analysis"
    }
