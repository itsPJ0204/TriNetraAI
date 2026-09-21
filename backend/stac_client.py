import os
from pathlib import Path
from typing import Any

import planetary_computer
from pystac_client import Client
import requests
import rasterio

def download_landsat_stac(bbox: list[float], datetime_range: str, output_dir: Path) -> Path | None:
    """
    Search MSTAC for Landsat C2 L2 imagery, download Red, Green, Blue bands,
    and stack them into an RGB composite GeoTIFF.
    """
    # 1. Search the STAC API
    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=bbox,
        datetime=datetime_range,
        query={"eo:cloud_cover": {"lt": 20}},
        max_items=1
    )
    
    items = list(search.items())
    if not items:
        return None
        
    item = items[0]
    
    # 2. Sign the item to get access to Azure Blob Storage
    signed_item = planetary_computer.sign(item)
    
    # 3. Get the URLs for the required bands
    assets = signed_item.assets
    band_names = ["red", "green", "blue"] # B4, B3, B2 in Landsat 8/9
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract acquisition date for the directory structure
    date_str = item.datetime.strftime("%Y-%m-%d") if item.datetime else "2026-06-27"
    date_dir = output_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine the target output file
    out_file = date_dir / f"landsat_{item.id}_RGB_COMPOSITE.tif"
    if out_file.exists():
        return out_file # Already downloaded
    
    # Download and stack using rasterio
    import numpy as np
    
    src_files = []
    for band in band_names:
        if band in assets:
            href = assets[band].href
            src_files.append(href)
            
    if len(src_files) != 3:
        raise ValueError(f"Could not find all required RGB bands in STAC item: {item.id}")
        
    # Read the bands from remote URLs (COGs) and stack them locally
    with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        # Open all sources
        sources = [rasterio.open(url) for url in src_files]
        
        # All bands should have the same profile
        meta = sources[0].meta
        meta.update(
            count=3,
            dtype='uint16',
            driver='GTiff',
            compress='deflate'
        )
        
        with rasterio.open(out_file, 'w', **meta) as dest:
            for i, src in enumerate(sources, start=1):
                # Landsat 8/9 SR is stored as uint16 with scaling. We will just copy the raw uint16 array.
                # The ingest pipeline handles normalization to uint8.
                dest.write(src.read(1), i)
                dest.set_band_description(i, band_names[i-1].upper())
                
        for src in sources:
            src.close()
            
    return out_file
