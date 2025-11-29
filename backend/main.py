import json
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from openai import OpenAI, AsyncOpenAI

from dotenv import load_dotenv

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch


# Initialize OpenAI clients
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # sync client (not really used now)
async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    timestamp: str | None = None


class DeviceRequest(BaseModel):
    name: str


class ChatRequest(BaseModel):
    message: str


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "devices": [],
            "history": [],
            "devices_data": [],
            "chat_history": [],
            "current_problem": None,
        }
        save_data(initial_data)
        return initial_data

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # Ensure default keys exist even for old files
    if "devices" not in data:
        data["devices"] = []
    if "history" not in data:
        data["history"] = []
    if "devices_data" not in data:
        data["devices_data"] = []
    if "chat_history" not in data:
        data["chat_history"] = []
    if "current_problem" not in data:
        data["current_problem"] = None

    # Backfill timestamps in history
    if "history" in data:
        updated = False
        for item in data["history"]:
            if "timestamp" not in item:
                item["timestamp"] = datetime.utcnow().isoformat() + "Z"
                updated = True
        if updated:
            save_data(data)

    return data


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_recent_sensor_data(
    devices_data: List[Dict[str, Any]], hours: int = 12
) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent: List[Dict[str, Any]] = []

    for item in devices_data:
        ts = item.get("timestamp")
        if not ts:
            recent.append(item)
            continue

        try:
            parsed = datetime.fromisoformat(ts)
        except Exception:
            recent.append(item)
            continue

        if parsed >= cutoff:
            recent.append(item)

    return recent


async def ask_chat_gpt_for_advice(history, current_complaint, devices_data):
    recent_sensors = get_recent_sensor_data(devices_data, hours=12)

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "The data can be incomplete, noisy, or low quality. "
        "Regardless of data quality, you must always provide some brief, "
        "practical, common-sense advice. "
        "You are NOT a doctor and this is NOT medical advice."
    )

    # Use only last few history entries to avoid huge context
    trimmed_history = history[-5:]

    user_payload = {
        "full_history_last_5": trimmed_history,
        "current_complaint": current_complaint,
        "recent_sensor_data_last_12h": recent_sensors,
    }

    user_message = (
        "You are being used in a health-monitoring app.\n\n"
        "Here is the context as JSON. Use it to infer what might be going on and give a short, "
        "simple explanation plus a few general tips.\n\n"
        f"```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "Constraints:\n"
        "- Always respond, even if data looks bad, weird, or incomplete.\n"
        "- Make it clear in a brief way that your answer is not a diagnosis or professional medical advice.\n"
        "- Keep your answer to 1–2 short paragraphs (around 120–180 words)."
    )

    completion = await async_client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )

    return completion.choices[0].message.content.strip()


async def ask_chat_gpt_for_overall_summary(
    devices,
    history,
    devices_data,
    chat_history,
    current_problem,
) -> str:
    """
    Ask ChatGPT to create a single overall summary paragraph using the most relevant data.
    Returns a plain string.
    """

    history_for_model = history[-5:]           # last 5 symptoms
    devices_data_for_model = devices_data[-5:] # last 5 sensor records
    chat_history_for_model = chat_history[-6:] # last 6 chat messages

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "You summarize the patient's situation for a doctor and for the patient. "
        "You are NOT a doctor and this is NOT medical advice. "
        "You must include a brief sentence making it clear that this summary does not replace professional medical care."
    )

    payload = {
        "current_problem": current_problem,
        "devices": devices,
        "recent_history": history_for_model,
        "recent_devices_data": devices_data_for_model,
        "recent_chat_history": chat_history_for_model,
    }

    user_message = (
        "You will receive JSON with the most relevant data about a person's symptoms,\n"
        "connected devices, recent sensor readings, and their recent chat with an AI assistant.\n\n"
        "Your task:\n"
        "- Read the data and write ONE overall summary paragraph (or two short paragraphs) that a doctor could quickly scan.\n"
        "- Briefly describe: the main complaint, how it evolved over time, any notable sensor patterns, "
        "and anything important from the conversation.\n"
        "- Use clear, simple language.\n"
        "- Include exactly one short sentence that clearly says this is not a diagnosis or medical advice and cannot replace a healthcare professional.\n"
        "- Aim for about 150–220 words.\n\n"
        "Respond with plain text only (no JSON, no bullet points, no markdown).\n\n"
        "Here is the data as JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    completion = await async_client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )

    return completion.choices[0].message.content.strip()


def parse_iso_datetime(ts: str) -> str:
    """Convert ISO timestamp to a nicer human-readable format."""
    if not ts:
        return "Unknown time"
    try:
        # strip trailing Z if present
        if ts.endswith("Z"):
            ts = ts[:-1]
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def build_devices_section(devices, styles):
    story = []
    story.append(Paragraph("Devices", styles["Heading2"]))
    if not devices:
        story.append(Paragraph("No devices registered.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story

    for d in devices:
        story.append(Paragraph(f"• {d}", styles["BodyText"]))
    story.append(Spacer(1, 10))
    return story


def build_history_section(history, styles, max_items: int | None = None):
    story = []
    story.append(Paragraph("Symptom History", styles["Heading2"]))
    if not history:
        story.append(Paragraph("No symptom history recorded yet.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story

    items = history
    if max_items is not None:
        items = history[-max_items:]

    for item in items:
        timestamp = parse_iso_datetime(item.get("timestamp"))
        body_part = item.get("bodyPart", "Unknown area")
        message = item.get("message", "")
        story.append(Paragraph(f"<b>{timestamp}</b> – {body_part}", styles["BodyText"]))
        story.append(Paragraph(message, styles["BodyText"]))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    return story


def build_sensor_section(devices_data, styles, max_items: int | None = None):
    story = []
    story.append(Paragraph("Sensor Data (Recent Records)", styles["Heading2"]))
    if not devices_data:
        story.append(Paragraph("No sensor data available.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story

    data = [["Time", "Source", "Data Summary"]]

    items = devices_data
    if max_items is not None:
        items = devices_data[-max_items:]

    for item in items:
        timestamp = parse_iso_datetime(item.get("timestamp"))
        source = item.get("device") or item.get("source") or "-"
        summary_parts = []
        for k, v in item.items():
            if k in ("timestamp", "device", "source"):
                continue
            summary_parts.append(f"{k}: {v}")
        summary = ", ".join(summary_parts) if summary_parts else "-"

        data.append([timestamp, str(source), summary])

    table = Table(data, colWidths=[1.6 * inch, 1.4 * inch, 3.4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 10))
    return story


def build_chat_section(chat_history, styles, max_items: int | None = None):
    story = []
    story.append(Paragraph("Chat Summary (Recent Messages)", styles["Heading2"]))
    if not chat_history:
        story.append(
            Paragraph(
                "No chat conversation recorded for this problem.", styles["BodyText"]
            )
        )
        story.append(Spacer(1, 10))
        return story

    items = chat_history
    if max_items is not None:
        items = chat_history[-max_items:]

    for msg in items:
        role = msg.get("role", "user")
        role_label = "User" if role == "user" else "Assistant"
        timestamp = parse_iso_datetime(msg.get("timestamp"))
        text = msg.get("message", "")

        story.append(
            Paragraph(f"<b>{role_label}</b> ({timestamp})", styles["BodyText"])
        )
        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    return story


async def ask_chat_gpt_for_chat(current_problem, chat_history, user_message: str) -> str:
    """
    current_problem: last history item (initial complaint) or None
    chat_history: list of {"role": "...", "message": "...", "timestamp": "..."}
    user_message: latest user message
    """
    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "You are chatting with the user about their initial complaint and follow-up questions. "
        "The data can be incomplete, noisy, or low quality. "
        "Regardless of data quality, you must always provide some brief, "
        "practical, common-sense advice. "
        "You are NOT a doctor and this is NOT medical advice."
    )

    # Use only last few chat messages for context
    trimmed_chat = chat_history[-6:]

    payload = {
        "initial_problem_from_history": current_problem,
        "recent_chat_history": trimmed_chat,
        "latest_user_message": user_message,
    }

    user_content = (
        "Continue the conversation with the user based on this JSON context.\n\n"
        "The JSON contains the user's initial problem (from /history), "
        "a short recent chat history, and the latest user message.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "Your task:\n"
        "- Answer the latest user message.\n"
        "- Keep the tone simple and friendly.\n"
        "- Give 1–2 short paragraphs of explanation and a few practical tips.\n"
        "- Clearly say this is NOT real medical advice.\n"
        "- Keep your reply under ~160 words."
    )

    completion = await async_client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )

    return completion.choices[0].message.content.strip()


@app.post("/history")
async def create_history(item: HistoryItem):
    data = load_data()

    timestamp = item.timestamp or datetime.utcnow().isoformat() + "Z"

    new_item = {
        "message": item.message,
        "bodyPart": item.bodyPart,
        "timestamp": timestamp,
    }
    data["history"].append(new_item)

    if "devices_data" not in data:
        data["devices_data"] = []

    # New history item = new “episode” → reset chat
    data["current_problem"] = new_item
    data["chat_history"] = []

    save_data(data)

    try:
        advice = await ask_chat_gpt_for_advice(
            history=data["history"],
            current_complaint=new_item,
            devices_data=data.get("devices_data", []),
        )
    except Exception as e:
        advice = (
            "System notice: AI call failed, so here is a fallback message.\n"
            f"Internal error: {e}"
        )

    return {
        "history_item": new_item,
        "advice": advice,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Uses:
    - data['current_problem']: last /history record (initial complaint)
    - data['chat_history']: full conversation history for this complaint

    Each time /history is called, chat_history is cleared and current_problem is updated.
    """
    data = load_data()

    current_problem = data.get("current_problem")
    if not current_problem and data.get("history"):
        current_problem = data["history"][-1]
        data["current_problem"] = current_problem

    if "chat_history" not in data:
        data["chat_history"] = []

    user_entry = {
        "role": "user",
        "message": req.message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    data["chat_history"].append(user_entry)

    try:
        reply = await ask_chat_gpt_for_chat(
            current_problem=current_problem,
            chat_history=data["chat_history"],
            user_message=req.message,
        )
    except Exception as e:
        reply = (
            "System notice: AI call failed, so here is a fallback message.\n"
            f"Internal error: {e}"
        )

    assistant_entry = {
        "role": "assistant",
        "message": reply,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    data["chat_history"].append(assistant_entry)

    save_data(data)

    return {
        "current_problem": current_problem,
        "reply": reply,
        "chat_history": data["chat_history"],
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


@app.get("/doctor_report")
async def generate_doctor_report():
    data = load_data()

    devices = data.get("devices", [])
    history = data.get("history", [])
    devices_data = data.get("devices_data", [])
    chat_history = data.get("chat_history", [])
    current_problem = data.get("current_problem")

    # Only the overall summary is generated by ChatGPT
    try:
        overall_summary = await ask_chat_gpt_for_overall_summary(
            devices=devices,
            history=history,
            devices_data=devices_data,
            chat_history=chat_history,
            current_problem=current_problem,
        )
    except Exception as e:
        overall_summary = (
            f"Automated summary could not be generated (internal error: {e})."
        )

    filename = "doctor_report.pdf"
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    if "SmallGrey" not in styles:
        styles.add(
            ParagraphStyle(
                name="SmallGrey",
                parent=styles["BodyText"],
                fontSize=8,
                textColor=colors.grey,
            )
        )

    story = []

    # Header
    story.append(Paragraph("Patient Report", styles["Title"]))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Automatically generated summary from the health-monitoring application.",
            styles["SmallGrey"],
        )
    )
    story.append(Spacer(1, 16))

    # Overall summary (the only part from ChatGPT)
    story.append(Paragraph("Overall Summary", styles["Heading1"]))
    story.append(Paragraph(overall_summary, styles["BodyText"]))
    story.append(Spacer(1, 16))

    # Current problem snapshot (raw data)
    story.append(Paragraph("Current Problem Snapshot", styles["Heading2"]))
    if current_problem:
        ts = parse_iso_datetime(current_problem.get("timestamp"))
        body_part = current_problem.get("bodyPart", "Unknown area")
        msg = current_problem.get("message", "")
        story.append(Paragraph(f"<b>Reported at:</b> {ts}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Body area:</b> {body_part}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Description:</b> {msg}", styles["BodyText"]))
    else:
        story.append(
            Paragraph(
                "No current problem has been selected yet.", styles["BodyText"]
            )
        )
    story.append(Spacer(1, 16))

    # Divider
    hr = Table([[""]], colWidths=[7.2 * inch], rowHeights=[0.4])
    hr.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.grey)]))
    story.append(hr)
    story.append(Spacer(1, 16))

    # Symptom history (last few entries)
    story.extend(build_history_section(history, styles, max_items=3))
    story.append(Spacer(1, 8))

    # Devices section (raw list)
    story.extend(build_devices_section(devices, styles))
    story.append(Spacer(1, 8))

    # Sensor data (recent table)
    story.extend(build_sensor_section(devices_data, styles, max_items=5))

    # Chat messages (last few)
    story.append(Spacer(1, 16))
    story.extend(build_chat_section(chat_history, styles, max_items=6))

    # Footer notice
    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "Note: This report is generated by an automated system and is not a substitute for professional medical evaluation or diagnosis.",
            styles["SmallGrey"],
        )
    )

    doc.build(story)

    return FileResponse(
        os.path.join(os.getcwd(), filename),
        media_type="application/pdf",
        filename=filename,
    )


# Run with:
# uvicorn main:app --reload
