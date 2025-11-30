# app/routers/chat.py
from datetime import datetime
import json

from fastapi import APIRouter

from models import ChatRequest, ChatMessage
from storage import load_data, save_data, _parse_iso_to_datetime

from config import async_client

router = APIRouter(tags=["chat"])

@router.post("/chat")
async def chat(req: ChatRequest):
    messages = req.messages

    last_user_msg = None
    for m in reversed(messages):
        if m.role == "user":
            last_user_msg = m
            break

    if not last_user_msg:
        return {"messages": messages, "error": "No user message found"}

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
        advice_text = f"System notice: AI call failed.\nError: {e}"

    data = load_data()
    history_item = {
        "message": last_user_msg.message,
        "bodyPart": last_user_msg.bodyPart,
        "timestamp": last_user_msg.timestamp or datetime.utcnow().isoformat() + "Z",
        "advice": advice_text,
    }
    data["history"].append(history_item)
    save_data(data)

    assistant_message = ChatMessage(
        role="assistant",
        message=advice_text,
        timestamp=datetime.utcnow().isoformat() + "Z",
        bodyPart=None,
    )

    return {"messages": messages + [assistant_message]}

@router.get("/chat_history")
def get_chat_history():
    data = load_data()

    entries = []
    current_problem = data.get("current_problem")
    history = data.get("history", [])
    chat_history = data.get("chat_history", [])

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

    entries.extend(chat_history)

    entries.sort(
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=False,
    )

    return entries
