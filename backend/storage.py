# app/storage.py
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

DATA_FILE = "data.json"

def _parse_iso_to_datetime(ts: str | None) -> datetime:
    if not ts:
        return datetime.min
    try:
        if ts.endswith("Z"):
            ts = ts[:-1]
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.min

def _sort_data_inplace(data: Dict[str, Any]) -> None:
    if "history" in data and isinstance(data["history"], list):
        data["history"].sort(
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )
    if "devices_data" in data and isinstance(data["devices_data"], list):
        data["devices_data"].sort(
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )
    if "chat_history" in data and isinstance(data["chat_history"], list):
        data["chat_history"].sort(
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "devices": [],
            "history": [],
            "devices_data": [],
            "chat_history": [],
            "current_problem": None,
        }
            # we call save_data below, so no recursion problems
        save_data(initial_data)
        return initial_data

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    data.setdefault("devices", [])
    data.setdefault("history", [])
    data.setdefault("devices_data", [])
    data.setdefault("chat_history", [])
    data.setdefault("current_problem", None)

    # backfill timestamps in history
    updated = False
    for item in data["history"]:
        if "timestamp" not in item:
            item["timestamp"] = datetime.utcnow().isoformat() + "Z"
            updated = True
    if updated:
        save_data(data)

    _sort_data_inplace(data)
    return data

def save_data(data: Dict[str, Any]) -> None:
    _sort_data_inplace(data)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_recent_sensor_data(
    devices_data: List[Dict[str, Any]], hours: int = 12
) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent: List[Dict[str, Any]] = []
    for item in devices_data:
        ts = item.get("timestamp")
        parsed = _parse_iso_to_datetime(ts)
        if parsed >= cutoff:
            recent.append(item)

    recent.sort(
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )
    return recent

def parse_iso_datetime(ts: str) -> str:
    dt = _parse_iso_to_datetime(ts)
    if dt == datetime.min:
        return ts or "Unknown time"
    return dt.strftime("%Y-%m-%d %H:%M")
