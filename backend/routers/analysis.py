# app/routers/analysis.py
from fastapi import APIRouter

from storage import load_data, _parse_iso_to_datetime
from ai import ask_chat_gpt_for_analysis

router = APIRouter(tags=["analysis"])

@router.get("/analize")
async def analize():
    data = load_data()

    devices = data.get("devices", [])
    history = data.get("history", [])
    devices_data = data.get("devices_data", [])
    chat_history = data.get("chat_history", [])
    current_problem = data.get("current_problem")

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

        cleaned = []
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
            risk_int = max(0, min(10, risk_int))
            cleaned.append({"disease": disease, "risk": risk_int})

        if not cleaned:
            cleaned = [{"disease": "Analysis unavailable or unclear", "risk": 0}]
    except Exception:
        cleaned = [{"disease": "Analysis failed", "risk": 0}]

    return cleaned[:5]
