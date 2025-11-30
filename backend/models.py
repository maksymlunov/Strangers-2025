# app/models.py
from typing import List, Optional
from pydantic import BaseModel

class HistoryItem(BaseModel):
    message: str
    bodyPart: str
    timestamp: Optional[str] = None
    advice: Optional[str] = None

class DeviceRequest(BaseModel):
    name: str

class ChatMessage(BaseModel):
    role: str
    message: str
    timestamp: str
    bodyPart: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
