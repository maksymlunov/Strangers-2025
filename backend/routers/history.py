# app/routers/history.py
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter

from models import HistoryItem, ChatMessage
from storage import load_data, save_data, _parse_iso_to_datetime
from ai import ask_chat_gpt_for_advice

router = APIRouter(prefix="", tags=["history"])

@router.get("/history_all")
def get_all_history():
    data = load_data()
    history = data.get("history", [])
    sorted_history = sorted(
        history,
        key=lambda x: _parse_iso_to_datetime(x.get("timestamp")),
        reverse=True,
    )
    return sorted_history

@router.post("/history")
async def create_history(item: HistoryItem):
    data = load_data()

    timestamp = item.timestamp or datetime.utcnow().isoformat() + "Z"
    new_item: Dict[str, Any] = {
        "message": item.message,
        "bodyPart": item.bodyPart,
        "timestamp": timestamp,
    }
    data["history"].append(new_item)
    data.setdefault("devices_data", [])

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
