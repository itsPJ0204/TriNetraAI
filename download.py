import os
import shutil
import tifffile
from sentinelhub import SHConfig, BBox, CRS, SentinelHubRequest, DataCollection, MimeType, MosaickingOrder

# 1. Configuration
config = SHConfig()
config.sh_client_id = "sh-d6aad816-707f-434d-8850-2f68e268e3e9"
config.sh_client_secret = "x1wbwLbagTkHZiyEeVhd6Yf15CIexMFo"
config.sh_base_url = "https://sh.dataspace.copernicus.eu"
config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

# 2. Define a targeted Area of Interest (AOI)
bbox = BBox(bbox=[77.20, 28.55, 77.30, 28.65], crs=CRS.WGS84)  # New Delhi area

# 3. Evalscript — 5-band output: [Red, Green, Blue, NIR, SCL]
#
#   Band index  |  Content
#   ------------|------------------------------------------
#        0      |  B04 (Red)          scaled × 10000
#        1      |  B03 (Green)        scaled × 10000
#        2      |  B02 (Blue)         scaled × 10000
#        3      |  B08 (NIR)          scaled × 10000
#        4      |  SCL (Scene Classification Layer, raw int)
#
#   SCL class codes relevant to masking:
#     0  = No Data         8  = Cloud (medium prob)
#     1  = Saturated       9  = Cloud (high prob)
#     3  = Cloud Shadow    10 = Thin Cirrus
#                          11 = Snow / Ice
evalscript = """
//VERSION=3
function setup() {
    return {
        input: ["B02", "B03", "B04", "B08", "SCL", "dataMask"],
        output: { id: "default", bands: 5, sampleType: "UINT16" }
    };
}

function evaluatePixel(sample) {
    return [
        sample.B04 * 10000,   // 0: Red
        sample.B03 * 10000,   // 1: Green
        sample.B02 * 10000,   // 2: Blue
        sample.B08 * 10000,   // 3: NIR
        sample.SCL            // 4: Scene Classification Layer (raw class int, NOT scaled)
    ];
}
"""

# 4. Time snapshots — same calendar month each year to suppress seasonal false alarms
time_intervals = [
    ("2024-01-01", "2024-01-31"),
    ("2025-01-01", "2025-01-31"),
    ("2026-01-01", "2026-01-31"),
]

# 5. Download loop
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(BASE_DIR, "sih_dataset")
os.makedirs(dataset_dir, exist_ok=True)

sentinel2_l2a_cdse = DataCollection.SENTINEL2_L2A.define_from(
    "SENTINEL2_L2A_CDSE", service_url="https://sh.dataspace.copernicus.eu"
)

for idx, time_interval in enumerate(time_intervals):
    year_label = time_interval[0][:4]
    print(f"[{idx+1}/3] Fetching Sentinel-2 L2A for {year_label} (bands: R,G,B,NIR,SCL)...")

    year_folder = os.path.join(dataset_dir, f"year_{idx+1}")
    os.makedirs(year_folder, exist_ok=True)

    # Clear old SentinelHub cache subdirs so the new 5-band request is not skipped
    for entry in os.listdir(year_folder):
        entry_path = os.path.join(year_folder, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
            print(f"  Cleared cache dir: {entry}")

    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=sentinel2_l2a_cdse,
                time_interval=time_interval,
                mosaicking_order=MosaickingOrder.LEAST_CC,  # least cloud-cover mosaic
            )
        ],
        responses=[
            SentinelHubRequest.output_response("default", MimeType.TIFF)
        ],
        bbox=bbox,
        size=(512, 512),
        config=config,
        data_folder=year_folder,
    )

    data = request.get_data(save_data=True)

    save_path = os.path.join(year_folder, "default.tif")
    tifffile.imwrite(save_path, data[0])
    print(f"  Saved ({data[0].shape[2] if data[0].ndim == 3 else data[0].shape[-1]} bands): {save_path}")

print("\nMulti-temporal staging complete! All default.tif files now contain 5 bands [R,G,B,NIR,SCL].")