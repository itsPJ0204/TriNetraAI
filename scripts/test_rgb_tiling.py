from semantic_search.sentinel2 import generate_sentinel2_rgb_tiles

result = generate_sentinel2_rgb_tiles(
    raw_date_dir="data/raw/sentinel2/2026-01-18",
    output_date_dir="data/tiles/sentinel2/2026-01-18",
    tile_size=256,
)

print("Date:", result["date"])
print("Tiles generated:", result["num_tiles"])

for tile in result["tiles"]:
    print(tile)