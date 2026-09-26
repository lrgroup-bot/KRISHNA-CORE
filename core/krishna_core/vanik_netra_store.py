from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(row: dict[str, Any]) -> str:
    keys = (
        "name", "brand", "primary_category", "phone", "email", "website",
        "address", "locality", "city", "district", "state", "postcode",
        "country", "latitude", "longitude", "operating_status",
    )
    body = {key: row.get(key) for key in keys}
    return hashlib.sha256(_json(body).encode("utf-8")).hexdigest()


class VanikNetraStore:
    """Local market store with snapshot/change history and optional H3 indexing."""

    def __init__(self, path: str | Path, h3_resolution: int = 9):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.h3_resolution = max(0, min(int(h3_resolution), 15))
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self._connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS places(
                    business_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    address TEXT,
                    latitude REAL,
                    longitude REAL,
                    h3_cell TEXT,
                    sources_json TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshots(
                    snapshot_id TEXT PRIMARY KEY,
                    area_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source TEXT,
                    bbox_json TEXT,
                    category TEXT,
                    record_count INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_area_time
                    ON snapshots(area_key, created_at DESC);
                CREATE TABLE IF NOT EXISTS snapshot_members(
                    snapshot_id TEXT NOT NULL,
                    business_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    PRIMARY KEY(snapshot_id,business_id)
                );
                CREATE TABLE IF NOT EXISTS changes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area_key TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    business_id TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_changes_area_time
                    ON changes(area_key, created_at DESC);
                """
            )

    def _h3(self, lat: Any, lon: Any) -> str:
        if lat is None or lon is None:
            return ""
        try:
            import h3  # type: ignore
            return str(h3.latlng_to_cell(float(lat), float(lon), self.h3_resolution))
        except Exception:
            return ""

    def capabilities(self) -> dict[str, Any]:
        try:
            import h3  # type: ignore
            available = hasattr(h3, "latlng_to_cell")
        except Exception:
            available = False
        return {
            "backend": "sqlite",
            "path": str(self.path),
            "h3_available": available,
            "h3_resolution": self.h3_resolution,
            "zero_spend": True,
        }

    def latest_snapshot(self, area_key: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM snapshots WHERE area_key=? ORDER BY created_at DESC LIMIT 1",
                (str(area_key),),
            ).fetchone()
        return dict(row) if row else None

    def _members(self, snapshot_id: str | None) -> dict[str, str]:
        if not snapshot_id:
            return {}
        with self._connect() as con:
            rows = con.execute(
                "SELECT business_id,fingerprint FROM snapshot_members WHERE snapshot_id=?",
                (snapshot_id,),
            ).fetchall()
        return {row["business_id"]: row["fingerprint"] for row in rows}

    def save_snapshot(
        self,
        area_key: str,
        records: list[dict[str, Any]],
        *,
        source: str = "",
        bbox: dict[str, Any] | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        area_key = str(area_key or "").strip()
        if not area_key:
            raise ValueError("area_key is required")
        previous = self.latest_snapshot(area_key)
        previous_members = self._members(previous["snapshot_id"] if previous else None)
        snapshot_id = "scan-" + uuid.uuid4().hex[:16]
        now = _now()
        current: dict[str, str] = {}
        normalized: list[tuple[dict[str, Any], str]] = []
        for row in records or []:
            business_id = str(row.get("business_id") or "").strip()
            if not business_id:
                continue
            fp = _fingerprint(row)
            current[business_id] = fp
            normalized.append((row, fp))

        added = [bid for bid in current if bid not in previous_members]
        changed = [bid for bid, fp in current.items() if bid in previous_members and previous_members[bid] != fp]
        removed = [bid for bid in previous_members if bid not in current]
        by_id = {str(row.get("business_id")): row for row, _ in normalized}

        with self._connect() as con:
            con.execute(
                "INSERT INTO snapshots(snapshot_id,area_key,created_at,source,bbox_json,category,record_count) VALUES(?,?,?,?,?,?,?)",
                (snapshot_id, area_key, now, source, _json(bbox or {}), category or "", len(current)),
            )
            for row, fp in normalized:
                bid = str(row["business_id"])
                con.execute(
                    """
                    INSERT INTO places(
                        business_id,name,category,phone,email,website,address,latitude,longitude,h3_cell,
                        sources_json,record_json,fingerprint,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(business_id) DO UPDATE SET
                        name=excluded.name,category=excluded.category,phone=excluded.phone,
                        email=excluded.email,website=excluded.website,address=excluded.address,
                        latitude=excluded.latitude,longitude=excluded.longitude,h3_cell=excluded.h3_cell,
                        sources_json=excluded.sources_json,record_json=excluded.record_json,
                        fingerprint=excluded.fingerprint,updated_at=excluded.updated_at
                    """,
                    (
                        bid, row.get("name") or "", row.get("primary_category") or "",
                        row.get("phone") or "", row.get("email") or "", row.get("website") or "",
                        row.get("address") or "", row.get("latitude"), row.get("longitude"),
                        self._h3(row.get("latitude"), row.get("longitude")),
                        _json(row.get("sources") or []), _json(row), fp, now,
                    ),
                )
                con.execute(
                    "INSERT INTO snapshot_members(snapshot_id,business_id,fingerprint) VALUES(?,?,?)",
                    (snapshot_id, bid, fp),
                )
            for change_type, ids in (("added", added), ("changed", changed), ("removed", removed)):
                for bid in ids:
                    con.execute(
                        "INSERT INTO changes(area_key,snapshot_id,business_id,change_type,created_at,record_json) VALUES(?,?,?,?,?,?)",
                        (area_key, snapshot_id, bid, change_type, now, _json(by_id.get(bid) or {})),
                    )
        return {
            "snapshot_id": snapshot_id,
            "area_key": area_key,
            "record_count": len(current),
            "previous_snapshot_id": previous["snapshot_id"] if previous else None,
            "changes": {"added": len(added), "changed": len(changed), "removed": len(removed)},
            "created_at": now,
        }

    def changes(self, area_key: str, limit: int = 200) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM changes WHERE area_key=? ORDER BY id DESC LIMIT ?",
                (str(area_key), limit),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["record"] = json.loads(item.pop("record_json") or "{}")
            except Exception:
                item["record"] = {}
            out.append(item)
        return out

    def query_bbox(
        self,
        bbox: dict[str, Any],
        *,
        category: str | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        west, south, east, north = (
            float(bbox["west"]), float(bbox["south"]),
            float(bbox["east"]), float(bbox["north"]),
        )
        limit = max(1, min(int(limit), 10000))
        sql = """
            SELECT record_json FROM places
            WHERE longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ?
        """
        params: list[Any] = [west, east, south, north]
        if category:
            sql += " AND lower(category) LIKE ?"
            params.append("%" + str(category).strip().lower() + "%")
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()
        out = []
        for row in rows:
            try:
                out.append(json.loads(row["record_json"]))
            except Exception:
                continue
        return out
