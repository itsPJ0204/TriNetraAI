import requests
import time
from datetime import datetime

API_URL = "http://localhost:8000/ingest/stac"

# Bounding boxes [min_lon, min_lat, max_lon, max_lat]
REGIONS = {
    "Kolkata": [88.30, 22.51, 88.38, 22.62],
    "Ladakh (LAC Border)": [78.70, 33.70, 78.90, 33.90],
    "Assam (Tawang Sector)": [91.80, 27.50, 92.00, 27.70]
}

# 01-01-2024 to current date
current_date = datetime.now().strftime("%Y-%m-%d")
DATETIME_RANGE = f"2024-01-01/{current_date}"

print(f"Starting Landsat STAC Ingestion for timeframe: {DATETIME_RANGE}")
print("-" * 50)

for region_name, bbox in REGIONS.items():
    print(f"[*] Triggering ingestion for: {region_name} (BBOX: {bbox})")
    
    payload = {
        "bbox": bbox,
        "datetime_range": DATETIME_RANGE,
        "tile_size": 256,
        "force": False
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=600)  # 10 minute timeout for downloading and processing
        if response.status_code == 200:
            data = response.json()
            tiles = data.get("tiles", [])
            print(f"[+] Success! Ingested {len(tiles)} tiles for {region_name}")
            print(f"    Date acquired: {data.get('date')}")
        else:
            print(f"[!] Failed to ingest {region_name}. Status: {response.status_code}")
            print(f"    Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[!] Request failed for {region_name}: {e}")
    
    print("-" * 50)
    time.sleep(2) # brief pause between regions

print("Ingestion script completed!")
