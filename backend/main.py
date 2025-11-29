import json
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai import OpenAI

from dotenv import load_dotenv

from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

# Initialize OpenAI client
# Make sure you set the environment variable: OPENAI_API_KEY
# e.g. in your shell: export OPENAI_API_KEY="sk-..."
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_FILE = "Report.pdf"
DATA_FILE = "data.json"


class HistoryItem(BaseModel):
    message: str
    bodyPart: str
    timestamp: str | None = None  # ISO 8601 format, auto-generated if not provided


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
        data = json.load(f)
    
    # Migration: add timestamps to existing history records that don't have them
    if "history" in data:
        for item in data["history"]:
            if "timestamp" not in item:
                item["timestamp"] = datetime.utcnow().isoformat() + "Z"
        # Save the migrated data
        save_data(data)
    
    return data


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_recent_sensor_data(devices_data: List[Dict[str, Any]], hours: int = 12) -> List[Dict[str, Any]]:
    """
    Filter sensor data to only include entries from the last `hours` hours.

    Expects each item to optionally have a "timestamp" field in ISO 8601 format.
    If timestamp is missing or unparsable, we still keep the item so that
    the model always has *some* data to look at (demo-friendly).
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent: List[Dict[str, Any]] = []

    for item in devices_data:
        ts = item.get("timestamp")
        if not ts:
            # No timestamp -> keep it, we want *some* data even if quality is bad.
            recent.append(item)
            continue

        try:
            parsed = datetime.fromisoformat(ts)
        except Exception:
            # Bad timestamp format -> keep anyway for demo purposes.
            recent.append(item)
            continue

        if parsed >= cutoff:
            recent.append(item)

    return recent


def ask_chat_gpt_for_advice(
    history: List[Dict[str, Any]],
    current_complaint: Dict[str, Any],
    devices_data: List[Dict[str, Any]],
) -> str:
    """
    Call ChatGPT with:
    - full previous history
    - current complaint
    - sensor data from last 12 hours

    The prompt explicitly says this is a demo and that it should always
    return *some* advice regardless of data quality.
    """
    recent_sensors = get_recent_sensor_data(devices_data, hours=12)

    system_prompt = (
        "You are a helpful assistant in a DEMO health-monitoring app. "
        "The data can be incomplete, noisy, or low quality. "
        "Regardless of data quality, you must always provide some brief, "
        "practical, common-sense advice. "
        "You are NOT a doctor and this is NOT medical advice."
    )

    user_payload = {
        "demo_note": "This is a DEMO. Data can be incomplete or noisy. Still provide an answer.",
        "full_history": history,
        "current_complaint": current_complaint,
        "recent_sensor_data_last_12h": recent_sensors,
    }

    user_message = (
        "You are being used in a demo app.\n\n"
        "Here is the context as JSON. Use it to infer what might be going on and give a short, "
        "simple explanation plus a few general tips.\n\n"
        f"```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "Constraints:\n"
        "- Always respond, even if data looks bad, weird, or incomplete.\n"
        "- Be very clear that this is JUST A DEMO and NOT real medical advice.\n"
        "- Keep your answer to 1–2 short paragraphs."
    )

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",  # or any other model you prefer
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )

    return completion.choices[0].message.content.strip()


@app.get("/generate_report")
def gen_report():
    data = load_data()

    c = canvas.Canvas(PDF_FILE, pagesize=A4)
    width, height = A4

    # ---------------- HEADER ----------------
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "Health Monitoring Report")

    c.setLineWidth(1.2)
    c.setStrokeColor(colors.darkgray)
    c.line(40, height - 60, width - 40, height - 60)

    y = height - 90

    # ---------------- DEVICE INFO ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Device Information:")
    y -= 20

    device_field = data.get("device", "ShoulderFlexPro")

    if isinstance(device_field, dict):
        device_name = device_field.get("name", "ShoulderFlexPro")
    else:
        device_name = device_field
    c.setFont("Helvetica", 11)
    c.drawString(70, y, f"Device name: {device_name}")
    y -= 25

        # ---------------- ТУТ ВИВЕСТИ ІНФО ЩО НАДАВ ПРИЙСТРІЙ ----------------

    for session in data.get("sessions", []):
        ts = session.get("timestamp", "")

        try:
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
        except:
            date_str, time_str = ts, ""

        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"Date: {date_str}  Time: {time_str}")
        y -= 15
        c.drawString(90, y, f"Alignment score: {session.get('alignmentScore', 'N/A')}")
        y -= 15
        c.drawString(90, y, f"Pressure points: {session.get('pressurePoints', 'N/A')}")
        y -= 25

    # ---------------- HISTORY TITLE ----------------
    if y < 120:
        c.showPage()
        y = height - 80

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Patient History")
    y -= 30

    c.setFont("Helvetica", 12)

    # ---------------- TEXT WRAP FUNCTION ----------------
    def draw_wrapped_text(c, text, x, y, max_width):
        words = text.split(" ")
        line = ""
        for word in words:
            if c.stringWidth(line + word, "Helvetica", 12) < max_width:
                line += word + " "
            else:
                c.drawString(x, y, line)
                y -= 14
                line = word + " "
        if line:
            c.drawString(x, y, line)
            y -= 14
        return y

    # ---------------- HISTORY CONTENT ----------------
    for hist in data.get("history", []):
        raw_ts = hist.get("timestamp", "")

        try:
            dt = datetime.fromisoformat(raw_ts.replace("Z", ""))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
        except:
            date_str, time_str = raw_ts, ""

        entry_lines = [
            f"Date: {date_str}",
            f"Time: {time_str}",
            f"Message: {hist.get('message', '')}",
            f"Body part: {hist.get('bodyPart', '')}",
        ]

        if y < 120:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - 50

        for line in entry_lines:
            y = draw_wrapped_text(c, line, 50, y, width - 100)
            y -= 5

        y -= 15

    # ---------------- SAVE PDF ----------------
    c.save()
    return FileResponse(PDF_FILE, media_type="application/pdf", filename="report.pdf")

@app.post("/history")
def create_history(item: HistoryItem):
    data = load_data()

    # Auto-generate timestamp if not provided
    timestamp = item.timestamp or datetime.utcnow().isoformat() + "Z"
    
    new_item = {"message": item.message, "bodyPart": item.bodyPart, "timestamp": timestamp}
    data["history"].append(new_item)

    # Ensure devices_data key exists
    if "devices_data" not in data:
        data["devices_data"] = []

    save_data(data)

    # Call ChatGPT for advice based on all history + current item + last 12h sensors
    try:
        advice = ask_chat_gpt_for_advice(
            history=data["history"],
            current_complaint=new_item,
            devices_data=data.get("devices_data", []),
        )
    except Exception as e:
        # Fallback so the endpoint still returns something in demo mode
        advice = (
            "Demo notice: ChatGPT call failed, so here is a fallback message.\n"
            f"Internal error: {e}"
        )

    # Return both the stored history item and the AI advice
    return {
        "history_item": new_item,
        "advice": advice,
    }


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


# Run with:
# uvicorn main:app --reload
