"""
Database manager for Red Lens Anemia Screening System.
Uses SQLite for zero-dependency, reliable, persistent local storage.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_FILE = os.getenv("DATABASE_PATH", str(Path(__file__).parent / "redlens.db"))


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables and indexes if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenings (
                id TEXT PRIMARY KEY,
                patient_id TEXT,
                patient_name TEXT,
                age REAL,
                gender TEXT,
                pregnancy INTEGER DEFAULT 0,
                village TEXT,
                screening_centre TEXT,
                operator TEXT,
                date_time TEXT,
                hb_value REAL,
                hb_source TEXT,
                hct_value REAL,
                image_result TEXT,
                combined_result TEXT,
                pallor_score REAL,
                screening_confidence TEXT,
                risk_level TEXT,
                probability REAL,
                quality TEXT,
                status TEXT,
                is_simulated INTEGER DEFAULT 0,
                record_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_pid ON screenings(patient_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_dt ON screenings(date_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_comb ON screenings(combined_result)")
        conn.commit()


def save_screening(record: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a screening record in SQLite."""
    record_id = record.get("rid") or record.get("id") or f"AS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    patient_id = record.get("id") or record.get("patient_id") or "–"
    patient_name = record.get("name") or record.get("patient_name") or "–"
    age = record.get("age")
    gender = record.get("gender") or "–"
    preg = 1 if record.get("preg") or record.get("pregnancy") else 0
    village = record.get("village", "")
    centre = record.get("centre", "")
    operator = record.get("by", "")
    dt = record.get("dt") or record.get("date_time") or datetime.now().isoformat()
    hb = record.get("hb")
    hb_src = record.get("hbSrc") or record.get("hb_source")
    hct = record.get("hct")
    img_res = record.get("img") or record.get("image_result") or "–"
    comb_res = record.get("combined") or record.get("combined_result") or "Needs Further Testing"
    pallor = record.get("pallor")
    conf = record.get("conf") or record.get("confidence") or "Moderate"

    prob_data = record.get("prob") or {}
    prob_val = prob_data.get("prob") if isinstance(prob_data, dict) else None
    risk_info = prob_data.get("risk", {}) if isinstance(prob_data, dict) else {}
    risk_name = risk_info.get("name") if isinstance(risk_info, dict) else None

    quality = record.get("quality") or "–"
    status = record.get("status") or "SCREENING — NOT A DIAGNOSIS"
    is_sim = 1 if record.get("sim") or hb_src in ("demo", "sim") else 0

    record_json_str = json.dumps(record)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO screenings (
                id, patient_id, patient_name, age, gender, pregnancy, village,
                screening_centre, operator, date_time, hb_value, hb_source, hct_value,
                image_result, combined_result, pallor_score, screening_confidence,
                risk_level, probability, quality, status, is_simulated, record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                patient_id = excluded.patient_id,
                patient_name = excluded.patient_name,
                age = excluded.age,
                gender = excluded.gender,
                pregnancy = excluded.pregnancy,
                village = excluded.village,
                screening_centre = excluded.screening_centre,
                operator = excluded.operator,
                date_time = excluded.date_time,
                hb_value = excluded.hb_value,
                hb_source = excluded.hb_source,
                hct_value = excluded.hct_value,
                image_result = excluded.image_result,
                combined_result = excluded.combined_result,
                pallor_score = excluded.pallor_score,
                screening_confidence = excluded.screening_confidence,
                risk_level = excluded.risk_level,
                probability = excluded.probability,
                quality = excluded.quality,
                status = excluded.status,
                is_simulated = excluded.is_simulated,
                record_json = excluded.record_json
        """, (
            record_id, patient_id, patient_name, age, gender, preg, village,
            centre, operator, dt, hb, hb_src, hct,
            img_res, comb_res, pallor, conf,
            risk_name, prob_val, quality, status, is_sim, record_json_str
        ))
        conn.commit()

    return {"status": "saved", "id": record_id}


def get_screenings(
    query: Optional[str] = None,
    filter_result: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve screenings with optional search query and category filtering."""
    sql = "SELECT record_json FROM screenings WHERE 1=1"
    params: List[Any] = []

    if query:
        q = f"%{query.strip().lower()}%"
        sql += " AND (LOWER(patient_id) LIKE ? OR LOWER(patient_name) LIKE ? OR LOWER(village) LIKE ?)"
        params.extend([q, q, q])

    if filter_result:
        sql += " AND combined_result LIKE ?"
        params.append(f"{filter_result.strip()}%")

    sql += " ORDER BY date_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    results = []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        for row in rows:
            try:
                rec = json.loads(row["record_json"])
                results.append(rec)
            except Exception:
                pass
    return results


def get_screening_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve single screening record by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT record_json FROM screenings WHERE id = ? OR patient_id = ?", (record_id, record_id))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["record_json"])
            except Exception:
                return None
    return None


def delete_screening(record_id: str) -> bool:
    """Delete a screening record by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM screenings WHERE id = ? OR patient_id = ?", (record_id, record_id))
        conn.commit()
        return cursor.rowcount > 0


def get_stats() -> Dict[str, Any]:
    """Compute aggregate counts for dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM screenings")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS c FROM screenings WHERE combined_result LIKE 'Normal%'")
        normal = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM screenings WHERE combined_result LIKE 'Possible%'")
        possible = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM screenings WHERE combined_result LIKE 'Needs%'")
        needs = cursor.fetchone()["c"]

        return {
            "total": total,
            "normal": normal,
            "possible": possible,
            "needs_testing": needs
        }


# Auto-initialize DB on import
init_db()
