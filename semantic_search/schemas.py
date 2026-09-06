"""Data schemas for semantic search results and geospatial metadata."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    """Clean, typed representation of a semantic search match."""

    tile_name: str
    image_path: str
    score: float
    crs: str
    bounds: dict[str, float]
    width: int
    height: int
    date: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a clean dictionary."""
        return {
            "tile_name": self.tile_name,
            "image_path": self.image_path,
            "score": self.score,
            "crs": self.crs,
            "bounds": dict(self.bounds),
            "width": self.width,
            "height": self.height,
            "date": self.date,
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access for backwards compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Allow 'in' membership tests for backwards compatibility."""
        return hasattr(self, key)
