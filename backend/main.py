# app/main.py
from config import create_app
from routers import history, chat, devices, analysis, report

app = create_app()

app.include_router(history.router)
app.include_router(chat.router)
app.include_router(devices.router)
app.include_router(analysis.router)
app.include_router(report.router)

# Run with:
# uvicorn app.main:app --reload
