# TriNetraAI

Welcome to the **TriNetraAI** QA & Discovery pipeline! 

This repository contains the tools needed to process satellite images for change-detection, specifically focusing on filtering out false alarms (like clouds and shadows) and clustering similar regions together.

---

## 🌍 The Offline Edge Pipeline (Sentinel-2)

We have built a completely offline, **Edge Computing** pipeline. This means the system can run on a disconnected device in the field (like a rugged laptop, a drone, or a Raspberry Pi) without needing an internet connection.

Here is a simple breakdown of how the edge pipeline works:

### 1. The Folder Structure
We set up a simple folder system to manage the flow of data just like a physical USB drive:
* **`edge_data/raw_input/`**: This is where you drop your raw, unprocessed satellite images. 
* **`edge_data/processed_output/`**: This is where the script automatically drops the cleaned images and the generated cloud masks.

### 2. Simulating the Data Drop (`download_edge_data.py`)
Since we need data to test with, this script acts as our data procurer. 
* It connects to the internet one time to download a batch of real Sentinel-2 satellite images over New Delhi (spanning different months of the year to capture different weather conditions).
* It pulls down the full **13-band Top-Of-Atmosphere (L1C)** data.
* It saves these files directly into the `raw_input/` folder, acting exactly like a field operator plugging in a hard drive.

### 3. The Offline Brain (`local_ingest.py`)
This is the core script that runs on the edge device. **It requires zero internet connection.**
* It constantly scans the `raw_input/` folder for new images.
* When it finds an image, it loads it and extracts the 10 specific light bands required to detect clouds.
* It runs **`s2cloudless`**, a lightweight machine learning model that runs perfectly on a standard CPU. This model looks at the pixels and figures out exactly which ones are clouds and which are clear land.
* It saves a clean, true-color image and a mathematical "mask" (a `.npy` file) into the `processed_output/` folder.

### 4. Integration with the Rest of the Team (`qa_mask.py`)
Once `local_ingest.py` has generated the offline cloud masks, the Temporal AI teammate needs to use them.
* We updated the main `qa_mask.py` script so that anyone on the team can simply call `get_quality_mask("edge_s2cloudless", npy_path="...")`. 
* This allows the rest of the change-detection AI to easily read the edge-computed masks and ignore the cloudy areas, preventing fake construction alerts!

---

### In Summary
1. Drop raw `.tif` files into `raw_input/`.
2. Run `local_ingest.py` offline.
3. Get clean images and cloud masks in `processed_output/` automatically!