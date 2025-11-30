# Health Monitoring API – FastAPI + GPT Integration

This project is a backend service for a health monitoring application.
It collects symptoms, wearable device data, and user messages, and enhances the experience using GPT models to generate contextual advice, summaries, and automated health risk insights.

The system is **not** a medical diagnostics tool.
All AI outputs are explicitly non-medical and for informational use only.

## 🚀 Features

### Symptom Tracking
- Users submit symptoms via `/history`.
- The system stores each symptom entry along with:
  - affected body part  
  - timestamp  
  - AI-generated initial advice

### Wearable Device Data
Supports 4 common devices:
- Smartwatch  
- Fitness Band  
- Blood Pressure Monitor  
- Smart Scale  

Each device contains multiple time-stamped “sessions” holding metrics like heart rate, steps, active minutes, blood pressure, weight, and more.

### AI Chat
A contextual, short-form chat that:
- Resets when a new symptom is created  
- Uses recent messages + current problem + sensor info  
- Provides practical, non-medical responses

### Doctor-Friendly PDF Report
Endpoint `/doctor_report` generates a structured PDF summarizing:
- AI summary  
- recent symptoms  
- embedded advice  
- device data tables  
- recent chat snippets  
- disclaimers  

### AI Disease Risk Analysis
The `/analize` endpoint returns:
```json
[
  { "disease": "migraine", "risk": 4 },
  { "disease": "stress-related symptoms", "risk": 3 }
]
```
The model outputs 1–5 possible non-diagnostic condition categories with risk 0–10.

## 📁 Project Structure
```
.
├── main.py
├── data.json
├── doctor_report.pdf
├── requirements.txt
└── README.md
```

## ⚙️ Setup

### 1. Virtual environment
```
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Add your OpenAI key
Create `.env`:
```
OPENAI_API_KEY=your-key-here
```

### 4. Run the server
```
uvicorn main:app --reload
```

## 📡 API Endpoints
- **POST /history** – add new symptom + AI advice  
- **GET /history_all** – full symptom history  
- **POST /chat** – continue conversation  
- **GET /chat_history** – initial complaint + messages  
- **POST /devices** – register device  
- **GET /devices** – list devices  
- **GET /devices_data** – all sensor data  
- **GET /doctor_report** – PDF summary  
- **GET /analize** – AI risk output  

## 🧠 AI Model Requirements
Models must:
- always respond  
- include disclaimers  
- avoid medical diagnoses  
- follow strict JSON formatting when required  
- handle incomplete data  

## 🗃️ Data Examples

### History Item
```json
{
  "message": "Lower back pain when bending",
  "bodyPart": "Back",
  "timestamp": "2025-11-29T11:00:00Z",
  "advice": "Short AI response..."
}
```

### Device Example
```json
{
  "device": "Smartwatch",
  "sessions": [
    {
      "timestamp": "2025-11-29T09:42:11Z",
      "heartRate": 82,
      "steps": 1240,
      "stressLevel": 3
    }
  ]
}
```

## 📄 PDF Report
Generated using reportlab, containing:
- summary  
- symptoms  
- advice  
- devices  
- chat  
- disclaimers  

## 🔮 Future Enhancements
- Real database  
- Authentication  
- Time-series analytics  
- Notifications  
- More device integrations  
