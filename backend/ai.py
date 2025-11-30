# app/ai.py
import json
from typing import Any, Dict, List
from datetime import datetime

from config import async_client
from storage import get_recent_sensor_data

async def ask_chat_gpt_for_advice(history, current_complaint, devices_data):
    recent_sensors = get_recent_sensor_data(devices_data, hours=12)

    system_prompt = (
        "You are a helpful assistant in a health-monitoring app. "
        "The data can be incomplete, noisy, or low quality. "
        "Regardless of data quality, you must always provide some brief, "
        "practical, common-sense advice. "
        "You are NOT a doctor and this is NOT medical advice."
    )

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
    history_for_model = history[:5]
    devices_data_for_model = devices_data[:5]
    chat_history_for_model = chat_history[:6]

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

    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("Analysis output is not a list")

    return parsed
