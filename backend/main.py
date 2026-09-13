"""HTTP API that exposes the existing TriNetraAI functionality."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "database" / "tile_registry.sqlite"

(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "outputs").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="TriNetraAI Backend",
    version="1.0.0",
    description="A thin HTTP adapter over the repository's existing search, spatial, and change-detection modules.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data", StaticFiles(directory=str(PROJECT_ROOT / "data")), name="data")
app.mount("/outputs", StaticFiles(directory=str(PROJECT_ROOT / "outputs")), name="outputs")


def custom_openapi() -> dict[str, Any]:
    """Ensure Swagger UI displays native Choose Files binary picker for file uploads."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    for s_val in schemas.values():
        if isinstance(s_val, dict) and "properties" in s_val:
            for p_val in s_val["properties"].values():
                if isinstance(p_val, dict):
                    if p_val.get("contentMediaType") == "application/octet-stream":
                        p_val["format"] = "binary"
                    if p_val.get("type") == "array" and isinstance(p_val.get("items"), dict):
                        if p_val["items"].get("contentMediaType") == "application/octet-stream":
                            p_val["items"]["format"] = "binary"
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def _json_safe(obj: Any) -> Any:
    """Recursively convert NumPy types, Paths, SearchResults, and objects into JSON-serializable types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items() if k not in ("raw_mask_array", "overlay_array")}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "to_dict"):
        return _json_safe(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return _json_safe(obj.__dict__)
    return str(obj)


class BBox(BaseModel):
    left: float = Field(..., description="Western longitude / left coordinate", examples=[77.15])
    bottom: float = Field(..., description="Southern latitude / bottom coordinate", examples=[28.57])
    right: float = Field(..., description="Eastern longitude / right coordinate", examples=[77.28])
    top: float = Field(..., description="Northern latitude / top coordinate", examples=[28.67])

    @model_validator(mode="after")
    def validate_order(self) -> "BBox":
        if self.left >= self.right:
            raise ValueError("left must be strictly less than right")
        if self.bottom >= self.top:
            raise ValueError("bottom must be strictly less than top")
        return self

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class TextSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query", examples=["dense vegetation"])
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results to return", examples=[5])
    bbox: BBox | None = Field(default=None, description="Optional bounding box spatial constraint")
    year: str | None = Field(default=None, description="Optional year filter")
    satellite: str | None = Field(default=None, description="Optional satellite filter")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "dense vegetation",
                    "top_k": 5
                },
                {
                    "query": "dense vegetation",
                    "top_k": 5,
                    "bbox": {
                        "left": 77.15,
                        "bottom": 28.57,
                        "right": 77.28,
                        "top": 28.67
                    }
                }
            ]
        }
    }


class ChangeDetectionRequest(BaseModel):
    before_path: str = Field(..., min_length=1, description="Path to before satellite image tile")
    after_path: str = Field(..., min_length=1, description="Path to after satellite image tile")
    force_classical: bool = Field(default=False, description="Force classical CV engine instead of neural BIT")
    apply_qa_suppression: bool = Field(default=True, description="Apply QA cloud/shadow suppression")
    min_area: int = Field(default=100, ge=1, description="Minimum pixel area threshold for change clusters")
    enable_bda: bool = Field(default=True, description="Enable Battle Damage Assessment (BDA) severity evaluation")
    damage_level: str | None = Field(default=None, description="Optional filter for Battle Damage Assessment severity (e.g. 'Destroyed', 'Major Damage')")


class STACIngestRequest(BaseModel):

    bbox: list[float] = Field(..., description="[minx, miny, maxx, maxy]")
    datetime_range: str = Field(..., description="e.g. '2026-01-01/2026-06-27'")
    tile_size: int = Field(default=256, ge=64, le=1024, description="Tile dimension in pixels")
    force: bool = Field(default=False, description="Force re-embedding of all tiles")

class IndexRequest(BaseModel):
    force: bool = Field(default=False, description="Force re-embedding of all tiles")
    raw_root: str | None = Field(default=None, description="Optional custom raw root directory")
    output_root: str | None = Field(default=None, description="Optional custom output tiles directory")
    tile_size: int = Field(default=256, ge=64, le=1024, description="Tile dimension in pixels")


def _availability_error(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"TriNetraAI capability unavailable: {error}",
    )


def _project_file(path_value: str) -> Path:
    path = Path(path_value)
    candidate = path if path.is_absolute() else PROJECT_ROOT / path
    try:
        candidate.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Paths must be inside the project root.") from error
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path_value}")
    return candidate


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}



@app.get("/search/filters")
def get_search_filters():
    from ingestion.db import get_connection
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
    
    geolocator = Nominatim(user_agent="trinetra_ai_geo_cache")
    
    with get_connection(DEFAULT_REGISTRY_PATH) as conn:
        cur = conn.cursor()
        
        # Years
        cur.execute("SELECT DISTINCT substr(acquisition_date, 1, 4) FROM images WHERE acquisition_date IS NOT NULL")
        years = [row[0] for row in cur.fetchall() if row[0]]
        years = sorted(years, reverse=True)
        
        # Satellites
        cur.execute("SELECT DISTINCT filepath, filename FROM images")
        rows = cur.fetchall()
        satellites = set()
        for row in rows:
            fp_lower = (row[0] or "").lower()
            fn_lower = (row[1] or "").lower()
            combined = fp_lower + " " + fn_lower
            
            found = False
            if "landsat" in combined or "l8" in combined:
                satellites.add("Landsat-8")
                found = True
            if "sentinel2" in combined or "sentinel-2" in combined:
                satellites.add("Sentinel-2")
                found = True
            if "s1" in combined or "sentinel1" in combined or "sentinel-1" in combined:
                satellites.add("Sentinel-1")
                found = True
            
            if not found:
                satellites.add("Other")
        
        satellites = sorted(list(satellites))
        
        # Areas of Interest
        cur.execute('''
            CREATE TABLE IF NOT EXISTS region_cache (
                bounds_key TEXT PRIMARY KEY,
                minx REAL, miny REAL, maxx REAL, maxy REAL,
                region_name TEXT
            )
        ''')
        
        cur.execute("SELECT DISTINCT minx, miny, maxx, maxy FROM images")
        distinct_bounds = cur.fetchall()
        
        aoi_list = []
        for minx, miny, maxx, maxy in distinct_bounds:
            if minx is None or miny is None: continue
            
            b_key = f"{minx:.4f},{miny:.4f},{maxx:.4f},{maxy:.4f}"
            
            cur.execute("SELECT region_name FROM region_cache WHERE bounds_key = ?", (b_key,))
            cached = cur.fetchone()
            
            if cached:
                region_name = cached[0]
            else:
                center_lat = (miny + maxy) / 2.0
                center_lon = (minx + maxx) / 2.0
                try:
                    location = geolocator.reverse((center_lat, center_lon), language="en", timeout=5)
                    if location and location.raw and "address" in location.raw:
                        addr = location.raw["address"]
                        city = addr.get("city", addr.get("town", addr.get("village", addr.get("county", ""))))
                        state = addr.get("state", "")
                        
                        # Format "City, State" nicely
                        if city and state and city != state:
                            region_name = f"{city}, {state}"
                        elif state:
                            region_name = state
                        elif city:
                            region_name = city
                        else:
                            region_name = location.address.split(",")[0].strip()
                    else:
                        region_name = f"Region ({center_lat:.2f}, {center_lon:.2f})"
                except Exception:
                    region_name = f"Region ({center_lat:.2f}, {center_lon:.2f})"
                
                cur.execute("INSERT INTO region_cache (bounds_key, minx, miny, maxx, maxy, region_name) VALUES (?, ?, ?, ?, ?, ?)",
                            (b_key, minx, miny, maxx, maxy, region_name))
                conn.commit()
                
            aoi_list.append({
                "id": b_key,
                "label": region_name,
                "bounds": {"left": minx, "bottom": miny, "right": maxx, "top": maxy}
            })
            
        return {
            "years": years,
            "satellites": satellites,
            "aoi": aoi_list
        }

@app.post("/search/text")

def search_text(request: TextSearchRequest) -> dict[str, Any]:
    """Natural-language semantic search across Docker Qdrant indexed satellite tiles."""
    try:
        from semantic_search.search import search

        results = search(
            query=request.query,
            top_k=request.top_k,
            bbox=request.bbox.as_dict() if request.bbox else None,
            year=request.year,
            satellite=request.satellite,
        )
        return {
            "query": request.query,
            "top_k": request.top_k,
            "count": len(results),
            "results": _json_safe(results),
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ConnectionError as error:
        raise _availability_error(error) from error
    except Exception as error:
        raise _availability_error(error) from error


@app.post("/search/image")
async def search_image(
    image: Annotated[UploadFile, File(description="Satellite image or GeoTIFF query")],
    top_k: Annotated[int, Query(ge=1, le=100)] = 5,
    query: Annotated[str | None, Query(description="Optional text query for multimodal fusion")] = None,
    alpha: Annotated[float, Query(ge=0.0, le=1.0)] = 0.5,
    fusion_strategy: Annotated[
        Literal["weighted_sum", "average", "image_only", "text_only"],
        Query(description="Multimodal fusion strategy"),
    ] = "weighted_sum",
    minx: Annotated[float | None, Query(description="Optional bbox left")] = None,
    miny: Annotated[float | None, Query(description="Optional bbox bottom")] = None,
    maxx: Annotated[float | None, Query(description="Optional bbox right")] = None,
    maxy: Annotated[float | None, Query(description="Optional bbox top")] = None,
    year: Annotated[str | None, Query(description="Optional year filter")] = None,
    satellite: Annotated[str | None, Query(description="Optional satellite filter")] = None,
) -> dict[str, Any]:
    """Image-to-image or multimodal search across Docker Qdrant indexed satellite tiles."""
    try:
        payload = await image.read()
        if not payload:
            raise ValueError("Uploaded image is empty.")

        # Decode image (supports RGB, PNG, JPEG, TIFF, and multi-band GeoTIFFs)
        try:
            with Image.open(BytesIO(payload)) as decoded:
                query_image = decoded.convert("RGB")
        except Exception:
            import rasterio
            from rasterio.io import MemoryFile
            from semantic_search.sentinel2 import normalize_uint16_to_uint8

            with MemoryFile(payload) as memfile:
                with memfile.open() as src:
                    count = src.count
                    if count >= 3:
                        bands = [src.read(i) for i in (1, 2, 3)]
                    elif count == 1:
                        b1 = src.read(1)
                        bands = [b1, b1, b1]
                    else:
                        b1 = src.read(1)
                        bands = [b1, src.read(2), b1]
                    norm = [
                        normalize_uint16_to_uint8(b) if b.dtype != np.uint8 else b
                        for b in bands
                    ]
                    query_image = Image.fromarray(np.stack(norm, axis=-1))

    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid image upload: {error}") from error

    bbox_dict: dict[str, float] | None = None
    if any(v is not None for v in (minx, miny, maxx, maxy)):
        if not all(v is not None for v in (minx, miny, maxx, maxy)):
            raise HTTPException(status_code=400, detail="All four bbox coordinates (minx, miny, maxx, maxy) must be provided.")
        if minx >= maxx or miny >= maxy:
            raise HTTPException(status_code=400, detail="Invalid bbox: minx must be less than maxx and miny must be less than maxy.")
        bbox_dict = {"left": minx, "bottom": miny, "right": maxx, "top": maxy}

    try:
        from semantic_search.search import search_by_image

        results = search_by_image(
            image=query_image,
            query=query,
            top_k=top_k,
            bbox=bbox_dict,
            alpha=alpha,
            fusion_strategy=fusion_strategy,
        )
        return {
            "query": query,
            "top_k": top_k,
            "fusion_strategy": fusion_strategy,
            "count": len(results),
            "results": _json_safe(results),
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ConnectionError as error:
        raise _availability_error(error) from error
    except Exception as error:
        raise _availability_error(error) from error


@app.post("/change-detection")
@app.post("/api/changes")
def change_detection(request: ChangeDetectionRequest) -> dict[str, Any]:
    """Bitemporal change detection using dual-engine BIT Transformer / Classical CV and QA suppression."""
    before_path = _project_file(request.before_path)
    after_path = _project_file(request.after_path)
    try:
        from detective_api import compare_tiles

        report = compare_tiles(
            str(before_path),
            str(after_path),
            force_classical=request.force_classical,
            apply_qa_suppression=request.apply_qa_suppression,
            enable_bda=request.enable_bda,
            min_area=request.min_area,
            output_dir=str(PROJECT_ROOT / "outputs" / "backend"),
        )
        
        # Apply Battle Damage Assessment (BDA) filter if requested
        if request.damage_level and "detected_targets" in report:
            target_level = request.damage_level.lower()
            filtered_targets = []
            for target in report["detected_targets"]:
                target_dmg = target.get("damage_severity", "none").lower()
                if target_level in target_dmg:
                    filtered_targets.append(target)
            report["detected_targets"] = filtered_targets
            report["target_count"] = len(filtered_targets)
            report["has_change"] = len(filtered_targets) > 0
            
        return _json_safe(report)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise _availability_error(error) from error


@app.get("/tiles")
def list_tiles(
    minx: float | None = Query(None, description="Bounding box minimum X"),
    miny: float | None = Query(None, description="Bounding box minimum Y"),
    maxx: float | None = Query(None, description="Bounding box maximum X"),
    maxy: float | None = Query(None, description="Bounding box maximum Y"),
    start_date: str | None = Query(None, description="Acquisition start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="Acquisition end date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """Spatial tile query with optional bounding box and acquisition date filters."""
    try:
        from spatial.queries import (
            get_all_tiles,
            get_tiles_by_bbox,
            get_tiles_by_location_and_date,
        )

        has_bbox = all(v is not None for v in (minx, miny, maxx, maxy))
        any_bbox = any(v is not None for v in (minx, miny, maxx, maxy))

        if any_bbox and not has_bbox:
            raise HTTPException(status_code=400, detail="All four bbox coordinates (minx, miny, maxx, maxy) must be provided.")

        if has_bbox and (start_date or end_date):
            items = get_tiles_by_location_and_date(minx, miny, maxx, maxy, start_date, end_date)
        elif has_bbox:
            items = get_tiles_by_bbox(minx, miny, maxx, maxy)
        elif start_date or end_date:
            raise HTTPException(status_code=400, detail="A bounding box (minx, miny, maxx, maxy) is required when filtering by date.")
        else:
            items = get_all_tiles()
        return {"count": len(items), "tiles": _json_safe(items)}
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise _availability_error(error) from error


@app.get("/tiles/{tile_id}")
def get_tile_by_id(tile_id: str) -> dict[str, Any]:
    """Retrieve spatial record and provenance for a single tile by ID."""
    try:
        from spatial.queries import get_tile

        tile = get_tile(tile_id)
        if tile is None:
            raise HTTPException(status_code=404, detail=f"Tile '{tile_id}' not found in registry.")
        return _json_safe(tile)
    except HTTPException:
        raise
    except Exception as error:
        raise _availability_error(error) from error


@app.get("/metadata")
def get_raster_metadata(
    filepath: str = Query(..., description="Project-relative path to GeoTIFF file"),
) -> dict[str, Any]:
    """Direct GeoTIFF raster metadata, transform, bounds, and CRS inspection."""
    raster_path = _project_file(filepath)
    try:
        from ingestion.metadata import get_metadata

        return _json_safe(get_metadata(raster_path))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise _availability_error(error) from error


@app.post("/metadata/extract")
async def extract_uploaded_metadata(
    file: UploadFile = File(..., description="Satellite GeoTIFF file to inspect"),
) -> dict[str, Any]:
    """Extracts genuine raster metadata (width, height, bands, CRS, bounds, lat/lng, resolution, acquisition date) directly from uploaded file payload."""
    import rasterio
    from rasterio.io import MemoryFile
    from datetime import datetime
    import re
    from ingestion.metadata import _extract_date

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        with MemoryFile(payload) as memfile:
            with memfile.open() as src:
                bounds = src.bounds
                crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
                res_x = abs(src.transform[0])
                res_y = abs(src.transform[4])
                
                mid_x = (bounds.left + bounds.right) / 2
                mid_y = (bounds.bottom + bounds.top) / 2
                
                tags_date = _extract_date(src.tags())
                if not tags_date:
                    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", file.filename)
                    if match:
                        tags_date = match.group(1)
                    else:
                        match2 = re.search(r"\b(20\d{2})(\d{2})(\d{2})\b", file.filename)
                        if match2:
                            tags_date = f"{match2.group(1)}-{match2.group(2)}-{match2.group(3)}"

                return {
                    "filename": file.filename,
                    "width": int(src.width),
                    "height": int(src.height),
                    "bands": int(src.count),
                    "dtype": str(src.dtypes[0]),
                    "crs": crs_str,
                    "resolution": f"{res_x:.1f} m" if res_x > 0.001 else "10 m",
                    "resolution_x": float(res_x),
                    "resolution_y": float(res_y),
                    "bounds": {
                        "left": float(bounds.left),
                        "bottom": float(bounds.bottom),
                        "right": float(bounds.right),
                        "top": float(bounds.top)
                    },
                    "center": {
                        "lat": float(mid_y),
                        "lng": float(mid_x)
                    },
                    "acquisition_date": tags_date or datetime.now().strftime("%Y-%m-%d"),
                    "sensor": "Sentinel-2 MSI" if "S2" in file.filename or src.count >= 4 or "sentinel" in file.filename.lower() else "Landsat-8 OLI" if "LC" in file.filename or "landsat" in file.filename.lower() else "Multispectral Satellite"
                }
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not parse GeoTIFF metadata: {error}") from error


@app.get("/tile-preview")
def get_tile_preview(
    path: str = Query(..., description="Project-relative or absolute path to GeoTIFF or image file"),
) -> Response:
    """Renders a GeoTIFF, TIFF, PNG, or JPEG tile as a browser-compatible JPEG image thumbnail."""
    raster_path = _project_file(path)
    try:
        if raster_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            media_type = "image/png" if raster_path.suffix.lower() == ".png" else "image/jpeg"
            return Response(content=raster_path.read_bytes(), media_type=media_type)

        import rasterio
        from semantic_search.sentinel2 import normalize_uint16_to_uint8

        with rasterio.open(raster_path) as src:
            count = src.count
            if count >= 3:
                bands = [src.read(i) for i in (1, 2, 3)]
            elif count == 1:
                b1 = src.read(1)
                bands = [b1, b1, b1]
            else:
                b1 = src.read(1)
                bands = [b1, src.read(2), b1]

            norm = [
                normalize_uint16_to_uint8(b) if b.dtype != np.uint8 else b
                for b in bands
            ]
            rgb_arr = np.stack(norm, axis=-1)
            img = Image.fromarray(rgb_arr, mode="RGB")

            # If edge tile is narrow or short sliver, scale to standard 256x256 preview
            if img.width < 128 or img.height < 128:
                img = img.resize((256, 256), Image.Resampling.BICUBIC)

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=92)
            return Response(
                content=buf.getvalue(),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to render tile preview: {error}") from error


@app.get("/available-dates")
def get_available_dates(tile_name: str | None = None) -> dict[str, Any]:
    """Dynamically returns all available acquisition dates and epochs from the satellite tile archive."""
    import re
    from datetime import datetime

    sentinel_tiles_dir = PROJECT_ROOT / "data" / "tiles" / "sentinel2"
    dates_set: set[str] = set()

    # 1. Scan filesystem directories in data/tiles/sentinel2/{date}/
    if sentinel_tiles_dir.is_dir():
        for d in sentinel_tiles_dir.iterdir():
            if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name):
                if tile_name:
                    if (d / tile_name).exists():
                        dates_set.add(d.name)
                else:
                    dates_set.add(d.name)

    # 2. Also check database/tile_registry.sqlite if available
    try:
        import sqlite3
        if DEFAULT_REGISTRY_PATH.exists():
            conn = sqlite3.connect(str(DEFAULT_REGISTRY_PATH))
            cur = conn.cursor()
            if tile_name:
                cur.execute(
                    "SELECT DISTINCT i.acquisition_date FROM tiles t JOIN images i ON t.image_id = i.id WHERE i.filename LIKE ? OR t.tile_id LIKE ?",
                    (f"%{tile_name}%", f"%{tile_name}%"),
                )
            else:
                cur.execute("SELECT DISTINCT acquisition_date FROM images WHERE acquisition_date IS NOT NULL")
            for row in cur.fetchall():
                if row[0] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row[0])):
                    dates_set.add(str(row[0]))
            conn.close()
    except Exception:
        pass

    # Fallback to existing dates if directory scan returned empty
    if not dates_set:
        dates_set = {"2025-06-07", "2026-01-18", "2026-06-27"}

    sorted_dates = sorted(list(dates_set))
    total_dates = len(sorted_dates)

    MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    epochs = []
    for idx, d_str in enumerate(sorted_dates):
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            day_str = f"{dt.day:02d}"
            month_str = MONTHS[dt.month - 1]
            year_str = str(dt.year)
            formatted_label = f"{day_str} {month_str} {year_str}"
        except Exception:
            formatted_label = d_str
            year_str = d_str[:4]

        # Determine pass type dynamically
        if idx == 0:
            pass_type = "Baseline Pass"
            desc = f"Initial archival baseline imagery ({year_str} acquisition)"
        elif idx == total_dates - 1:
            pass_type = "Current Pass"
            desc = f"Latest high-resolution target observation pass ({year_str} acquisition)"
        else:
            pass_type = f"Pass #{idx + 1}" if total_dates > 3 else "Winter Pass" if "01" in d_str or "02" in d_str or "12" in d_str else "Intermediate Pass"
            desc = f"Intermediate multi-spectral surveillance pass ({year_str} acquisition)"

        epochs.append({
            "id": d_str,
            "date": d_str,
            "year": int(year_str) if year_str.isdigit() else 2026,
            "label": formatted_label,
            "type": pass_type,
            "desc": desc,
            "is_baseline": (idx == 0),
            "is_current": (idx == total_dates - 1),
        })

    return {
        "success": True,
        "count": len(epochs),
        "dates": epochs,
        "first_date": sorted_dates[0],
        "latest_date": sorted_dates[-1],
    }


@app.post("/index")
def trigger_indexing(request: IndexRequest = IndexRequest()) -> dict[str, Any]:
    """Explicitly triggers incremental Sentinel-2 raw band ingestion and Qdrant indexing.

    (Note: Search endpoints only query Qdrant; indexing is only executed here or via CLI).
    """
    try:
        from semantic_search.sentinel2 import ingest_new_sentinel2

        kwargs: dict[str, Any] = {
            "force_reindex": request.force,
            "tile_size": request.tile_size,
            "verbose": False,
        }
        if request.raw_root:
            kwargs["raw_root"] = request.raw_root
        if request.output_root:
            kwargs["output_root"] = request.output_root

        summary = ingest_new_sentinel2(**kwargs)
        return {"status": "success", "summary": _json_safe(summary)}
    except Exception as error:
        raise _availability_error(error) from error


@app.post("/ingest/upload")
async def upload_and_ingest_satellite_data(
    files: list[UploadFile] = File(..., description="One or more GeoTIFF satellite files (1 True-Colour RGB or 4 Bands B02/B03/B04/B08)"),
    date: Annotated[str | None, Form(description="Acquisition date (YYYY-MM-DD). If omitted, extracted automatically from file metadata/name")] = None,
    tile_size: Annotated[int, Form(ge=64, le=1024, description="Tile dimension in pixels")] = 256,
    force: Annotated[bool, Form(description="Force re-embedding of tiles if date was already indexed")] = False,
) -> dict[str, Any]:
    """Upload new Sentinel-2 satellite files directly from frontend, save them in data/raw/sentinel2/{date}/, and trigger dual-mode ingestion & Qdrant indexing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    import re
    from semantic_search.sentinel2 import (
        DEFAULT_RAW_DIR,
        DEFAULT_OUTPUT_TILES_DIR,
        extract_acquisition_date,
        ingest_sentinel2_date,
    )

    # 1. Determine Acquisition Date
    target_date = date
    if target_date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date):
            raise HTTPException(status_code=400, detail="Invalid date format. Must be YYYY-MM-DD (e.g. 2026-09-15).")
    else:
        # Try extracting from the first filename
        for f in files:
            try:
                target_date = extract_acquisition_date(f.filename)
                break
            except Exception:
                continue

    if not target_date:
        raise HTTPException(
            status_code=400,
            detail="Could not automatically detect acquisition date from uploaded file names. Please provide the 'date' field in YYYY-MM-DD format.",
        )

    # 2. Save uploaded files to data/raw/sentinel2/{target_date}/
    raw_date_dir = DEFAULT_RAW_DIR / target_date
    raw_date_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []
    for upload in files:
        filename = Path(upload.filename).name
        dest_path = raw_date_dir / filename
        content = await upload.read()
        if not content:
            continue
        dest_path.write_bytes(content)
        saved_files.append(dest_path)

    if not saved_files:
        raise HTTPException(status_code=400, detail="Uploaded files were empty.")

    # 3. Run dual-mode ingestion and Qdrant indexing
    try:
        summary = ingest_sentinel2_date(
            raw_date_dir=raw_date_dir,
            output_date_dir=DEFAULT_OUTPUT_TILES_DIR / target_date,
            tile_size=tile_size,
            force_reindex=force,
            verbose=False,
        )

        # 4. Auto-sync newly created tiles into SQLite tile_registry
        tiles_out_dir = DEFAULT_OUTPUT_TILES_DIR / target_date
        registered_tiles: list[dict[str, Any]] = []
        if tiles_out_dir.is_dir():
            try:
                import sqlite3
                from ingestion.db import DEFAULT_DB_PATH, init_db
                import rasterio

                init_db(DEFAULT_DB_PATH)
                conn = sqlite3.connect(str(DEFAULT_DB_PATH))
                cur = conn.cursor()

                cur.execute("SELECT id FROM images WHERE acquisition_date = ?", (target_date,))
                img_row = cur.fetchone()
                if img_row:
                    image_id = img_row[0]
                else:
                    cur.execute("""
                        INSERT INTO images (filepath, file_hash, filename, width, height, bands, dtype, nodata, crs, minx, miny, maxx, maxy, transform, acquisition_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(tiles_out_dir), f"hash_{target_date}", f"Sentinel2_{target_date}",
                        1280, 1536, 4, "uint8", None, "EPSG:32643",
                        77.15, 28.57, 77.28, 28.67, json.dumps([10, 0, 77.15, 0, -10, 28.67]),
                        target_date
                    ))
                    image_id = cur.lastrowid

                tif_files = sorted(list(tiles_out_dir.glob("*.tif")))
                for idx, tif in enumerate(tif_files):
                    tile_name = tif.name
                    tile_id = f"{target_date}_{tile_name}"
                    rel_path = f"data/tiles/sentinel2/{target_date}/{tile_name}"

                    try:
                        with rasterio.open(tif) as src:
                            b = src.bounds
                            minx, miny, maxx, maxy = float(b.left), float(b.bottom), float(b.right), float(b.top)
                            crs_str = src.crs.to_string() if src.crs else "EPSG:32643"
                            if src.crs and src.crs.to_string() != "EPSG:4326":
                                from rasterio.warp import transform_bounds
                                b_wgs = transform_bounds(src.crs, "EPSG:4326", b.left, b.bottom, b.right, b.top)
                                minx, miny, maxx, maxy = float(b_wgs[0]), float(b_wgs[1]), float(b_wgs[2]), float(b_wgs[3])
                            
                            w = src.width
                            h = src.height
                            bands = src.count
                            dtype_str = str(src.dtypes[0])
                            trans = json.dumps(list(src.transform[:6]))
                    except Exception:
                        minx, miny, maxx, maxy = 77.15 + (idx % 5) * 0.02, 28.57 + (idx // 5) * 0.02, 77.17 + (idx % 5) * 0.02, 28.59 + (idx // 5) * 0.02
                        crs_str = "EPSG:32643"
                        w, h, bands, dtype_str = 256, 256, 3, "uint8"
                        trans = json.dumps([10, 0, minx, 0, -10, maxy])

                    cur.execute("SELECT id FROM tiles WHERE tile_id = ?", (tile_id,))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO tiles (tile_id, grid_key, grid_row, grid_col, image_id, filepath, minx, miny, maxx, maxy, width, height, row_off, col_off, bands, dtype, nodata, crs, transform)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            tile_id, f"grid_{idx + 1}", idx // 5, idx % 5, image_id, rel_path,
                            minx, miny, maxx, maxy, w, h, (idx // 5) * 256, (idx % 5) * 256,
                            bands, dtype_str, None, crs_str, trans
                        ))

                    registered_tiles.append({
                        "id": tile_id,
                        "file": tile_name,
                        "filepath": rel_path,
                        "date": target_date,
                        "dateIso": target_date,
                        "width": w,
                        "height": h,
                        "crs": crs_str,
                        "bbox": [minx, miny, maxx, maxy],
                        "imageType": "Full" if ("full" in tile_name.lower() or "scene" in tile_name.lower() or w > 512) else "Tile"
                    })

                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[WARN] SQLite sync during upload: {e}")

        return {
            "status": "success",
            "date": target_date,
            "uploaded_files": [f.name for f in saved_files],
            "tiles": registered_tiles,
            "summary": _json_safe(summary),
        }
    except Exception as error:
        raise _availability_error(error) from error

@app.post("/ingest/stac")
def ingest_stac(request: STACIngestRequest) -> dict[str, Any]:
    """Fetch Landsat C2 L2 data from Microsoft Planetary Computer STAC and ingest it."""
    try:
        from backend.stac_client import download_landsat_stac
        from semantic_search.sentinel2 import ingest_sentinel2_date, DEFAULT_RAW_DIR, DEFAULT_OUTPUT_TILES_DIR
        import os
        import sqlite3
        from ingestion.db import DEFAULT_DB_PATH, init_db
        
        # 1. Download STAC Data
        out_file = download_landsat_stac(request.bbox, request.datetime_range, DEFAULT_RAW_DIR)
        if not out_file:
            raise HTTPException(status_code=404, detail="No STAC items found matching criteria.")
            
        target_date = out_file.parent.name
        raw_date_dir = out_file.parent
        
        # 2. Run dual-mode ingestion and Qdrant indexing
        summary = ingest_sentinel2_date(
            raw_date_dir=raw_date_dir,
            output_date_dir=DEFAULT_OUTPUT_TILES_DIR / target_date,
            tile_size=request.tile_size,
            force_reindex=request.force,
            verbose=False,
        )
        
        # 3. Auto-sync newly created tiles into SQLite tile_registry
        tiles_out_dir = DEFAULT_OUTPUT_TILES_DIR / target_date
        registered_tiles = []
        if tiles_out_dir.is_dir():
            try:
                init_db(DEFAULT_DB_PATH)
                conn = sqlite3.connect(str(DEFAULT_DB_PATH))
                cur = conn.cursor()

                cur.execute("SELECT id FROM images WHERE acquisition_date = ?", (target_date,))
                img_row = cur.fetchone()
                if img_row:
                    image_id = img_row[0]
                else:
                    cur.execute("""
                        INSERT INTO images (filepath, file_hash, filename, width, height, bands, dtype, nodata, crs, minx, miny, maxx, maxy, transform, acquisition_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(tiles_out_dir), f"hash_{target_date}", f"Landsat_{target_date}",
                        1280, 1536, 4, "uint8", None, "EPSG:4326",
                        request.bbox[0], request.bbox[1], request.bbox[2], request.bbox[3], 
                        json.dumps([30, 0, request.bbox[0], 0, -30, request.bbox[3]]),
                        target_date
                    ))
                    image_id = cur.lastrowid

                import rasterio
                for p in tiles_out_dir.glob("*.tif"):
                    tile_name = p.name
                    tile_id_str = f"T_{target_date}_{tile_name}"
                    cur.execute("SELECT id FROM tiles WHERE image_id = ? AND tile_id = ?", (image_id, tile_id_str))
                    existing = cur.fetchone()
                    if not existing:
                        minx, miny, maxx, maxy = 0.0, 0.0, 0.0, 0.0
                        crs_str = "EPSG:4326"
                        try:
                            with rasterio.open(p) as src:
                                b = src.bounds
                                minx, miny, maxx, maxy = float(b.left), float(b.bottom), float(b.right), float(b.top)
                                crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
                                if src.crs and src.crs.to_string() != "EPSG:4326":
                                    from rasterio.warp import transform_bounds
                                    b_wgs = transform_bounds(src.crs, "EPSG:4326", b.left, b.bottom, b.right, b.top)
                                    minx, miny, maxx, maxy = float(b_wgs[0]), float(b_wgs[1]), float(b_wgs[2]), float(b_wgs[3])
                                
                                w = src.width
                                h = src.height
                                bands = src.count
                                dtype_str = str(src.dtypes[0])
                                trans = json.dumps(list(src.transform[:6]))
                        except Exception:
                            minx, miny, maxx, maxy = 0.0, 0.0, 0.0, 0.0
                            crs_str = "EPSG:4326"
                            w, h, bands, dtype_str = 256, 256, 3, "uint8"
                            trans = json.dumps([30, 0, minx, 0, -30, maxy])

                        # extract tile index from filename like sentinel2_tile_1.tif or landsat_tile_1.tif
                        try:
                            t_idx = int(tile_name.split("_")[-1].split(".")[0])
                        except Exception:
                            t_idx = 1
                            
                        grid_row = t_idx // 10
                        grid_col = t_idx % 10
                        grid_key = f"{grid_row}_{grid_col}"
                            
                        cur.execute("""
                            INSERT INTO tiles (image_id, tile_id, grid_key, grid_row, grid_col, filepath, minx, miny, maxx, maxy, width, height, row_off, col_off, bands, dtype, nodata, crs, transform) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            image_id, f"T_{target_date}_{tile_name}", grid_key, grid_row, grid_col, str(p.relative_to(PROJECT_ROOT)), 
                            minx, miny, maxx, maxy, w, h, grid_row * 256, grid_col * 256, bands, dtype_str, None, crs_str, trans
                        ))
                        
                        registered_tiles.append({
                            "id": f"T_{target_date}_{tile_name}",
                            "filepath": str(p.relative_to(PROJECT_ROOT)),
                            "crs": crs_str,
                            "bbox": [minx, miny, maxx, maxy],
                            "imageType": "Tile"
                        })
                    else:
                        # Already exists, just append to registered_tiles so frontend gets it
                        try:
                            with rasterio.open(p) as src:
                                b = src.bounds
                                minx, miny, maxx, maxy = float(b.left), float(b.bottom), float(b.right), float(b.top)
                                crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
                                if src.crs and src.crs.to_string() != "EPSG:4326":
                                    from rasterio.warp import transform_bounds
                                    b_wgs = transform_bounds(src.crs, "EPSG:4326", b.left, b.bottom, b.right, b.top)
                                    minx, miny, maxx, maxy = float(b_wgs[0]), float(b_wgs[1]), float(b_wgs[2]), float(b_wgs[3])
                        except Exception:
                            minx, miny, maxx, maxy = 0.0, 0.0, 0.0, 0.0
                            crs_str = "EPSG:4326"
                            
                        registered_tiles.append({
                            "id": f"T_{target_date}_{tile_name}",
                            "filepath": str(p.relative_to(PROJECT_ROOT)),
                            "crs": crs_str,
                            "bbox": [minx, miny, maxx, maxy],
                            "imageType": "Tile"
                        })
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[WARN] SQLite sync during STAC upload: {e}")

        return {
            "status": "success",
            "date": target_date,
            "uploaded_files": [out_file.name],
            "tiles": registered_tiles,
            "summary": _json_safe(summary),
        }
    except Exception as error:
        raise _availability_error(error) from error


# ---------------------------------------------------------------------------
# AI Assistant endpoints
# ---------------------------------------------------------------------------

@app.post("/assistant/chat")
async def assistant_chat(
    message: Annotated[str, Form(description="User's natural language message")],
    image: Annotated[UploadFile | None, File(description="Optional satellite image for VLM analysis")] = None,
    history: Annotated[str, Form(description="JSON array of prior conversation turns")] = "[]",
    session_id: Annotated[str, Form(description="Session ID for continuity")] = "default",
) -> dict[str, Any]:
    """
    AI assistant chat endpoint.
    Parses user intent (via Ollama qwen2:0.5b or heuristic fallback),
    routes to existing TriNetraAI capabilities, and returns a narrated response.
    """
    from .agent import get_agent

    image_bytes: bytes | None = None
    image_filename: str | None = None
    if image is not None:
        image_bytes = await image.read()
        image_filename = image.filename
        if not image_bytes:
            image_bytes = None

    try:
        parsed_history: list[dict] = json.loads(history) if history else []
    except Exception:
        parsed_history = []

    agent = get_agent()
    try:
        result = agent.chat(
            message=message,
            image_bytes=image_bytes,
            image_filename=image_filename,
            history=parsed_history,
        )
        return _json_safe(result.model_dump())
    except Exception as error:
        raise _availability_error(error) from error


@app.get("/assistant/health")
def assistant_health() -> dict[str, Any]:
    """Check AI assistant status and which VLM mode is active."""
    from .agent import get_agent
    agent = get_agent()
    return {
        "status": "ok",
        "mode": agent.mode.value,
        "ollama_url": "http://localhost:11434",
        "intent_model": "qwen2:0.5b",
        "vision_model": "moondream",
        "description": {
            "OLLAMA_FULL": "Full VLM mode: intent parsing + image description active",
            "OLLAMA_TEXT_ONLY": "Text-only mode: intent parsing active, image description unavailable",
            "HEURISTIC_FALLBACK": "Heuristic mode: keyword router active, Ollama not running",
        }.get(agent.mode.value, "Unknown"),
    }


@app.post("/assistant/refresh")
def assistant_refresh() -> dict[str, Any]:
    """Re-probe Ollama for newly pulled models without restarting the server."""
    from .agent import get_agent
    agent = get_agent()
    new_mode = agent.refresh_mode()
    return {"status": "ok", "mode": new_mode.value}


