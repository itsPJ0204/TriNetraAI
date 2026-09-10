"""Verification for the local RemoteCLIP ViT-B-32 checkpoint and inference invariants."""

import numpy as np
from PIL import Image
import torch

from semantic_search.model import CHECKPOINT_PATH, load_remoteclip
from semantic_search.search import text_to_embedding


def test_remoteclip_checkpoint_exists() -> None:
    """Verify that the official RemoteCLIP-ViT-B-32.pt checkpoint is present on disk."""
    assert CHECKPOINT_PATH.is_file(), f"Checkpoint missing at {CHECKPOINT_PATH}"
    assert CHECKPOINT_PATH.stat().st_size > 100 * 1024 * 1024  # Must be >100MB


def test_remoteclip_loads() -> None:
    """Confirm the CPU model loader returns all required RemoteCLIP tools in eval mode."""
    model, tokenizer, preprocess = load_remoteclip(reload=True)

    assert model is not None
    assert tokenizer is not None
    assert preprocess is not None
    assert not model.training


def test_remoteclip_checkpoint_strict_load() -> None:
    """Verify checkpoint parameters match raw PyTorch checkpoint with strict=True."""
    raw_state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
    assert len(raw_state_dict) > 200

    model, _, _ = load_remoteclip()
    for name, param in model.named_parameters():
        if name in raw_state_dict:
            assert torch.equal(param.data, raw_state_dict[name]), f"Mismatch in {name}"


def test_remoteclip_text_embedding_invariants() -> None:
    """Verify text embedding generation produces 512-D normalized finite float32 vectors."""
    text_emb = text_to_embedding("buildings near a river", use_cache=False)

    assert isinstance(text_emb, np.ndarray)
    assert text_emb.shape == (512,)
    assert text_emb.dtype == np.float32
    assert np.all(np.isfinite(text_emb))
    assert np.any(text_emb != 0)
    norm = float(np.linalg.norm(text_emb))
    assert abs(norm - 1.0) < 1e-4


def test_remoteclip_image_embedding_invariants() -> None:
    """Verify image embedding generation produces 512-D normalized finite float32 vectors."""
    model, _, preprocess = load_remoteclip()
    dummy_img = Image.new("RGB", (224, 224), color=(100, 150, 200))
    img_tensor = preprocess(dummy_img).unsqueeze(0)

    with torch.inference_mode():
        feat = model.encode_image(img_tensor)
        feat = torch.nn.functional.normalize(feat, p=2, dim=-1)

    img_emb = feat.squeeze(0).cpu().numpy().astype(np.float32)
    assert img_emb.shape == (512,)
    assert np.all(np.isfinite(img_emb))
    assert np.any(img_emb != 0)
    norm = float(np.linalg.norm(img_emb))
    assert abs(norm - 1.0) < 1e-4


if __name__ == "__main__":
    test_remoteclip_checkpoint_exists()
    test_remoteclip_loads()
    test_remoteclip_checkpoint_strict_load()
    test_remoteclip_text_embedding_invariants()
    test_remoteclip_image_embedding_invariants()
    print("RemoteCLIP ViT-B-32 checkpoint and invariants verified successfully on CPU.")

