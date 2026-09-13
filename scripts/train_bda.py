import os
import glob
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
import shapely.wkt
from shapely.geometry import Polygon

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

# Try to import our BDA Head from the main project
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
from src.semantic_classifier import BDASiameseHead

DATA_DIR = PROJECT_ROOT / "data" / "xview2" / "hold"

DAMAGE_MAP = {
    "no-damage": 0,
    "minor-damage": 1,
    "major-damage": 2,
    "destroyed": 3
}

class xView2Dataset(Dataset):
    def __init__(self, data_root, split="train", test_ratio=0.2, crop_size=128, padding=8):
        self.data_root = Path(data_root)
        self.crop_size = crop_size
        self.padding = padding
        
        self.transform = transforms.Compose([
            transforms.Resize((crop_size, crop_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])
        
        self.samples = []
        
        labels_dir = self.data_root / "labels"
        if not labels_dir.exists():
            print(f"[!] Warning: Labels directory not found at {labels_dir}")
            return
            
        post_jsons = sorted(glob.glob(str(labels_dir / "*_post_disaster.json")))
        
        # Split by image tile to avoid data leakage
        num_tiles = len(post_jsons)
        split_idx = int(num_tiles * (1 - test_ratio))
        
        if split == "train":
            target_jsons = post_jsons[:split_idx]
        else:
            target_jsons = post_jsons[split_idx:]
            
        print(f"[*] Parsing {len(target_jsons)} tiles for {split} split...")
        
        # We limit the number of tiles to parse to keep RAM reasonable and prototyping fast
        # (Change this limit if you want to train on the entire set)
        limit = min(50, len(target_jsons)) 
        
        for json_path in target_jsons[:limit]:
            post_json_path = Path(json_path)
            pre_json_path = post_json_path.parent / post_json_path.name.replace("_post_disaster", "_pre_disaster")
            
            post_img_path = self.data_root / "images" / post_json_path.name.replace(".json", ".png")
            pre_img_path = self.data_root / "images" / pre_json_path.name.replace(".json", ".png")
            
            if not pre_img_path.exists() or not post_img_path.exists():
                continue
                
            with open(post_json_path, 'r') as f:
                post_data = json.load(f)
                
            for feature in post_data["features"]["xy"]:
                props = feature["properties"]
                if props.get("feature_type") == "building":
                    subtype = props.get("subtype")
                    if subtype in DAMAGE_MAP:
                        wkt_poly = feature["wkt"]
                        poly = shapely.wkt.loads(wkt_poly)
                        minx, miny, maxx, maxy = poly.bounds
                        
                        self.samples.append({
                            "pre_img": str(pre_img_path),
                            "post_img": str(post_img_path),
                            "bbox": (int(minx), int(miny), int(maxx), int(maxy)),
                            "label": DAMAGE_MAP[subtype]
                        })
                        
        print(f"[+] Found {len(self.samples)} building crops for {split} set.")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # In a production environment, opening the full 1024x1024 image every time is slow.
        # But for prototyping and memory efficiency without pre-processing, we crop on the fly.
        pre_img = Image.open(sample["pre_img"]).convert("RGB")
        post_img = Image.open(sample["post_img"]).convert("RGB")
        
        minx, miny, maxx, maxy = sample["bbox"]
        
        # Apply padding
        w, h = pre_img.size
        minx = max(0, minx - self.padding)
        miny = max(0, miny - self.padding)
        maxx = min(w, maxx + self.padding)
        maxy = min(h, maxy + self.padding)
        
        pre_crop = pre_img.crop((minx, miny, maxx, maxy))
        post_crop = post_img.crop((minx, miny, maxx, maxy))
        
        pre_tensor = self.transform(pre_crop)
        post_tensor = self.transform(post_crop)
        
        label = torch.tensor(sample["label"], dtype=torch.long)
        
        return pre_tensor, post_tensor, label


def train_bda():
    print("="*50)
    print("Initializing Battle Damage Assessment (BDA) Training")
    print("="*50)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Using device: {device}")
    
    # 1. Datasets and Dataloaders
    print("\n[*] Loading Datasets...")
    train_dataset = xView2Dataset(DATA_DIR, split="train", test_ratio=0.2, crop_size=128)
    val_dataset = xView2Dataset(DATA_DIR, split="val", test_ratio=0.2, crop_size=128)
    
    if len(train_dataset) == 0 or len(val_dataset) == 0:
        print("[!] Dataset is empty. Make sure xView2 data is extracted in data/xview2/hold/")
        return
        
    train_loader = DataLoader(train_dataset, batch_size=1, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, num_workers=0)
    
    # 2. Model, Loss, Optimizer
    model = BDASiameseHead(in_channels=6).to(device)
    
    # xView2 is heavily imbalanced (mostly no-damage). 
    # Optional: We could use weighted CrossEntropy, but we'll stick to basic for now.
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    
    # 3. Early Stopping Parameters
    patience = 3
    best_val_loss = float('inf')
    epochs_no_improve = 0
    max_epochs = 100 # Effectively infinite, controlled by early stopping
    
    checkpoints_dir = PROJECT_ROOT / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)
    save_path = checkpoints_dir / "bda_head_xview2.pth"
    
    print("\n[*] Starting Training Loop (Early Stopping Enabled)...")
    
    for epoch in range(1, max_epochs + 1):
        # --- TRAIN ---
        model.train()
        train_loss = 0.0
        correct_train = 0
        total_train = 0
        
        for pre_t, post_t, labels in train_loader:
            pre_t, post_t, labels = pre_t.to(device), post_t.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(pre_t, post_t)
            
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * pre_t.size(0)
            _, predicted = torch.max(outputs.data, 1)
            total_train += labels.size(0)
            correct_train += (predicted == labels).sum().item()
            
        train_loss = train_loss / len(train_loader.dataset)
        train_acc = 100 * correct_train / total_train
        
        # --- VALIDATION ---
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0
        
        with torch.no_grad():
            for pre_t, post_t, labels in val_loader:
                pre_t, post_t, labels = pre_t.to(device), post_t.to(device), labels.to(device)
                
                outputs = model(pre_t, post_t)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item() * pre_t.size(0)
                _, predicted = torch.max(outputs.data, 1)
                total_val += labels.size(0)
                correct_val += (predicted == labels).sum().item()
                
        val_loss = val_loss / len(val_loader.dataset)
        val_acc = 100 * correct_val / total_val
        
        print(f"Epoch {epoch:03d} | Train Loss: {train_loss:.4f} Acc: {train_acc:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc:.2f}%")
        
        # --- EARLY STOPPING CHECK ---
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            # Save the best model
            torch.save(model.state_dict(), save_path)
            print(f"  --> Validation loss improved. Saving model to {save_path}")
        else:
            epochs_no_improve += 1
            print(f"  --> No improvement in validation loss for {epochs_no_improve} epoch(s).")
            
        if epochs_no_improve >= patience:
            print(f"\n[+] Early stopping triggered at epoch {epoch}. Best Val Loss: {best_val_loss:.4f}")
            break

    print(f"\n[+] Training complete! Best weights stored at: {save_path}")
    print("[*] The main TriNetraAI change detection pipeline will now use these neural weights.")

if __name__ == "__main__":
    train_bda()
