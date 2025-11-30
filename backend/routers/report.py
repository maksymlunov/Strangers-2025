# app/routers/report.py
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

from storage import load_data
from pdf_report import build_doctor_report_pdf

router = APIRouter(tags=["report"])

@router.get("/doctor_report")
async def generate_doctor_report():
    data = load_data()
    pdf_path = await build_doctor_report_pdf(data)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="doctor_report.pdf",
    )
