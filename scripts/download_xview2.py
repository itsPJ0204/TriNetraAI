import os
import sys
import requests
import tarfile
import zipfile
from pathlib import Path

# Note: The xView2 dataset requires a free account to download the challenge data.
# 1. Go to https://xview2.org/download
# 2. Log in and copy the download link for "train_images_labels_targets" (or tier3).
# 3. Paste the URL below or pass it as an argument.

DEFAULT_URL = "YOUR_XVIEW2_DOWNLOAD_LINK_HERE"
OUTPUT_DIR = Path("data/xview2")

def download_file(url, dest_path):
    print(f"[*] Downloading {url} to {dest_path}...")
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        print(f"[!] Failed to download. HTTP Status: {response.status_code}")
        print("Please ensure your download link is valid and hasn't expired.")
        sys.exit(1)
        
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                # Print progress
                if total_size > 0:
                    percent = int(100 * downloaded / total_size)
                    print(f"\rProgress: {percent}% ({downloaded / (1024*1024):.1f} MB)", end="")
    print("\n[+] Download complete.")

def extract_dataset(filepath, extract_to):
    print(f"[*] Extracting {filepath} to {extract_to}...")
    filepath_str = str(filepath)
    if filepath_str.endswith(".tar.gz") or filepath_str.endswith(".tgz"):
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(path=extract_to)
    elif filepath_str.endswith(".zip"):
        with zipfile.open(filepath, "r") as zip_ref:
            zip_ref.extractall(extract_to)
    else:
        print("[!] Unsupported file format for extraction.")
        sys.exit(1)
    print("[+] Extraction complete.")

def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = DEFAULT_URL

    if url == "YOUR_XVIEW2_DOWNLOAD_LINK_HERE" or not url.startswith("http"):
        print("[!] Error: You must provide a valid xView2 download URL.")
        print("Usage: python download_xview2.py \"<download_link>\"")
        print("Get your link from https://xview2.org/download")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = url.split("?")[0].split("/")[-1]
    if not filename:
        filename = "xview2_dataset.tar.gz"
        
    archive_path = OUTPUT_DIR / filename
    
    if not archive_path.exists():
        download_file(url, archive_path)
    else:
        print(f"[*] Archive already exists at {archive_path}, skipping download.")
        
    extract_dataset(archive_path, OUTPUT_DIR)
    
    print(f"[+] xView2 dataset successfully prepared in {OUTPUT_DIR}")
    print("[*] Ready for Battle Damage Assessment (BDA) training!")

if __name__ == "__main__":
    main()
