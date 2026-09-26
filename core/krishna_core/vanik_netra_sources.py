from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
import csv
import json
import os
import re


@dataclass(frozen=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float

    def __post_init__(self):
        if not (-180 <= self.west < self.east <= 180):
            raise ValueError("invalid west/east bounding box")
        if not (-90 <= self.south < self.north <= 90):
            raise ValueError("invalid south/north bounding box")

    def as_dict(self) -> dict[str, float]:
        return {"west": self.west, "south": self.south, "east": self.east, "north": self.north}

    @classmethod
    def from_value(cls, value: Any) -> "BoundingBox":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(
                float(value["west"]), float(value["south"]),
                float(value["east"]), float(value["north"]),
            )
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return cls(*(float(x) for x in value))
        raise ValueError("bbox must be {west,south,east,north} or [west,south,east,north]")


class OverturePlacesAdapter:
    """Live, free Overture Places reader using DuckDB against public GeoParquet."""

    STAC = "https://stac.overturemaps.org/catalog.json"
    RELEASE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.\d+$")

    def __init__(self, state_dir: str | Path, release: str | None = None):
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.extension_dir = self.state_dir / "duckdb-extensions"
        self.extension_dir.mkdir(parents=True, exist_ok=True)
        self.release = str(release or os.getenv("OVERTURE_RELEASE") or "").strip() or None

    @staticmethod
    def _duckdb():
        try:
            import duckdb  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "DuckDB is required for live Overture scans. Install the free duckdb package in KRISHNA's E-drive venv."
            ) from exc
        return duckdb

    def discover_release(self, timeout: int = 10) -> str:
        if self.release:
            if not self.RELEASE_RE.match(self.release):
                raise ValueError("invalid Overture release format")
            return self.release
        req = Request(self.STAC, headers={"User-Agent": "KRISHNA-VANIK-NETRA/1.0"})
        with urlopen(req, timeout=max(2, min(int(timeout), 30))) as response:
            data = json.loads(response.read().decode("utf-8"))
        release = str(data.get("latest") or "").strip().rstrip("/")
        if not self.RELEASE_RE.match(release):
            raise RuntimeError("Overture STAC did not provide a valid latest release")
        return release

    def status(self) -> dict[str, Any]:
        try:
            self._duckdb()
            duckdb_available = True
        except RuntimeError:
            duckdb_available = False
        return {
            "id": "overture",
            "free": True,
            "connection_required": False,
            "live_scan": duckdb_available,
            "duckdb_available": duckdb_available,
            "release": self.release or "discover-via-stac",
            "extension_dir": str(self.extension_dir),
        }

    def scan(
        self,
        bbox: BoundingBox | dict | list | tuple,
        *,
        category: str | None = None,
        limit: int = 1000,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        box = BoundingBox.from_value(bbox)
        limit = max(1, min(int(limit), 5000))
        min_confidence = max(0.0, min(1.0, float(min_confidence)))
        release = self.discover_release()
        duckdb = self._duckdb()
        con = duckdb.connect(database=":memory:")
        ext = str(self.extension_dir).replace("\\", "/").replace("'", "''")
        try:
            con.execute(f"SET extension_directory='{ext}'")
            try:
                con.execute("LOAD httpfs")
            except Exception:
                con.execute("INSTALL httpfs")
                con.execute("LOAD httpfs")
            con.execute("SET s3_region='us-west-2'")
            path = (
                "s3://overturemaps-us-west-2/release/"
                + release
                + "/theme=places/type=place/*"
            )
            filters = [
                "bbox.xmin BETWEEN ? AND ?",
                "bbox.ymin BETWEEN ? AND ?",
                "COALESCE(confidence,0) >= ?",
            ]
            params: list[Any] = [box.west, box.east, box.south, box.north, min_confidence]
            if category:
                filters.append("taxonomy.primary ILIKE ?")
                params.append("%" + str(category).strip() + "%")
            sql = f"""
                SELECT
                    id,
                    names.primary AS name,
                    basic_category,
                    taxonomy.primary AS category,
                    confidence,
                    websites[1] AS website,
                    emails[1] AS email,
                    phones[1] AS phone,
                    socials[1] AS social,
                    addresses[1].freeform AS address,
                    addresses[1].locality AS locality,
                    addresses[1].postcode AS postcode,
                    addresses[1].region AS state,
                    addresses[1].country AS country,
                    bbox.xmin AS longitude,
                    bbox.ymin AS latitude,
                    operating_status
                FROM read_parquet('{path}', filename=true, hive_partitioning=1)
                WHERE {" AND ".join(filters)}
                LIMIT {limit}
            """
            cur = con.execute(sql, params)
            columns = [x[0] for x in cur.description]
            out = []
            for values in cur.fetchall():
                row = dict(zip(columns, values))
                row["source"] = "overture"
                row["source_id"] = row.get("id")
                row["overture_release"] = release
                out.append(row)
            return out
        finally:
            con.close()


class FoursquareOSAdapter:
    """Free Foursquare OS enrichment from owner-connected/local exports.

    Foursquare OS Places now uses its Places Portal/Iceberg access model. This
    adapter deliberately does not invent anonymous credentials or paid API use.
    """

    def __init__(self, token_env: str = "FOURSQUARE_OS_TOKEN"):
        self.token_env = token_env

    def status(self) -> dict[str, Any]:
        return {
            "id": "foursquare_os",
            "free": True,
            "connection_required": True,
            "connected": bool(os.getenv(self.token_env)),
            "delivery": "Places Portal / Iceberg or owner-exported local file",
            "paid_fallback": False,
        }

    @staticmethod
    def load_local(path: str | Path, *, limit: int = 5000) -> list[dict[str, Any]]:
        source = Path(path).resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))
        limit = max(1, min(int(limit), 100000))
        suffix = source.suffix.lower()
        rows: list[dict[str, Any]] = []
        if suffix == ".csv":
            with source.open("r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    row = dict(row)
                    row["source"] = "foursquare_os"
                    row["phone"] = row.get("phone") or row.get("tel")
                    labels = row.get("fsq_category_labels")
                    if labels and not row.get("category"):
                        try:
                            parsed = json.loads(labels) if isinstance(labels,str) and labels.strip().startswith("[") else labels
                        except Exception:
                            parsed = labels
                        if isinstance(parsed,list) and parsed:
                            row["category"] = parsed[0]
                        elif parsed:
                            row["category"] = str(parsed).split(",")[0].strip()
                    rows.append(row)
                    if len(rows) >= limit:
                        break
            return rows
        if suffix in {".jsonl", ".ndjson"}:
            with source.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if isinstance(row, dict):
                        row["source"] = "foursquare_os"
                        rows.append(row)
                    if len(rows) >= limit:
                        break
            return rows
        if suffix == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data = data.get("places") or data.get("records") or data.get("features") or []
            for item in list(data)[:limit]:
                if isinstance(item, dict):
                    row = item.get("properties") if item.get("type") == "Feature" else item
                    row = dict(row or {})
                    row["source"] = "foursquare_os"
                    rows.append(row)
            return rows
        if suffix in {".parquet", ".geoparquet"}:
            try:
                import duckdb  # type: ignore
            except Exception as exc:
                raise RuntimeError("DuckDB is required to read Foursquare Parquet exports") from exc
            con = duckdb.connect(database=":memory:")
            try:
                safe = str(source).replace("'", "''")
                cur = con.execute(f"SELECT * FROM read_parquet('{safe}') LIMIT {limit}")
                cols = [x[0] for x in cur.description]
                for values in cur.fetchall():
                    row = dict(zip(cols, values))
                    row["source"] = "foursquare_os"
                    rows.append(row)
                return rows
            finally:
                con.close()
        raise ValueError("supported Foursquare OS local formats: csv, json, jsonl, parquet")


class OSMExtractAdapter:
    """Free OpenStreetMap extract adapter for local GeoJSON exports."""

    GEOFABRIK_INDIA = "https://download.geofabrik.de/asia/india-latest.osm.pbf"
    GEOFABRIK_EASTERN_ZONE = "https://download.geofabrik.de/asia/india/eastern-zone-latest.osm.pbf"

    def status(self) -> dict[str, Any]:
        return {
            "id": "openstreetmap_extract",
            "free": True,
            "connection_required": False,
            "live_public_overpass_bulk_scan": False,
            "preferred": "local Geofabrik/HOTOSM extract",
            "india_pbf": self.GEOFABRIK_INDIA,
            "eastern_zone_pbf": self.GEOFABRIK_EASTERN_ZONE,
        }

    @staticmethod
    def load_geojson(path: str | Path, *, limit: int = 100000) -> list[dict[str, Any]]:
        source = Path(path).resolve()
        if not source.exists():
            raise FileNotFoundError(str(source))
        data = json.loads(source.read_text(encoding="utf-8"))
        features = data.get("features") if isinstance(data, dict) else data
        rows: list[dict[str, Any]] = []
        for feature in list(features or [])[: max(1, min(int(limit), 100000))]:
            if not isinstance(feature, dict):
                continue
            props = dict(feature.get("properties") or {})
            geom = feature.get("geometry") or {}
            coords = geom.get("coordinates") if isinstance(geom, dict) else None
            if isinstance(coords, list) and len(coords) >= 2 and not isinstance(coords[0], list):
                props["longitude"], props["latitude"] = coords[0], coords[1]
            props["source"] = "openstreetmap_extract"
            props["source_id"] = props.get("osm_id") or feature.get("id")
            props["name"] = props.get("name") or props.get("brand")
            props["category"] = (
                props.get("shop") or props.get("amenity") or props.get("office")
                or props.get("craft") or props.get("tourism") or props.get("healthcare")
            )
            props["phone"] = props.get("phone") or props.get("contact:phone")
            props["email"] = props.get("email") or props.get("contact:email")
            props["website"] = props.get("website") or props.get("contact:website")
            rows.append(props)
        return rows


class FreeMarketSourceRegistry:
    def __init__(self, state_dir: str | Path):
        self.overture = OverturePlacesAdapter(Path(state_dir) / "overture")
        self.foursquare = FoursquareOSAdapter()
        self.osm = OSMExtractAdapter()

    def status(self) -> dict[str, Any]:
        return {
            "zero_spend": True,
            "paid_fallback": False,
            "sources": {
                "overture": self.overture.status(),
                "foursquare_os": self.foursquare.status(),
                "openstreetmap_extract": self.osm.status(),
            },
        }
