import os
import matplotlib.pyplot as plt
from detective_api import compare_tiles

def main():
    # Look for sample tiles provided by Person 1 (in sample_pairs/ or patches/)
    t1_test = "sample_pairs/tile_000_t1.png"
    t2_test = "sample_pairs/tile_000_t2.png"

    if not os.path.exists(t1_test):
        t1_test = "sample_pairs/tile_001_t1.tif"
        t2_test = "sample_pairs/tile_001_t2.tif"

    if not os.path.exists(t1_test):
        sample_files = [f for f in os.listdir("sample_pairs") if "_t1" in f] if os.path.exists("sample_pairs") else []
        if sample_files:
            t1_test = os.path.join("sample_pairs", sample_files[0])
            t2_test = t1_test.replace("_t1", "_t2")
        else:
            print("Please place two sample image tiles in sample_pairs/ to run verification.")
            return

    print("==================================================")
    print("      TEMPORAL DETECTIVE AI ANALYSIS (ROLE 3)")
    print("==================================================")
    print(f"Time 1 (Before) : {t1_test}")
    print(f"Time 2 (After)  : {t2_test}\n")

    result = compare_tiles(t1_test, t2_test)

    print("================ DETECTIVE REPORT ================")
    print(f"Detection Engine       : {result['mode_used']}")
    print(f"Significant Change     : {result['has_change']}")
    print(f"Change Percentage      : {result['change_ratio'] * 100:.2f}%")
    print(f"Targets Flagged        : {result['target_count']}")
    print(f"Mask Saved At          : {result['mask_path']}")
    print(f"Overlay Saved At       : {result['overlay_path']}")
    print("--------------------------------------------------")
    print("        SEMANTIC CHANGE CLASSIFICATION ('WHAT')   ")
    print("--------------------------------------------------")
    for target in result["detected_targets"]:
        t_id = target["target_id"]
        c_type = target["change_type"]
        trans = target["transition"]
        conf = target["confidence"]
        desc = target["description"]
        bbox = target["bbox"]
        print(f"• Target #{t_id}:")
        print(f"    - Type       : {c_type} (Confidence: {conf*100:.1f}%)")
        print(f"    - Transition : {trans}")
        print(f"    - Details    : {desc}")
        print(f"    - BoundingBox: [x={bbox['x']}, y={bbox['y']}, w={bbox['w']}, h={bbox['h']}, area={bbox['area_px']}px]")
    print("==================================================")

    # 3-Panel Visual Comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    from src.preprocessor import read_satellite_image
    axes[0].imshow(read_satellite_image(t1_test))
    axes[0].set_title(f"Time 1 (Before)")
    axes[0].axis("off")

    axes[1].imshow(result["raw_mask_array"], cmap="gray")
    axes[1].set_title(f"Binary Change Mask ({result['target_count']} targets)")
    axes[1].axis("off")

    axes[2].imshow(result["overlay_array"])
    axes[2].set_title(f"Semantic Red-Alert Overlay")
    axes[2].axis("off")

    plt.tight_layout()
    plot_out = os.path.join("outputs", "test_report.png")
    plt.savefig(plot_out, bbox_inches="tight", dpi=150)
    print(f"\nSaved test visualization figure to: {plot_out}")

    try:
        plt.show()
    except Exception:
        pass

if __name__ == "__main__":
    main()
