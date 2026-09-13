import cv2
import numpy as np
from src.semantic_classifier import determine_semantic_change

def process_detection(
    raw_mask: np.ndarray, 
    img_t1: np.ndarray, 
    img_t2: np.ndarray, 
    min_area: int = 100,
    enable_bda: bool = True
) -> dict:
    """
    Takes raw binary change mask, Before (T1) image, and After (T2) image:
    1. Applies morphological noise reduction.
    2. Extracts contours & bounding boxes.
    3. Runs Semantic AI Classification (RemoteCLIP) to determine WHAT changed.
    4. Renders red-alert overlays with bounding boxes and semantic labels.
    """
    h, w = raw_mask.shape[:2]

    if (img_t2.shape[0], img_t2.shape[1]) != (h, w):
        raw_mask = cv2.resize(raw_mask, (img_t2.shape[1], img_t2.shape[0]), interpolation=cv2.INTER_NEAREST)
        h, w = img_t2.shape[:2]

    # 1. Morphological noise filtering
    kernel_open = np.ones((3, 3), np.uint8)
    kernel_close = np.ones((5, 5), np.uint8)
    clean_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel_open)
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_close)

    # 2. Extract Contours & Bounding Boxes
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_targets = []
    total_change_pixels = 0
    overlay = img_t2.copy()

    for target_id, cnt in enumerate(contours, start=1):
        area = cv2.contourArea(cnt)
        if area >= min_area:
            total_change_pixels += area
            x, y, bw, bh = cv2.boundingRect(cnt)
            bbox_dict = {"x": int(x), "y": int(y), "w": int(bw), "h": int(bh), "area_px": float(area)}

            # 3. Determine WHAT the actual change is using Semantic AI (RemoteCLIP)
            semantic = determine_semantic_change(img_t1, img_t2, bbox_dict, enable_bda=enable_bda)

            target_entry = {
                "target_id": target_id,
                "bbox": bbox_dict,
                "change_type": semantic["category"],
                "transition": semantic["transition"],
                "from_state": semantic["from_class"],
                "to_state": semantic["to_class"],
                "confidence": semantic["confidence"],
                "description": semantic["description"],
                "damage_severity": semantic.get("damage_severity", "None"),
                "classification_method": semantic.get("method", "Semantic_AI")
            }
            detected_targets.append(target_entry)

            # 4. Draw bounding box and highlight overlay
            box_color = (255, 0, 0)
            if semantic.get("damage_severity") == "Destroyed":
                box_color = (0, 0, 255) # Red for destroyed
            elif semantic.get("damage_severity") in ["Major Damage", "Minor Damage"]:
                box_color = (0, 165, 255) # Orange for major/minor
                
            cv2.rectangle(overlay, (x, y), (x + bw, y + bh), box_color, 2)
            cv2.drawContours(overlay, [cnt], -1, (255, 30, 30), -1)

            # Draw small tag label on overlay
            label_text = f"#{target_id}: {semantic['category'][:22]}"
            if semantic.get("damage_severity", "None") != "None":
                label_text += f" [{semantic['damage_severity']}]"
                
            cv2.putText(
                overlay, 
                label_text, 
                (max(0, x), max(15, y - 5)), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.42, 
                (255, 255, 255), 
                1, 
                cv2.LINE_AA
            )

    # Blend overlay (40% red highlight fill)
    overlay = cv2.addWeighted(overlay, 0.45, img_t2, 0.55, 0)
    change_ratio = float(total_change_pixels / (h * w))

    return {
        "has_change": len(detected_targets) > 0,
        "change_ratio": round(change_ratio, 4),
        "target_count": len(detected_targets),
        "detected_targets": detected_targets,
        "clean_mask": clean_mask,
        "overlay": overlay
    }
