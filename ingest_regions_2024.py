import requests
import time

API_URL = "http://localhost:8000/ingest/stac"

# Bounding boxes [min_lon, min_lat, max_lon, max_lat]
REGIONS = {
    "Kolkata 2024": [88.30, 22.51, 88.38, 22.62]
}

# Strictly 2024 to ensure a 2024 tile is downloaded
DATETIME_RANGE = "2024-01-01/2024-12-31"

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
        response = requests.post(API_URL, json=payload, timeout=900)  # 15 min timeout
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
    
print("Ingestion script completed!")
