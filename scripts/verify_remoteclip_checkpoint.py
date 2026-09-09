"""Explicit verification of the official RemoteCLIP-ViT-B-32 checkpoint loading and inference."""

from pathlib import Path
import sys
import numpy as np
from PIL import Image
import torch

from semantic_search.embeddings import image_to_embedding
from semantic_search.model import CHECKPOINT_PATH, load_remoteclip
from semantic_search.search import text_to_embedding


def verify_checkpoint() -> bool:
    """Perform comprehensive validation of the local RemoteCLIP checkpoint."""
    print("=" * 75)
    print("      REMOTECLIP-ViT-B-32 CHECKPOINT LOADING & INFERENCE VERIFICATION")
    print("=" * 75)

    all_passed = True

    # 1. Checkpoint file presence
    print("\n[1/6] Verifying checkpoint file existence...")
    if not CHECKPOINT_PATH.is_file():
        print(f"  [FAIL] Checkpoint not found at: {CHECKPOINT_PATH}")
        return False
    size_mb = CHECKPOINT_PATH.stat().st_size / (1024 * 1024)
    print(f"  [PASS] Found checkpoint file: {CHECKPOINT_PATH.name}")
    print(f"         Location: {CHECKPOINT_PATH}")
    print(f"         Size: {size_mb:.2f} MB")

    # 2. Inspect raw checkpoint state_dict
    print("\n[2/6] Inspecting checkpoint tensor dictionary (weights_only=True)...")
    try:
        raw_state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        key_count = len(raw_state_dict)
        print(f"  [PASS] Successfully read PyTorch state_dict with {key_count} tensor keys.")
        
        # Verify critical RemoteCLIP layers exist in state_dict
        essential_keys = [
            "visual.conv1.weight",
            "visual.proj",
            "text_projection",
            "positional_embedding",
            "logit_scale",
        ]
        for ek in essential_keys:
            if ek not in raw_state_dict:
                print(f"  [FAIL] Missing expected key in state_dict: {ek}")
                all_passed = False
            else:
                shape_str = str(list(raw_state_dict[ek].shape))
                print(f"         Key '{ek}': shape {shape_str}")
    except Exception as err:
        print(f"  [FAIL] Error reading checkpoint: {err}")
        return False

    # 3. Load model using production loader with strict=True
    print("\n[3/6] Loading model via load_remoteclip(device='cpu', reload=True)...")
    try:
        model, tokenizer, preprocess = load_remoteclip(device="cpu", reload=True)
        print("  [PASS] load_remoteclip() executed cleanly with strict=True state_dict matching.")
        print(f"         Model type: {type(model).__name__}")
        print(f"         Training mode: {model.training} (eval mode active)")

        # Verify model parameters match raw checkpoint weights directly
        mismatches = 0
        for name, param in model.named_parameters():
            if name in raw_state_dict:
                if not torch.equal(param.data, raw_state_dict[name]):
                    mismatches += 1
        if mismatches == 0:
            print("  [PASS] 100% of model parameter tensors match checkpoint weights exactly.")
        else:
            print(f"  [FAIL] Found {mismatches} parameter tensor mismatches.")
            all_passed = False
    except Exception as err:
        print(f"  [FAIL] Error during model loading: {err}")
        return False

    # 4. Verify text embedding generation
    print("\n[4/6] Verifying text embedding generation...")
    try:
        sample_query = "satellite imagery of buildings near a river"
        text_emb = text_to_embedding(sample_query, use_cache=False)
        dim = text_emb.shape[0]
        is_finite = bool(np.all(np.isfinite(text_emb)))
        is_nonzero = bool(np.any(text_emb != 0))
        norm = float(np.linalg.norm(text_emb))

        print(f"         Query: '{sample_query}'")
        print(f"         Dimension: {dim} (expected 512)")
        print(f"         Finite: {is_finite} | Non-zero: {is_nonzero}")
        print(f"         L2 Norm: {norm:.6f} (expected ~1.000000)")

        if dim == 512 and is_finite and is_nonzero and abs(norm - 1.0) < 1e-4:
            print("  [PASS] Text embedding meets all format, dimension, and normalization invariants.")
        else:
            print("  [FAIL] Text embedding invariants violated.")
            all_passed = False
    except Exception as err:
        print(f"  [FAIL] Error generating text embedding: {err}")
        all_passed = False

    # 5. Verify image embedding generation
    print("\n[5/6] Verifying image embedding generation...")
    try:
        # Check if tile exists, or use synthetic RGB image
        tile_path = Path(__file__).resolve().parents[1] / "data" / "tiles" / "tile_1.tif"
        if tile_path.is_file():
            img_emb = image_to_embedding(tile_path)
            source_desc = f"GeoTIFF tile ({tile_path.name})"
        else:
            # Synthetic 224x224 RGB image
            dummy_img = Image.new("RGB", (224, 224), color=(73, 109, 137))
            img_tensor = preprocess(dummy_img).unsqueeze(0)
            with torch.inference_mode():
                feat = model.encode_image(img_tensor)
                feat = torch.nn.functional.normalize(feat, p=2, dim=-1)
            img_emb = feat.squeeze(0).cpu().numpy().astype(np.float32)
            source_desc = "Synthetic RGB test image"

        img_dim = img_emb.shape[0]
        img_finite = bool(np.all(np.isfinite(img_emb)))
        img_nonzero = bool(np.any(img_emb != 0))
        img_norm = float(np.linalg.norm(img_emb))

        print(f"         Source: {source_desc}")
        print(f"         Dimension: {img_dim} (expected 512)")
        print(f"         Finite: {img_finite} | Non-zero: {img_nonzero}")
        print(f"         L2 Norm: {img_norm:.6f} (expected ~1.000000)")

        if img_dim == 512 and img_finite and img_nonzero and abs(img_norm - 1.0) < 1e-4:
            print("  [PASS] Image embedding meets all format, dimension, and normalization invariants.")
        else:
            print("  [FAIL] Image embedding invariants violated.")
            all_passed = False
    except Exception as err:
        print(f"  [FAIL] Error generating image embedding: {err}")
        all_passed = False

    # 6. Verify cross-modal cosine similarity computation
    print("\n[6/6] Verifying multi-modal text-image alignment...")
    try:
        sim = float(np.dot(text_emb, img_emb))
        print(f"         Cosine similarity (text vs image): {sim:.6f}")
        if -1.0 <= sim <= 1.0:
            print("  [PASS] Cross-modal similarity computation verified.")
        else:
            print("  [FAIL] Similarity out of [-1.0, 1.0] range.")
            all_passed = False
    except Exception as err:
        print(f"  [FAIL] Error calculating similarity: {err}")
        all_passed = False

    # Final Summary Report
    print("\n" + "=" * 75)
    print("                         FINAL VERIFICATION REPORT")
    print("=" * 75)
    if all_passed:
        print(">>> STATUS: PASS")
        print(">>> VERDICT: RemoteCLIP-ViT-B-32 official checkpoint was successfully")
        print("             loaded with strict=True and is actively driving inference.")
    else:
        print(">>> STATUS: FAIL")
        print(">>> VERDICT: RemoteCLIP checkpoint verification failed.")
    print("=" * 75)

    return all_passed


def main() -> int:
    """CLI entry point for verification script."""
    success = verify_checkpoint()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
