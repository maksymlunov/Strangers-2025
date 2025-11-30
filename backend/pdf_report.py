# app/pdf_report.py
from typing import Any, Dict, List
from datetime import datetime
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch

from storage import _parse_iso_to_datetime, parse_iso_datetime
from ai import ask_chat_gpt_for_overall_summary

def build_devices_section(devices, styles):
    story = [Paragraph("Devices", styles["Heading2"])]
    if not devices:
        story.append(Paragraph("No devices registered.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story
    for d in devices:
        story.append(Paragraph(f"• {d}", styles["BodyText"]))
    story.append(Spacer(1, 10))
    return story

def build_history_section(history, styles, max_items: int | None = None):
    story = [Paragraph("Symptom History", styles["Heading2"])]
    if not history:
        story.append(Paragraph("No symptom history recorded yet.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story

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
    story = [Paragraph("Sensor Data (Recent Records)", styles["Heading2"])]
    if not devices_data:
        story.append(Paragraph("No sensor data available.", styles["BodyText"]))
        story.append(Spacer(1, 10))
        return story

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
    story = [Paragraph("Chat Summary (Recent Messages)", styles["Heading2"])]
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
        story.append(Paragraph(f"<b>{role_label}</b> ({timestamp})", styles["BodyText"]))
        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 10))
    return story

async def build_doctor_report_pdf(data: Dict[str, Any]) -> str:
    devices = data.get("devices", [])
    history = data.get("history", [])
    devices_data = data.get("devices_data", [])
    chat_history = data.get("chat_history", [])
    current_problem = data.get("current_problem")

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
    story.append(Paragraph("Patient Report", styles["Title"]))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Automatically generated summary from the health-monitoring application.",
            styles["SmallGrey"],
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("Overall Summary", styles["Heading1"]))
    story.append(Paragraph(overall_summary, styles["BodyText"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Current Problem Snapshot", styles["Heading2"]))

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
            Paragraph("No current problem has been selected yet.", styles["BodyText"])
        )
    story.append(Spacer(1, 16))

    # Divider
    hr = Table([[""]], colWidths=[7.2 * inch], rowHeights=[0.4])
    hr.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.grey)]))
    story.append(hr)
    story.append(Spacer(1, 16))

    story.extend(build_history_section(history, styles, max_items=3))
    story.extend(build_devices_section(devices, styles))
    story.extend(build_sensor_section(devices_data, styles, max_items=5))
    story.extend(build_chat_section(chat_history, styles, max_items=6))

    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "Note: This report is generated by an automated system and is not a substitute for professional medical evaluation or diagnosis.",
            styles["SmallGrey"],
        )
    )

    doc.build(story)
    return os.path.abspath(filename)
