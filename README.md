# Red Lens — AI-Based Non-Invasive Anemia Screening System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com/)
[![OpenCV.js](https://img.shields.io/badge/Computer%20Vision-OpenCV.js-5C3EE8)](https://docs.opencv.org/)
[![License: Research Prototype](https://img.shields.io/badge/Status-Research%20Prototype-orange)](#clinical-safety-and-biomedical-disclaimer)

A full-stack, multimodal biomedical screening system integrating non-invasive optical conjunctival & fingernail colorimetric analysis (OpenCV), optical sensor readings (e.g. MAX30102 / ESP32 via USB Web Serial), persistent SQLite screening history, and a conversational clinical support AI agent.

---

## 1. Architecture Overview

```
                          ┌────────────────────────────────────────────────────────┐
                          │                   Frontend (SPA)                       │
                          │   • redlens.html / index.html                          │
                          │   • OpenCV.js (RGB, HSV, CIE Lab a* extraction)        │
                          │   • Web Serial (ESP32 / MAX30102 Sensor)               │
                          │   • redlens-ai.js (Interactive Medical Chatbot)        │
                          │   • api.js (Centralized Reusable REST Client)          │
                          └───────────┬────────────────────────────────┬───────────┘
                                      │                                │
                       REST APIs / JSON (port 8000)        localStorage Fallback
                                      │                                │
                          ┌───────────▼────────────────────────────────▼───────────┐
                          │             FastAPI Backend (backend/main.py)          │
                          │   • GET  /api/health (Diagnostics & AI config)         │
                          │   • POST /api/analyze (Multi-modal consistency)        │
                          │   • POST /api/agent (Deterministic rules engine)       │
                          │   • POST /api/chat (Conversational Clinical AI)        │
                          │   • GET/POST/DELETE /api/history (SQLite DB)           │
                          │   • POST /api/sensor/reading (Optical PPG)             │
                          └───────────┬────────────────────────────────┬───────────┘
                                      │                                │
                      ┌───────────────▼──────────────┐   ┌─────────────▼──────────────┐
                      │    SQLite Database (DB)      │   │ External AI Provider       │
                      │    backend/redlens.db        │   │ (OpenAI / Gemini / Groq)   │
                      │    Screenings Table          │   │ Env: OPENAI_API_KEY        │
                      └──────────────────────────────┘   └────────────────────────────┘
```

---

## 2. Directory Structure

```
RedLens-AI/
├── .env.example              <- Root environment variable reference
├── .gitignore                <- Protects .env, *.db, and virtual environments
├── README.md                 <- Architecture, setup, API & testing guide
├── backend/
│   ├── .env                  <- Local active environment variables (Ignored in Git)
│   ├── .env.example          <- Backend-specific environment template
│   ├── ai_agent.py           <- Deterministic biomedical rules & multimodal correlation
│   ├── chatbot.py            <- LLM client + clinical knowledge base fallback
│   ├── database.py           <- SQLite persistent database CRUD layer
│   ├── main.py               <- FastAPI server, CORS, REST routes & static mount
│   ├── redlens.db            <- SQLite database file (auto-created on startup)
│   └── requirements.txt      <- Backend Python dependencies
└── frontend/
    ├── api.js                <- Centralized reusable frontend REST API client
    ├── index.html            <- Root router (auto-redirects to redlens.html)
    ├── redlens-ai.js         <- Interactive AI Assistant & Chatbot UI
    └── redlens.html          <- Main medical screening SPA (Dashboard, Scan, Sensor, Result, History)
```

---

## 3. Technology Stack

- **Frontend**: Vanilla HTML5, CSS3, ES6+ JavaScript, OpenCV.js, Web Serial API.
- **Backend**: Python 3.10+, FastAPI, Uvicorn (ASGI server), Pydantic v2 (Validation), HTTPX (Async HTTP).
- **Database**: SQLite3 with auto-indexing on `patient_id`, `date_time`, and `combined_result`.
- **AI Agent**: OpenAI API (GPT-4o-mini / GPT-4o) or Google Gemini via OpenAI-compatible endpoint, with an offline rule-based clinical engine fallback.

---

## 4. Setup & Running in VS Code

### Step 1: Open VS Code Terminal
Open your project root (`c:\Users\sankar\Desktop\RedLens-AI`) in VS Code.

### Step 2: Set Up Backend Virtual Environment
```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Windows Command Prompt:
.venv\Scripts\activate.bat
# On macOS/Linux:
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# On Windows Command Prompt:
copy .env.example .env
# On Windows PowerShell:
cp .env.example .env
```
Open `backend/.env` in VS Code and insert your API key:
```env
PORT=8000
HOST=127.0.0.1
FRONTEND_URL=http://localhost:3000
DATABASE_PATH=redlens.db

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```
*(If no API key is provided, the application runs automatically in DEMO mode with full rule-based clinical intelligence).*

### Step 5: Start the Backend Server
```bash
uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

### Step 6: Launch the Frontend
Open your browser and navigate to:
```
http://localhost:8000/
```
*(The server automatically serves the frontend application, checks backend health, and connects the API service).*

---

## 5. REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status, active AI model, and database metrics. |
| `POST` | `/api/analyze` | Multi-modal screening correlation (eye, nail, sensor, vitals). |
| `POST` | `/api/agent` | Deterministic rule-based evaluation (data validation & plausibility). |
| `POST` | `/api/chat` | AI Chatbot with sanitized screening context and biomedical guardrails. |
| `GET` | `/api/history` | Retrieve saved screening records from SQLite (`?q=...&filter_result=...`). |
| `POST` | `/api/history` | Save a new screening record to SQLite. |
| `GET` | `/api/history/{id}` | Retrieve a specific screening record. |
| `DELETE` | `/api/history/{id}` | Delete a screening record. |
| `POST` | `/api/sensor/reading` | Validate and record raw optical sensor reading from ESP32. |

---

## 6. Example API Requests

### 1. Multi-Modal Analysis (`POST /api/analyze`)
```json
{
  "eyeAnalysis": {
    "status": "available",
    "pallorScore": 45.0
  },
  "nailAnalysis": {
    "status": "available",
    "pallorScore": 48.0
  },
  "hemoglobinSensor": {
    "value": 10.4,
    "unit": "g/dL",
    "source": "serial"
  },
  "vitals": {
    "hr": 82,
    "spo2": 98.0
  },
  "patient": {
    "age": 28,
    "gender": "Female",
    "preg": false
  }
}
```

### 2. AI Chatbot Query (`POST /api/chat`)
```json
{
  "message": "What does my screening report mean and why do the readings differ?",
  "history": [],
  "language": "en",
  "context": {
    "hb": 10.4,
    "hbSrc": "serial",
    "nail": "Possible Anaemia",
    "eye": "Normal Screening Range"
  }
}
```

---

## 7. Troubleshooting

1. **"Backend offline" pill in header**:
   - Ensure Uvicorn is running: `uvicorn main:app --reload --port 8000`
   - Check firewall permissions for `localhost:8000`.
2. **"DEMO mode" indicated in AI status**:
   - `OPENAI_API_KEY` is not set or empty in `backend/.env`.
   - Add your key to `backend/.env` and restart Uvicorn.
3. **HTTP 502 / 401 Bad Gateway on Chat**:
   - Invalid or expired OpenAI API key.
   - Quota limit exceeded on OpenAI account.
4. **Sensor Two-Reading Check Retest Alert**:
   - Two consecutive readings must agree within `0.2 g/dL`. If readings fluctuate beyond this, the system mandates a retest to prevent erroneous estimations.

---

## 8. Clinical Safety and Biomedical Disclaimer

> [!WARNING]
> **Research Prototype Only — Not a Confirmed Medical Diagnosis**:
> 1. Photoplethysmography sensors (e.g. MAX30102) measure optical absorption variations (red and infrared) and are **not** clinically validated for direct hemoglobin determination.
> 2. Conjunctival and nail-bed colorimetric pallor analysis can be distorted by ambient lux, color temperature, camera white balance, nail varnish, or cold-induced peripheral vasoconstriction.
> 3. Values in this application are clearly classified as `MEASURED` (laboratory blood reference), `ESTIMATED` (colorimetric model), `UNVERIFIED_SENSOR` (optical PPG), `MANUAL`, or `SIMULATED`.
> 4. **Always confirm any screening indication with a certified venous blood Complete Blood Count (CBC) and consultation with a qualified medical professional.**
