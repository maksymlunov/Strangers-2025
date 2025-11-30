# app/routers/devices.py
from fastapi import APIRouter

from models import DeviceRequest
from storage import load_data, save_data, _parse_iso_to_datetime

router = APIRouter(tags=["devices"])

@router.post("/devices")
def create_device(device: DeviceRequest):
    data = load_data()
    data["devices"].append(device.name)
    save_data(data)
    return data["devices"]

@router.get("/devices")
def get_devices():
    data = load_data()
    return data["devices"]

@router.get("/devices_data")
def get_devices_data():
    data = load_data()
    sorted_devices_data = sorted(
        data.get("devices_data", []),
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )
    return sorted_devices_data
