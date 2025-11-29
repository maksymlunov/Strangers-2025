import json
import os
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data.json"

class HistoryItem(BaseModel):
    message: str
    bodyPart: str

class DeviceRequest(BaseModel):
    name: str

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "devices": [],
            "history": [],
            "devices_data": []
        }
        save_data(initial_data)
        return initial_data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.post("/history")
def create_history(item: HistoryItem):
    data = load_data()
    new_item = {"message": item.message, "bodyPart": item.bodyPart}
    data["history"].append(new_item)
    save_data(data)
    return new_item

@app.post("/devices")
def create_device(device: DeviceRequest):
    data = load_data()
    data["devices"].append(device.name)
    save_data(data)
    return data["devices"]

@app.get("/devices")
def get_devices():
    data = load_data()
    return data["devices"]

@app.get("/devices_data")
def get_devices_data():
    data = load_data()
    return data["devices_data"]

# uvicorn main:app --reload
