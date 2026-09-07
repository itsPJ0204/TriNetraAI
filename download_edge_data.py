"""
download_edge_data.py — Edge computing data provisioning simulator
==================================================================
Simulates physical transfer of raw satellite imagery to the edge device.
Downloads a Sentinel-2 L1C (Top-of-Atmosphere) 13-band image to 'edge_data/raw_input/'.

Bands retrieved for s2cloudless:
[B01, B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, B12]
(These represent 13 full TOA reflectance bands needed for local inference)
"""

import os
import tifffile
import numpy as np
from sentinelhub import (
    SHConfig,
    BBox,
    CRS,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    MosaickingOrder,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "edge_data", "raw_input")
os.makedirs(RAW_DIR, exist_ok=True)


def download_13_band_scene():
    config = SHConfig()
    config.sh_client_id = "sh-d6aad816-707f-434d-8850-2f68e268e3e9"
    config.sh_client_secret = "x1wbwLbagTkHZiyEeVhd6Yf15CIexMFo"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    # Fetch L1C (Top of Atmosphere) - optimal for s2cloudless model
    sentinel2_l1c = DataCollection.SENTINEL2_L1C.define_from(
        "SENTINEL2_L1C_CDSE", service_url="https://sh.dataspace.copernicus.eu"
    )
    
    # New Delhi area
    bbox = BBox(bbox=[77.20, 28.55, 77.30, 28.65], crs=CRS.WGS84)

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"],
            output: { id: "default", bands: 13, sampleType: "UINT16" }
        };
    }
    function evaluatePixel(sample) {
        // Return 13 bands scaled x10000
        return [
            sample.B01 * 10000,
            sample.B02 * 10000,
            sample.B03 * 10000,
            sample.B04 * 10000,
            sample.B05 * 10000,
            sample.B06 * 10000,
            sample.B07 * 10000,
            sample.B08 * 10000,
            sample.B8A * 10000,
            sample.B09 * 10000,
            sample.B10 * 10000,
            sample.B11 * 10000,
            sample.B12 * 10000
        ];
    }
    """

    # Download a batch of images to simulate a larger edge dataset
    time_intervals = [
        ("2024-01-01", "2024-01-31"), # January
        ("2024-04-01", "2024-04-30"), # April
        ("2024-07-01", "2024-07-31"), # July (Monsoon)
        ("2024-10-01", "2024-10-31"), # October
    ]

    for start_date, end_date in time_intervals:
        req = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=sentinel2_l1c,
                    time_interval=(start_date, end_date),
                    mosaicking_order=MosaickingOrder.MOST_RECENT,
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=(512, 512),
            config=config,
        )

        month_name = start_date.split("-")[1]
        print(f"[DOWNLOAD] Provisioning 13-band Sentinel-2 L1C image over Delhi for 2024-{month_name}...")
        data = req.get_data()
        img_data = data[0].astype(np.uint16)

        tif_path = os.path.join(RAW_DIR, f"delhi_13band_2024_{month_name}.tif")
        tifffile.imwrite(tif_path, img_data)
        print(f"  -> [SUCCESS] Saved 13-band TIF to {tif_path}")

    print("\nAll batch files downloaded. The local_ingest.py edge script will process all of them.")


if __name__ == "__main__":
    download_13_band_scene()
