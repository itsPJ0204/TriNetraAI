# Bhuvan Satellite Data Scientist Module

This module is the **data foundation** for an offline AI satellite search + temporal change-detection system.

## Scope

Input is only the **original Bhuvan/NRSC/ISRO GeoTIFF/COG** supplied to the project (`.tif` / `.tiff`). The pipeline does not generate fake satellite imagery.

It performs:

1. Source raster metadata extraction.
2. 512x512 georeferenced tiling.
3. Stable `tile_id` and `grid_key` creation.
4. Incremental ingestion using SHA-256 so an already processed image is skipped.
5. Complete tile registry in SQLite.
6. CSV export as the handoff contract for the Semantic AI teammate.
7. Spatial lookup and same-location cross-date tile pairing for Temporal AI.

## Team contract

The Data Scientist owns:

```text
Original TIFF -> tiles -> tile_registry.sqlite + tiles_metadata.csv
```

The Semantic AI teammate owns:

```text
tile_id + tile_path -> RemoteCLIP/CLIP -> embedding -> vector DB
```

The Temporal AI teammate owns:

```text
grid_key + date1/date2 -> before TIFF + after TIFF -> change detection
```

**Vector embeddings and the vector DB are intentionally not implemented here.** This module only provides the stable tile identity, actual TIFF path, geospatial metadata, and date needed by those downstream AI modules.

## Output

After ingesting an image:

```text
data/
├── tiles/
│   └── <source_name>/
│       ├── <source>_r00000_c00000.tif
│       └── ...
└── tiles_metadata.csv

database/
└── tile_registry.sqlite
```

Each CSV/SQLite tile record contains:

`tile_id, grid_key, date, source filename, actual TIFF path, bbox, width, height, pixel offsets, bands, dtype, nodata, CRS, transform`

### Why `grid_key`?

`grid_key` identifies the same spatial grid cell across different dates:

```text
2026-01 -> r00003_c00005
2026-06 -> r00003_c00005
```

That lets Temporal AI pair the two actual TIFF tiles without guessing by filename.

## Run

```bash
python -m pip install -r requirements.txt
python main.py init-db
python main.py ingest /path/to/original_bhuvan_image.tif
```

The ingest command prints the number of tiles and the path of `tiles_metadata.csv`.

Useful commands:

```bash
python main.py list-tiles
python main.py get-tile <tile_id>
python main.py search-bbox 80 23 82 30
python main.py export-csv
```

## Semantic AI handoff

The Semantic AI teammate can read `tiles_metadata.csv` or query `tile_registry.sqlite`.

Example logic:

```python
row = registry.get_tile(tile_id)
image = load_tiff(row["filepath"])
embedding = remote_clip.encode_image(image)
vector_db.insert(id=row["tile_id"], vector=embedding)
```

The vector DB should keep `tile_id` as its ID. When search returns a tile ID, the registry resolves it back to the actual TIFF and geographic metadata.

## Tests

```bash
pytest -q
```

Tests create temporary rasters only inside the test environment; those are not project inputs or demo satellite data.

## Bhuvan BAND2-BAND5 folder input

If a Bhuvan download contains separate files such as `BAND2.tif`, `BAND3.tif`, `BAND4.tif`, `BAND5.tif`, keep them together in one scene/date folder. The Data Scientist module can ingest that folder directly:

```bash
python main.py init-db
python main.py ingest-folder data/raw/2024-06 --date 2024-06-15
python main.py list-tiles
python main.py export-csv
```

The module validates that all four bands have matching size, CRS and transform, then writes real multi-band GeoTIFF tiles. It does **not** generate synthetic satellite imagery. Re-running the same folder is skipped using a manifest hash, so ingestion remains incremental.

Expected layout:

```text
data/raw/
├── 2024-01/
│   ├── BAND2.tif
│   ├── BAND3.tif
│   ├── BAND4.tif
│   └── BAND5.tif
└── 2024-06/
    ├── BAND2.tif
    ├── BAND3.tif
    ├── BAND4.tif
    └── BAND5.tif
```

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