"""
CarbonKarma — Geospatial utility functions.
Uses shapely when available; falls back to pure numpy geometry otherwise.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    from shapely.geometry import Point, Polygon, shape as shp_shape
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

LocationDict = Dict[str, Any]

def parse_location(lat=None, lon=None, geojson=None) -> LocationDict:
    if geojson is not None:
        return _parse_geojson(geojson)
    if lat is not None and lon is not None:
        return {
            "lat": float(lat), "lon": float(lon),
            "bbox": (float(lon)-0.005, float(lat)-0.005, float(lon)+0.005, float(lat)+0.005),
            "polygon_coords": None, "area_ha": None,
        }
    raise ValueError("Provide lat+lon or geojson.")

def _parse_geojson(geojson: Dict) -> LocationDict:
    geometry = geojson.get("geometry", geojson) if geojson.get("type") == "Feature" else geojson
    coords_list = geometry.get("coordinates", [[]])[0]   # outer ring

    lons = [c[0] for c in coords_list]
    lats = [c[1] for c in coords_list]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    centroid_lat = sum(lats) / len(lats)
    centroid_lon = sum(lons) / len(lons)

    lat_rad = math.radians(centroid_lat)
    width_m  = (max_lon - min_lon) * 111_320 * math.cos(lat_rad)
    height_m = (max_lat - min_lat) * 111_320
    area_ha  = (width_m * height_m) / 10_000

    return {
        "lat": centroid_lat, "lon": centroid_lon,
        "bbox": (min_lon, min_lat, max_lon, max_lat),
        "polygon_coords": coords_list,
        "area_ha": round(area_ha, 4),
    }

def latlon_to_pixel(lat, lon, bbox, patch_size) -> Tuple[int, int]:
    min_lon, min_lat, max_lon, max_lat = bbox
    col = int((lon - min_lon) / max(max_lon - min_lon, 1e-9) * patch_size)
    row = int((max_lat - lat) / max(max_lat - min_lat, 1e-9) * patch_size)
    return max(0, min(patch_size-1, row)), max(0, min(patch_size-1, col))

def pixel_to_latlon(row, col, bbox, patch_size) -> Tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    lat = max_lat - (row / patch_size) * (max_lat - min_lat)
    lon = min_lon + (col / patch_size) * (max_lon - min_lon)
    return round(lat, 6), round(lon, 6)

def build_heatmap_grid(bbox, patch_size, values) -> List[Dict]:
    import cv2
    if values.shape != (patch_size, patch_size):
        values = cv2.resize(values.astype(np.float32), (patch_size, patch_size), interpolation=cv2.INTER_NEAREST)
    grid = []
    for row in range(patch_size):
        for col in range(patch_size):
            lat, lon = pixel_to_latlon(row, col, bbox, patch_size)
            grid.append({"lat": lat, "lon": lon, "value": round(float(values[row, col]), 6)})
    return grid

def _point_in_polygon(px, py, polygon_coords) -> bool:
    """Ray-casting algorithm."""
    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / max(yj - yi, 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def filter_points_in_polygon(points, polygon_coords) -> List[Dict]:
    if polygon_coords is None:
        return points
    if SHAPELY_AVAILABLE:
        poly = Polygon([(c[0], c[1]) for c in polygon_coords])
        return [p for p in points if poly.contains(Point(p["lon"], p["lat"]))]
    return [p for p in points if _point_in_polygon(p["lon"], p["lat"], polygon_coords)]
