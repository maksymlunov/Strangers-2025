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
    # Advice from the assistant stored directly with the history item
    advice: str | None = None


class DeviceRequest(BaseModel):
    name: str


class ChatMessage(BaseModel):
    role: str
    message: str
    timestamp: str
    bodyPart: str | None = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]


def _parse_iso_to_datetime(ts: str | None) -> datetime:
    """Internal helper: robust ISO timestamp -> datetime (invalid = very old)."""
    if not ts:
        return datetime.min
    try:
        if ts.endswith("Z"):
            ts = ts[:-1]
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.min


def _sort_data_inplace(data: Dict[str, Any]) -> None:
    """Sort history, devices_data, chat_history by timestamp (most recent first)."""
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

    # Ensure sorted (most recent first)
    _sort_data_inplace(data)

    return data


def save_data(data: Dict[str, Any]) -> None:
    # Always sort before saving so file is chronological (newest first)
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

    # Ensure most recent first
    recent.sort(
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )

    return recent


async def ask_chat_gpt_for_advice(history, current_complaint, devices_data):
    # history is stored newest-first; keep that
    recent_sensors = get_recent_sensor_data(devices_data, hours=12)

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "The data can be incomplete, noisy, or low quality. "
        "Regardless of data quality, you must always provide some brief, "
        "practical, common-sense advice. "
        "You are NOT a doctor and this is NOT medical advice."
    )

    # Take the 5 most recent history items
    trimmed_history = history[:5]

    user_payload = {
        "full_history_most_recent_5": trimmed_history,
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

    # All lists are stored newest-first; slice from the front
    history_for_model = history[:5]            # 5 most recent symptoms
    devices_data_for_model = devices_data[:5]  # 5 most recent sensor records
    chat_history_for_model = chat_history[:6]  # 6 most recent chat messages

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "You summarize the patient's situation for a doctor and for the patient. "
        "You are NOT a doctor and this is NOT medical advice. "
        "You must include a brief sentence making it clear that this summary does not replace professional medical care."
    )

    payload = {
        "current_problem": current_problem,
        "devices": devices,
        "recent_history_most_recent_first": history_for_model,
        "recent_devices_data_most_recent_first": devices_data_for_model,
        "recent_chat_history_most_recent_first": chat_history_for_model,
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


async def ask_chat_gpt_for_analysis(
    devices,
    history,
    devices_data,
    chat_history,
    current_problem,
) -> List[Dict[str, Any]]:
    """
    Ask ChatGPT to analyze all available data and return 1–5
    possible 'disease' labels with integer risk 0–10.

    This is explicitly NOT a diagnosis, just a rough risk tagging.
    """
    # Use most recent slices to keep prompt size under control
    history_for_model = history[:8]
    devices_data_for_model = devices_data[:40]
    chat_history_for_model = chat_history[:10]

    system_prompt = (
        "You are an assistant in a health-monitoring app. "
        "You are NOT a doctor and this is NOT medical advice or diagnosis. "
        "Your job is only to generate rough, high-level risk tags for possible conditions, "
        "based on symptoms, sensors, and chat history. "
        "Your output will be displayed with a clear warning that it is not medical advice."
    )

    payload = {
        "current_problem": current_problem,
        "devices": devices,
        "history_most_recent_first": history_for_model,
        "devices_data_most_recent_first": devices_data_for_model,
        "chat_history_most_recent_first": chat_history_for_model,
    }

    user_message = (
        "You will receive JSON with symptom history, current problem, connected devices, "
        "sensor data, and chat history from a health-monitoring app.\n\n"
        "Your task:\n"
        "- Infer up to 5 POSSIBLE conditions or problem categories (these are NOT diagnoses).\n"
        "- For each, assign an integer risk score from 0 to 10 (0 = no apparent risk, 10 = very concerning). "
        "Use 0–3 for low risk, 4–6 for moderate, 7–10 for high concern.\n"
        "- Focus on broad, human-readable labels like 'migraine', 'anxiety-related symptoms', "
        "'mild dehydration', 'cardiovascular issue', etc. Avoid very rare or hyper-specific diseases.\n"
        "- If data is very unclear, include one item like 'Unclear cause' with a low risk (1–3).\n\n"
        "FORMAT REQUIREMENTS (VERY IMPORTANT):\n"
        "- Respond with ONLY a JSON array.\n"
        "- Length must be between 1 and 5.\n"
        "- Each element must be an object with EXACTLY these keys: \"disease\" (string) and \"risk\" (integer 0–10).\n"
        "- Do NOT include any extra keys, comments, text, or explanations outside the JSON.\n\n"
        "Example of valid output:\n"
        "[\n"
        "  {\"disease\": \"migraine\", \"risk\": 4},\n"
        "  {\"disease\": \"tension headache\", \"risk\": 6}\n"
        "]\n\n"
        "Here is the data as JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    completion = await async_client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    raw = completion.choices[0].message.content.strip()

    # Try to parse robustly; if it fails, we will handle in caller
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("Analysis output is not a list")
    except Exception:
        # Bubble up as error; caller will create fallback
        raise ValueError(f"Model returned invalid JSON: {raw!r}")

    return parsed


def parse_iso_datetime(ts: str) -> str:
    """Convert ISO timestamp to a nicer human-readable format."""
    dt = _parse_iso_to_datetime(ts)
    if dt == datetime.min:
        return ts or "Unknown time"
    return dt.strftime("%Y-%m-%d %H:%M")


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

    # Ensure newest-first order when rendering
    sorted_items = sorted(
        history,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )

    if max_items is not None:
        sorted_items = sorted_items[:max_items]

    for item in sorted_items:
        timestamp = parse_iso_datetime(item.get("timestamp"))
        body_part = item.get("bodyPart", "Unknown area")
        message = item.get("message", "")
        advice = item.get("advice")

        story.append(Paragraph(f"<b>{timestamp}</b> – {body_part}", styles["BodyText"]))
        story.append(Paragraph(message, styles["BodyText"]))
        if advice:
            story.append(
                Paragraph(
                    f"<i>App advice at that time:</i> {advice}",
                    styles["BodyText"],
                )
            )
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

    # Sort newest-first for display
    sorted_items = sorted(
        devices_data,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )

    if max_items is not None:
        sorted_items = sorted_items[:max_items]

    data = [["Time", "Source", "Data Summary"]]

    for item in sorted_items:
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

    sorted_items = sorted(
        chat_history,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )

    if max_items is not None:
        sorted_items = sorted_items[:max_items]

    for msg in sorted_items:
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

    # Ensure newest-first, then take the most recent 6
    sorted_chat = sorted(
        chat_history,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )
    trimmed_chat = sorted_chat[:6]

    payload = {
        "initial_problem_from_history": current_problem,
        "recent_chat_history_most_recent_first": trimmed_chat,
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


@app.get("/history_all")
def get_all_history():
    """
    Return full symptom history sorted from newest to oldest.
    Format stays exactly as stored: { message, bodyPart, timestamp, advice? }.
    """
    data = load_data()

    history = data.get("history", [])

    sorted_history = sorted(
        history,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,   # newest → oldest
    )

    return sorted_history


@app.post("/history")
async def create_history(item: HistoryItem):
    data = load_data()

    timestamp = item.timestamp or datetime.utcnow().isoformat() + "Z"

    # New history item starts without advice; we add it after the model replies
    new_item: Dict[str, Any] = {
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

    # Store advice directly into the history item so history + advice live together
    new_item["advice"] = advice

    chats_ans = {
        "role": "assistant",
        "message": advice,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    data["chat_history"].append(chats_ans)
    save_data(data)
    return {
        "history_item": new_item,
        "advice": advice,
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Новый логика:
    - НЕ сохраняем chat_history
    - Фронт присылает полный массив сообщений
    - Берём последнее user сообщение
    - Достаём user message + bodyPart
    - GPT генерирует advice
    - Создаём history item и сохраняем в файл
    - Возвращаем массив сообщений + новое assistant сообщение
    """

    messages = req.messages

    # Находим последнее user-сообщение
    last_user_msg = None
    for m in reversed(messages):
        if m.role == "user":
            last_user_msg = m
            break

    if not last_user_msg:
        return {
            "messages": messages,
            "error": "No user message found"
        }

    # GPT контекст
    payload = {
        "chat_history": [m.dict() for m in messages],
        "latest_user_message": last_user_msg.message,
        "bodyPart": last_user_msg.bodyPart,
    }

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "You chat with the user about their symptoms. "
        "Always give simple, practical advice. "
        "You are NOT a doctor. This is NOT medical advice."
    )

    user_content = (
        "Continue the conversation based on this JSON:\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Your task:\n"
        "- Respond to the latest user message.\n"
        "- Keep tone warm and simple.\n"
        "- Give brief, practical tips.\n"
        "- Clearly say this is NOT medical advice.\n"
        "- Reply only with raw assistant text."
    )

    try:
        completion = await async_client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
        )
        advice_text = completion.choices[0].message.content.strip()

    except Exception as e:
        advice_text = (
            "System notice: AI call failed.\n"
            f"Error: {e}"
        )

    # Сохраняем в history
    data = load_data()

    history_item = {
        "message": last_user_msg.message,
        "bodyPart": last_user_msg.bodyPart,
        "timestamp": last_user_msg.timestamp or datetime.utcnow().isoformat() + "Z",
        "advice": advice_text,
    }

    data["history"].append(history_item)
    save_data(data)

    # Формируем ассистент-сообщение для ответа
    assistant_message = ChatMessage(
        role="assistant",
        message=advice_text,
        timestamp=datetime.utcnow().isoformat() + "Z",
        bodyPart=None
    )

    return {
        "messages": messages + [assistant_message],
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
    # Always return sensor data newest-first
    sorted_devices_data = sorted(
        data.get("devices_data", []),
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )
    return sorted_devices_data


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

    # Make sure we treat the most recent history item as current if missing
    if not current_problem and history:
        current_problem = sorted(
            history,
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )[0]

    if current_problem:
        ts = parse_iso_datetime(current_problem.get("timestamp"))
        body_part = current_problem.get("bodyPart", "Unknown area")
        msg = current_problem.get("message", "")
        story.append(Paragraph(f"<b>Reported at:</b> {ts}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Body area:</b> {body_part}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Description:</b> {msg}", styles["BodyText"]))
        if current_problem.get("advice"):
            story.append(
                Paragraph(
                    f"<b>Initial app advice:</b> {current_problem.get('advice')}",
                    styles["BodyText"],
                )
            )
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

    # Symptom history (last few entries, newest-first)
    story.extend(build_history_section(history, styles, max_items=3))
    story.append(Spacer(1, 8))

    # Devices section (raw list)
    story.extend(build_devices_section(devices, styles))
    story.append(Spacer(1, 8))

    # Sensor data (recent table, newest-first)
    story.extend(build_sensor_section(devices_data, styles, max_items=5))

    # Chat messages (last few, newest-first)
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


@app.get("/chat_history")
def get_chat_history():
    """
    Return combined current problem + chat_history
    in the same format as chat_history (role, message, timestamp),
    sorted from latest to newest.
    """
    data = load_data()

    entries: List[Dict[str, Any]] = []

    current_problem = data.get("current_problem")
    history = data.get("history", [])
    chat_history = data.get("chat_history", [])

    # If current_problem is missing, fall back to most recent history item
    if not current_problem and history:
        current_problem = sorted(
            history,
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )[0]

    if current_problem:
        entries.append(
            {
                "role": "user",
                "message": f"[Initial complaint] {current_problem.get('message', '')}",
                "timestamp": current_problem.get("timestamp"),
            }
        )

    # Add all chat_history entries as-is
    entries.extend(chat_history)

    # Sort combined list oldest-first
    entries.sort(
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=False,
    )

    return entries


@app.get("/analize")
async def analize():
    """
    Analyze all available data (history, sensors, chat, devices) and return
    1–5 objects of the form { "disease": str, "risk": int(0–10) }.

    This is NOT a diagnosis. It is a rough, automated risk tagging.
    """
    data = load_data()

    devices = data.get("devices", [])
    history = data.get("history", [])
    devices_data = data.get("devices_data", [])
    chat_history = data.get("chat_history", [])
    current_problem = data.get("current_problem")

    # If current_problem is missing, use most recent history item, if any
    if not current_problem and history:
        current_problem = sorted(
            history,
            key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
            reverse=True,
        )[0]

    try:
        raw_list = await ask_chat_gpt_for_analysis(
            devices=devices,
            history=history,
            devices_data=devices_data,
            chat_history=chat_history,
            current_problem=current_problem,
        )

        cleaned: List[Dict[str, Any]] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            disease = item.get("disease")
            if not disease:
                continue
            disease = str(disease)

            risk = item.get("risk", 0)
            try:
                risk_int = int(risk)
            except Exception:
                risk_int = 0
            # Clamp to 0–10
            if risk_int < 0:
                risk_int = 0
            if risk_int > 10:
                risk_int = 10

            cleaned.append({"disease": disease, "risk": risk_int})

        # Ensure we always return at least one item
        if not cleaned:
            cleaned = [
                {
                    "disease": "Analysis unavailable or unclear",
                    "risk": 0,
                }
            ]

    except Exception as e:
        # Fallback on any failure
        cleaned = [
            {
                "disease": "Analysis failed",
                "risk": 0,
            }
        ]

    # Return between 1 and 5 items (truncate if model gave more)
    return cleaned[:5]


# Run with:
# uvicorn main:app --reload
