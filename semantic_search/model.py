"""CPU-compatible loader for the official RemoteCLIP ViT-B-32 checkpoint."""

from pathlib import Path
import threading
from typing import Any

import open_clip
import torch


MODEL_NAME = "ViT-B-32"
CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "remoteclip"
    / "RemoteCLIP-ViT-B-32.pt"
)

_MODEL_CACHE_LOCK = threading.Lock()
_CACHED_MODEL_BUNDLE: dict[str, tuple[Any, Any, Any]] = {}


def clear_model_cache() -> None:
    """Clear in-memory cached model instances (useful for testing and memory release)."""
    with _MODEL_CACHE_LOCK:
        _CACHED_MODEL_BUNDLE.clear()


def load_remoteclip(
    device: str | torch.device = "cpu",
    reload: bool = False,
) -> tuple[Any, Any, Any]:
    """Load RemoteCLIP ViT-B-32 for inference and return model tools.

    The checkpoint must already be stored at ``models/remoteclip``. CPU is the
    default so the function works on machines without an NVIDIA GPU.

    Repeated calls within the same process safely reuse the cached model, tokenizer,
    and preprocessing transform unless reload=True is specified.
    """
    dev_key = str(device)

    with _MODEL_CACHE_LOCK:
        if not reload and dev_key in _CACHED_MODEL_BUNDLE:
            return _CACHED_MODEL_BUNDLE[dev_key]

        checkpoint_path = CHECKPOINT_PATH
        if not checkpoint_path.is_file():
            raise FileNotFoundError(
                f"RemoteCLIP checkpoint was not found at: {checkpoint_path}"
            )

        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=None, device=device
        )
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
        model.load_state_dict(checkpoint, strict=True)
        model.eval()

        bundle = (model, tokenizer, preprocess)
        _CACHED_MODEL_BUNDLE[dev_key] = bundle
        return bundle
