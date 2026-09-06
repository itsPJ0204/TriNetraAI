"""Phase 2 verification for the local RemoteCLIP setup."""

from semantic_search.model import load_remoteclip


def test_remoteclip_loads() -> None:
    """Confirm the CPU model loader returns all required RemoteCLIP tools."""
    model, tokenizer, preprocess = load_remoteclip()

    assert model is not None
    assert tokenizer is not None
    assert preprocess is not None
    assert not model.training


if __name__ == "__main__":
    test_remoteclip_loads()
    print("RemoteCLIP ViT-B-32 loaded successfully on CPU.")
