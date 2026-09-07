import os
import torch
import numpy as np
from src.preprocessor import to_tensor

class BITInferenceEngine:
    def __init__(self, checkpoint_path: str = "checkpoints/bit_levircd.pth"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.checkpoint_path = checkpoint_path
        self.model = None
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.checkpoint_path):
            raise FileNotFoundError(f"BIT weights not found at: {self.checkpoint_path}")

        try:
            from bit_core.networks import define_G
        except ImportError:
            try:
                from models.networks import define_G
            except ImportError:
                import sys
                sys.path.append(os.path.abspath("bit_core"))
                from networks import define_G

        print(f"[Temporal AI] Initializing BIT Model on {self.device}...")
        self.model = define_G(
            net_G='base_transformer_pos_s4_dd8',
            in_c=3,
            out_c=2
        )

        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        state_dict = checkpoint["state_dict"] if "state_dict" in checkpoint else checkpoint
        clean_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        
        self.model.load_state_dict(clean_state_dict, strict=False)
        self.model.to(self.device)
        self.model.eval()
        print("[Temporal AI] Model weights loaded successfully.")

    def predict(self, img_t1: np.ndarray, img_t2: np.ndarray) -> np.ndarray:
        t1 = to_tensor(img_t1, target_size=(256, 256), device=self.device)
        t2 = to_tensor(img_t2, target_size=(256, 256), device=self.device)

        with torch.no_grad():
            output = self.model(t1, t2)
            if isinstance(output, (list, tuple)):
                output = output[-1]
            
            pred = torch.argmax(output, dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
            pred_mask = pred * 255
            
        return pred_mask
