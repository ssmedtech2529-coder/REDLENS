"""
Red Lens — AI-Based Non-Invasive Anemia Screening System
FastAPI Backend Application Entrypoint
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_agent
import chatbot
import database

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Red Lens AI — Non-Invasive Anemia Screening Backend",
    description="Biomedical analysis, optical sensor validation, and clinical AI support agent.",
    version="2.0.0"
)

# Configure CORS dynamically based on environment and local development hosts
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    frontend_origin.rstrip("/")
]
# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Data Models ---

class ChatMessage(BaseModel):
    role: str = Field(description="Role: user or assistant")
    content: str = Field(max_length=1500, description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500, description="User question")
    history: List[ChatMessage] = []
    language: str = Field(default="en", description="Language code: en or ta")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Screening record data")


class AnalysisRequest(BaseModel):
    eyeAnalysis: Optional[Dict[str, Any]] = None
    nailAnalysis: Optional[Dict[str, Any]] = None
    hemoglobinSensor: Optional[Dict[str, Any]] = None
    vitals: Optional[Dict[str, Any]] = None
    patient: Optional[Dict[str, Any]] = None


class SensorReadingRequest(BaseModel):
    value: float = Field(ge=2.0, le=25.0, description="Hemoglobin value in g/dL")
    unit: str = Field(default="g/dL")
    source: str = Field(default="serial", description="Source: serial, manual, demo, sim")
    reads: Optional[List[float]] = None
    vitals: Optional[Dict[str, Any]] = None


# --- Health & Diagnostic Routes ---

@app.get("/api/health")
def health():
    """Verify backend health, database connectivity, and AI service configuration."""
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    has_key = has_openai or has_gemini
    ai_mode = "ai" if has_key else "demo"

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if has_key else "clinical_rules_engine"

    # Quick DB check
    db_ok = True
    try:
        stats = database.get_stats()
    except Exception:
        db_ok = False
        stats = {}

    return {
        "status": "ok",
        "service": "Red Lens Anemia Screening API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "ai_mode": ai_mode,
        "ai_provider_configured": has_key,
        "active_model": model_name,
        "database_connected": db_ok,
        "stats": stats
    }


# --- Biomedical Analysis Routes ---

@app.post("/api/analyze")
def analyze_screening(payload: Dict[str, Any]):
    """
    Evaluate multi-modal screening parameters (eye pallor, nail pallor, sensor readings, vitals).
    Performs cross-modal validation, checks measurement tolerance, and flags discrepancies.
    """
    try:
        result = ai_agent.analyze(payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Analysis processing error: {str(e)}"
        )


@app.post("/api/agent")
def run_agent(ctx: Dict[str, Any]):
    """Deterministic rule-based agent analysis (backward compatibility)."""
    return ai_agent.analyze(ctx)


@app.post("/api/sensor/reading")
def submit_sensor_reading(reading: SensorReadingRequest):
    """Validate and log a sensor reading from microcontroller/Web Serial."""
    status_label = "valid"
    notes = []

    if reading.value < 7.0:
        notes.append("Severe range indication")
    elif reading.value < 11.0:
        notes.append("Mild-to-moderate range indication")
    else:
        notes.append("Normal screening range indication")

    return {
        "status": status_label,
        "value": reading.value,
        "unit": reading.unit,
        "source": reading.source,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    }


# --- Interactive AI Chatbot Route ---

@app.post("/api/chat")
async def chat(body: ChatRequest):
    """
    Secure AI assistant endpoint.
    Sanitizes context, enforces biomedical safety boundaries, and returns plain-English guidance.
    """
    # Generate ground-truth clinical analysis if context was provided
    agent_summary = ai_agent.analyze(body.context) if body.context else None
    history = [m.model_dump() for m in body.history]

    try:
        reply = await chatbot.llm_reply(body.message, history, body.language, agent_summary)
        mode = "ai"
    except LookupError:
        # No API key configured -> clearly labeled DEMO mode
        reply = chatbot.build_demo_reply(body.message, body.language, agent_summary)
        mode = "demo"
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"error": "The AI service timed out. Please check your network connection and retry."}
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"error": "Authentication failed with AI provider. Please verify your OPENAI_API_KEY in backend/.env."}
            )
        elif e.response.status_code == 429:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "AI rate limit reached. Please wait a moment before sending another message."}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"error": f"AI provider returned an error (HTTP {e.response.status_code}). Please retry later."}
            )
    except httpx.HTTPError:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "Cannot reach the external AI service. Please verify your internet connection."}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )

    return {
        "reply": reply,
        "mode": mode,
        "agent": agent_summary,
        "timestamp": datetime.now().isoformat()
    }


# --- Database & History Routes ---

@app.get("/api/history")
def get_history(
    q: Optional[str] = Query(None, description="Search by ID, name, or location"),
    filter_result: Optional[str] = Query(None, description="Filter by combined result category"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Retrieve screening history records from the persistent SQLite database."""
    try:
        records = database.get_screenings(query=q, filter_result=filter_result, limit=limit, offset=offset)
        return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error: {str(e)}"
        )


@app.post("/api/history")
def save_history(record: Dict[str, Any]):
    """Save or update a screening record in the persistent SQLite database."""
    try:
        res = database.save_screening(record)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save screening record: {str(e)}"
        )


@app.get("/api/history/{record_id}")
def get_single_record(record_id: str):
    """Fetch a single screening record by ID."""
    rec = database.get_screening_by_id(record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return rec


@app.delete("/api/history/{record_id}")
def delete_single_record(record_id: str):
    """Delete a screening record by ID."""
    success = database.delete_screening(record_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found or already deleted")
    return {"status": "deleted", "id": record_id}


# --- Static Frontend Serving ---

FRONT_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONT_DIR.exists():
    # Specific route for root "/" to serve redlens.html (or index.html)
    @app.get("/")
    def serve_root():
        index_file = FRONT_DIR / "index.html"
        redlens_file = FRONT_DIR / "redlens.html"
        if index_file.exists():
            return FileResponse(index_file)
        if redlens_file.exists():
            return FileResponse(redlens_file)
        return JSONResponse({"status": "frontend files not found"}, status_code=404)

    # Mount remaining static assets (CSS, JS, images)
    app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="frontend")
