from __future__ import annotations

from collections import Counter
from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import quote_plus

from .vanik_netra_sources import BoundingBox, FreeMarketSourceRegistry
from .vanik_netra_store import VanikNetraStore
import re


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).lower())


def _first(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


class VanikNetra:
    """Free-first local market-intelligence specialist for MANIBHADRA.

    VANIK-NETRA fuses lawful/open business-place data into market intelligence,
    scores commercial opportunities, and can hand selected records to MANIBHADRA
    CRM. It does not send outreach, spend money, scrape Google Maps in bulk, or
    mutate third-party systems.
    """

    NAME = "VANIK-NETRA"
    ROLE = "market intelligence, POI fusion, competition analysis and opportunity scouting"

    SOURCE_POLICY = {
        "overture": {
            "priority": 1,
            "purpose": "primary open place/POI source",
            "bulk_allowed_by_agent": True,
            "cost": 0,
        },
        "foursquare_os": {
            "priority": 2,
            "purpose": "open-source place/contact/category enrichment",
            "bulk_allowed_by_agent": True,
            "cost": 0,
        },
        "openstreetmap_extract": {
            "priority": 3,
            "purpose": "open map/shop/amenity/road context from extracts",
            "bulk_allowed_by_agent": True,
            "cost": 0,
        },
        "business_website": {
            "priority": 4,
            "purpose": "public first-party website enrichment subject to site rules",
            "bulk_allowed_by_agent": False,
            "cost": 0,
        },
        "google_maps_bulk_scrape": {
            "priority": 99,
            "purpose": "not a production ingestion source",
            "bulk_allowed_by_agent": False,
            "cost": 0,
            "blocked": True,
        },
        "public_nominatim_bulk_grid": {
            "priority": 99,
            "purpose": "public service is not a bulk POI extraction backend",
            "bulk_allowed_by_agent": False,
            "cost": 0,
            "blocked": True,
        },
    }

    def __init__(self, crm=None, *, store: VanikNetraStore | None = None, sources: FreeMarketSourceRegistry | None = None):
        self.crm = crm
        self.store = store
        self.source_registry = sources

    @staticmethod
    def _coords(row: dict[str, Any]) -> tuple[float | None, float | None]:
        lat = _float(row.get("latitude", row.get("lat")))
        lon = _float(row.get("longitude", row.get("lon", row.get("lng"))))
        geometry = row.get("geometry")
        if (lat is None or lon is None) and isinstance(geometry, dict):
            coords = geometry.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lon = lon if lon is not None else _float(coords[0])
                lat = lat if lat is not None else _float(coords[1])
        return lat, lon

    @staticmethod
    def _pick_contact(row: dict[str, Any], singular: str, plural: str) -> str:
        value = row.get(singular)
        if value:
            return _text(value)
        values = _list(row.get(plural))
        for item in values:
            if isinstance(item, dict):
                candidate = _first(item.get("value"), item.get("phone"), item.get("email"), item.get("url"))
            else:
                candidate = _text(item)
            if candidate:
                return candidate
        return ""

    @staticmethod
    def _name(row: dict[str, Any]) -> str:
        names = row.get("names")
        if isinstance(names, dict):
            primary = names.get("primary")
            if isinstance(primary, str):
                return _text(primary)
            if isinstance(primary, dict):
                return _first(primary.get("value"), primary.get("name"))
            common = names.get("common")
            if isinstance(common, list) and common:
                item = common[0]
                if isinstance(item, dict):
                    return _first(item.get("value"), item.get("name"))
        return _first(row.get("name"), row.get("title"), row.get("business_name"))

    @staticmethod
    def _address(row: dict[str, Any]) -> str:
        direct = _first(row.get("full_address"), row.get("address"), row.get("formatted_address"))
        if direct:
            return direct
        parts = [
            row.get("address_line"), row.get("locality"), row.get("city"),
            row.get("district"), row.get("region"), row.get("state"),
            row.get("postcode"), row.get("postal_code"), row.get("country"),
        ]
        return ", ".join(_text(x) for x in parts if _text(x))

    @staticmethod
    def _category(row: dict[str, Any]) -> str:
        direct = _first(
            row.get("primary_category"), row.get("basic_category"),
            row.get("category"), row.get("category_name"),
        )
        if direct:
            return direct
        taxonomy = row.get("taxonomy")
        if isinstance(taxonomy, dict):
            return _first(taxonomy.get("primary"), taxonomy.get("category"))
        categories = row.get("categories")
        if isinstance(categories, list) and categories:
            first = categories[0]
            if isinstance(first, dict):
                return _first(first.get("name"), first.get("label"), first.get("id"))
            return _text(first)
        return "uncategorized"

    @staticmethod
    def _source(row: dict[str, Any]) -> str:
        source = row.get("source")
        if isinstance(source, dict):
            return _first(source.get("name"), source.get("dataset"))
        if source:
            return _text(source)
        return _first(row.get("dataset"), row.get("provider"), "unknown")

    @classmethod
    def normalize_place(cls, row: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise TypeError("place row must be an object")
        name = cls._name(row)
        if not name:
            raise ValueError("place name is required")
        lat, lon = cls._coords(row)
        phone = cls._pick_contact(row, "phone", "phones")
        email = cls._pick_contact(row, "email", "emails")
        website = cls._pick_contact(row, "website", "websites")
        category = cls._category(row)
        address = cls._address(row)
        source = cls._source(row)
        confidence = _float(row.get("confidence"))
        if confidence is None:
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        source_id = _first(
            row.get("source_id"), row.get("fsq_place_id"), row.get("id"),
        )
        socials = row.get("socials")
        if not isinstance(socials, dict):
            socials = {
                key: _text(row.get(key))
                for key in ("facebook", "instagram", "twitter", "x")
                if _text(row.get(key))
            }

        nav_query = " ".join(x for x in (name, address) if x).strip()
        if lat is not None and lon is not None:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat:.7f}%2C{lon:.7f}"
        else:
            maps_url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(nav_query)

        return {
            "business_id": _first(row.get("business_id"), source_id, _norm(name + "|" + address)),
            "name": name,
            "brand": _text(row.get("brand")),
            "primary_category": category,
            "phone": phone,
            "email": email,
            "website": website,
            "socials": socials,
            "address": address,
            "locality": _first(row.get("locality"), row.get("neighborhood")),
            "city": _text(row.get("city")),
            "district": _text(row.get("district")),
            "state": _first(row.get("state"), row.get("region")),
            "postcode": _first(row.get("postcode"), row.get("postal_code")),
            "country": _text(row.get("country")),
            "latitude": lat,
            "longitude": lon,
            "operating_status": _first(row.get("operating_status"), row.get("status"), "unknown").lower(),
            "confidence": round(confidence, 4),
            "source": source,
            "source_id": source_id,
            "source_ids": [source_id] if source_id else [],
            "sources": [source] if source else [],
            "refreshed_at": _first(row.get("refreshed_at"), row.get("updated_at"), row.get("date_refreshed")),
            "google_maps_navigation_url": maps_url,
        }

    @staticmethod
    def _distance_m(a: dict[str, Any], b: dict[str, Any]) -> float | None:
        lat1, lon1 = a.get("latitude"), a.get("longitude")
        lat2, lon2 = b.get("latitude"), b.get("longitude")
        if None in (lat1, lon1, lat2, lon2):
            return None
        p1, p2 = radians(float(lat1)), radians(float(lat2))
        dp = radians(float(lat2) - float(lat1))
        dl = radians(float(lon2) - float(lon1))
        h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
        return 6371000.0 * 2 * asin(sqrt(h))

    @classmethod
    def _same_place(cls, a: dict[str, Any], b: dict[str, Any]) -> bool:
        phone_a, phone_b = _norm(a.get("phone")), _norm(b.get("phone"))
        if phone_a and phone_b and phone_a == phone_b:
            return True
        email_a, email_b = _norm(a.get("email")), _norm(b.get("email"))
        if email_a and email_b and email_a == email_b:
            return True
        web_a, web_b = _norm(a.get("website")), _norm(b.get("website"))
        if web_a and web_b and web_a == web_b:
            return True
        same_name = _norm(a.get("name")) and _norm(a.get("name")) == _norm(b.get("name"))
        same_address = _norm(a.get("address")) and _norm(a.get("address")) == _norm(b.get("address"))
        if same_name and same_address:
            return True
        distance = cls._distance_m(a, b)
        return bool(same_name and distance is not None and distance <= 40.0)

    @staticmethod
    def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
        out = dict(a)
        for key in (
            "brand", "phone", "email", "website", "address", "locality", "city",
            "district", "state", "postcode", "country", "refreshed_at",
        ):
            if not out.get(key) and b.get(key):
                out[key] = b[key]
        if out.get("primary_category") in ("", "uncategorized") and b.get("primary_category"):
            out["primary_category"] = b["primary_category"]
        if out.get("latitude") is None and b.get("latitude") is not None:
            out["latitude"] = b["latitude"]
            out["longitude"] = b.get("longitude")
            out["google_maps_navigation_url"] = b.get("google_maps_navigation_url")
        out["confidence"] = round(max(float(out.get("confidence") or 0), float(b.get("confidence") or 0)), 4)
        out["source_ids"] = list(dict.fromkeys(_list(out.get("source_ids")) + _list(b.get("source_ids"))))
        out["sources"] = list(dict.fromkeys(_list(out.get("sources")) + _list(b.get("sources"))))
        socials = dict(out.get("socials") or {})
        socials.update({k: v for k, v in (b.get("socials") or {}).items() if v and not socials.get(k)})
        out["socials"] = socials
        return out

    @classmethod
    def deduplicate(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for raw in rows or []:
            row = raw if "business_id" in raw and "primary_category" in raw else cls.normalize_place(raw)
            match = next((x for x in merged if cls._same_place(x, row)), None)
            if match is None:
                merged.append(dict(row))
            else:
                updated = cls._merge(match, row)
                match.clear()
                match.update(updated)
        return merged

    @staticmethod
    def opportunity_score(
        row: dict[str, Any],
        *,
        category_value: float = 0.5,
        demand_proxy: float = 0.5,
        competition_opportunity: float = 0.5,
        ai_visibility_gap: float | None = None,
    ) -> dict[str, Any]:
        for name, value in {
            "category_value": category_value,
            "demand_proxy": demand_proxy,
            "competition_opportunity": competition_opportunity,
        }.items():
            if not 0 <= float(value) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if ai_visibility_gap is None:
            ai_visibility_gap = 1.0 if not row.get("website") else 0.4
        if not 0 <= float(ai_visibility_gap) <= 1:
            raise ValueError("ai_visibility_gap must be between 0 and 1")

        digital_gap = 1.0 if not row.get("website") else 0.25
        reachable = 1.0 if row.get("phone") and row.get("email") else 0.7 if row.get("phone") or row.get("email") else 0.2
        confidence = max(0.0, min(1.0, float(row.get("confidence") or 0.5)))
        score = (
            25 * digital_gap
            + 20 * reachable
            + 15 * confidence
            + 15 * float(category_value)
            + 10 * float(demand_proxy)
            + 10 * float(competition_opportunity)
            + 5 * float(ai_visibility_gap)
        )
        reasons = []
        if not row.get("website"):
            reasons.append("no website detected")
        if row.get("phone"):
            reasons.append("phone available")
        if row.get("email"):
            reasons.append("email available")
        if confidence >= 0.8:
            reasons.append("high-confidence place record")
        return {"score": round(score, 2), "reasons": reasons}

    @classmethod
    def analyze_area(cls, rows: list[dict[str, Any]]) -> dict[str, Any]:
        places = cls.deduplicate(rows)
        categories = Counter(_text(x.get("primary_category")) or "uncategorized" for x in places)
        with_phone = sum(bool(x.get("phone")) for x in places)
        with_email = sum(bool(x.get("email")) for x in places)
        with_website = sum(bool(x.get("website")) for x in places)
        no_website_reachable = sum(
            bool(not x.get("website") and (x.get("phone") or x.get("email")))
            for x in places
        )
        return {
            "businesses": len(places),
            "categories": [
                {"category": key, "count": count}
                for key, count in categories.most_common()
            ],
            "contactability": {
                "phone": with_phone,
                "email": with_email,
                "website": with_website,
            },
            "opportunities": {
                "no_website": len(places) - with_website,
                "no_website_but_reachable": no_website_reachable,
            },
            "records": places,
        }

    @classmethod
    def crm_lead_payload(cls, row: dict[str, Any], *, score: float | None = None) -> dict[str, Any]:
        place = row if "business_id" in row and "primary_category" in row else cls.normalize_place(row)
        scored = cls.opportunity_score(place) if score is None else {"score": float(score), "reasons": []}
        tags = [
            "vanik-netra",
            "market-intelligence",
            _text(place.get("primary_category")).lower(),
        ]
        if not place.get("website"):
            tags.append("no-website")
        return {
            "company": place["name"],
            "email": place.get("email") or "",
            "phone": place.get("phone") or "",
            "source": "vanik-netra:" + ",".join(place.get("sources") or ["unknown"]),
            "intent": "Market opportunity: " + (_text(place.get("primary_category")) or "business"),
            "stage": "new",
            "score": max(0.0, min(100.0, float(scored["score"]))),
            "tags": list(dict.fromkeys(x for x in tags if x)),
            "next_action": "Review opportunity before any outreach",
        }

    def import_to_crm(self, row: dict[str, Any], *, score: float | None = None) -> dict[str, Any]:
        if self.crm is None:
            raise RuntimeError("MANIBHADRA CRM is not bound")
        return self.crm.upsert_lead(self.crm_lead_payload(row, score=score))

    def source_status(self) -> dict[str, Any]:
        return self.source_registry.status() if self.source_registry else {
            "zero_spend": True,
            "paid_fallback": False,
            "sources": {},
            "configured": False,
        }

    def scan_area(
        self,
        bbox: dict[str, Any] | list | tuple,
        *,
        area_key: str,
        source: str = "overture",
        category: str | None = None,
        limit: int = 1000,
        min_confidence: float = 0.0,
        persist: bool = True,
        local_path: str | None = None,
    ) -> dict[str, Any]:
        if not self.source_registry:
            raise RuntimeError("VANIK-NETRA source registry is not bound")
        box = BoundingBox.from_value(bbox)
        source = str(source or "overture").strip().lower()
        if source == "overture":
            raw = self.source_registry.overture.scan(
                box, category=category, limit=limit, min_confidence=min_confidence,
            )
        elif source == "foursquare_os":
            if not local_path:
                raise ValueError("Foursquare OS requires an owner-connected/local export path")
            raw = self.source_registry.foursquare.load_local(local_path, limit=limit)
        elif source == "openstreetmap_extract":
            if not local_path:
                raise ValueError("OpenStreetMap extract scan requires a local GeoJSON path")
            raw = self.source_registry.osm.load_geojson(local_path, limit=limit)
        else:
            raise ValueError("unsupported market source")

        normalized = []
        for row in raw:
            try:
                item = self.normalize_place(row)
            except (ValueError, TypeError):
                continue
            lat, lon = item.get("latitude"), item.get("longitude")
            if lat is not None and lon is not None:
                if not (box.west <= float(lon) <= box.east and box.south <= float(lat) <= box.north):
                    continue
            if category and category.lower() not in _text(item.get("primary_category")).lower():
                continue
            normalized.append(item)
        records = self.deduplicate(normalized)
        report = self.analyze_area(records)
        snapshot = None
        if persist and self.store:
            snapshot = self.store.save_snapshot(
                area_key, records, source=source, bbox=box.as_dict(), category=category,
            )
        return {
            "agent": self.NAME,
            "area_key": str(area_key),
            "source": source,
            "bbox": box.as_dict(),
            "category": category,
            "record_count": len(records),
            "summary": {k: v for k, v in report.items() if k != "records"},
            "snapshot": snapshot,
            "records": records,
            "zero_spend": True,
            "external_outreach": False,
        }

    def stored_area(
        self,
        bbox: dict[str, Any],
        *,
        category: str | None = None,
        limit: int = 2000,
    ) -> dict[str, Any]:
        if not self.store:
            raise RuntimeError("VANIK-NETRA market store is not bound")
        records = self.store.query_bbox(bbox, category=category, limit=limit)
        report = self.analyze_area(records)
        return {
            "bbox": BoundingBox.from_value(bbox).as_dict(),
            "category": category,
            "summary": {k: v for k, v in report.items() if k != "records"},
            "records": report["records"],
        }

    def change_report(self, area_key: str, *, limit: int = 200) -> dict[str, Any]:
        if not self.store:
            raise RuntimeError("VANIK-NETRA market store is not bound")
        return {
            "area_key": str(area_key),
            "latest_snapshot": self.store.latest_snapshot(str(area_key)),
            "changes": self.store.changes(str(area_key), limit=limit),
        }

    @staticmethod
    def map_payload(records: list[dict[str, Any]], *, limit: int = 1000) -> dict[str, Any]:
        points = []
        for row in records or []:
            lat = _float(row.get("latitude"))
            lon = _float(row.get("longitude"))
            if lat is None or lon is None:
                continue
            points.append({
                "business_id": row.get("business_id"),
                "name": row.get("name"),
                "category": row.get("primary_category"),
                "lat": lat,
                "lon": lon,
                "phone": row.get("phone"),
                "website": row.get("website"),
                "address": row.get("address"),
                "map_url": row.get("google_maps_navigation_url"),
            })
            if len(points) >= max(1, min(int(limit), 5000)):
                break
        if not points:
            return {"points": [], "bounds": None}
        lats = [x["lat"] for x in points]
        lons = [x["lon"] for x in points]
        return {
            "points": points,
            "bounds": {
                "west": min(lons), "south": min(lats),
                "east": max(lons), "north": max(lats),
            },
        }

    def status(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "role": self.ROLE,
            "zero_spend": True,
            "paid_sources_enabled": False,
            "external_outreach_enabled": False,
            "external_writes_enabled": False,
            "google_maps_bulk_scraping": False,
            "public_nominatim_bulk_grid": False,
            "crm_handoff": self.crm is not None,
            "market_store": self.store.capabilities() if self.store else {"configured": False},
            "source_registry": self.source_status(),
            "sources": self.SOURCE_POLICY,
            "capabilities": [
                "area market analysis",
                "place normalization",
                "multi-source deduplication",
                "category mix",
                "contactability analysis",
                "digital-gap discovery",
                "opportunity scoring",
                "Google Maps navigation-link generation",
                "MANIBHADRA CRM lead handoff",
            ],
        }
