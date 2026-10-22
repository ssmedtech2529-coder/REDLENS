"""
Red Lens AI Agent — Biomedical Analysis & Screening Support Engine.
Performs deterministic, rule-based clinical validation and multi-modal correlation.
Never hallucinates or fabricates patient measurements.
"""

from typing import Any, Dict, List, Optional
import math

# PII keys that must be stripped before any processing or LLM usage
IDENTIFIER_KEYS = {
    "pid", "patientid", "name", "pname", "phone", "pph", "village", "pvil",
    "location", "centre", "center", "pcen", "operator", "by", "pby", "address",
    "id", "email", "contact"
}

# Prototype pallor calibration thresholds
HB_AT_PALLOR0 = 15.5
HB_AT_PALLOR100 = 6.0
HB_TOLERANCE = 0.2


def sanitize(obj: Any, depth: int = 0) -> Any:
    """Recursively remove identifier keys, base64 images and oversized strings."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        return {
            k: sanitize(v, depth + 1)
            for k, v in obj.items()
            if str(k).lower() not in IDENTIFIER_KEYS
        }
    if isinstance(obj, list):
        return [sanitize(v, depth + 1) for v in obj[:30]]
    if isinstance(obj, str):
        return None if obj.startswith("data:") or len(obj) > 300 else obj
    return obj


def num(v: Any) -> Optional[float]:
    """Safely convert numeric values."""
    try:
        if v is None:
            return None
        val = float(v)
        return val if not (math.isnan(val) or math.isinf(val)) else None
    except (TypeError, ValueError):
        return None


def find(d: Any, names: List[str]) -> Any:
    """Find the first matching key (case-insensitive) in nested dicts or lists."""
    if isinstance(d, dict):
        low = {str(k).lower(): v for k, v in d.items()}
        for n in names:
            if n in low and low[n] not in (None, ""):
                return low[n]
        for v in d.values():
            r = find(v, names)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = find(v, names)
            if r is not None:
                return r
    return None


def get_who_cutoffs(age: Optional[float], gender: Optional[str], preg: bool = False) -> List[float]:
    """
    WHO hemoglobin thresholds (g/dL) for anemia classification:
    Returns [Mild_cut, Moderate_cut, Severe_cut]
    """
    if age is not None:
        if age < 5:
            return [11.0, 10.0, 7.0]
        if age < 12:
            return [11.5, 11.0, 8.0]
        if age < 15:
            return [12.0, 11.0, 8.0]

    g = str(gender).lower() if gender else ""
    if "fem" in g or g == "f":
        return [11.0, 10.0, 7.0] if preg else [12.0, 11.0, 8.0]
    return [13.0, 11.0, 8.0]


def hb_from_pallor(pallor: float) -> float:
    """Convert a 0-100 pallor score to estimated hemoglobin (g/dL)."""
    p = max(0.0, min(100.0, pallor))
    est = HB_AT_PALLOR0 - ((HB_AT_PALLOR0 - HB_AT_PALLOR100) * p / 100.0)
    return round(max(5.0, min(16.0, est)), 1)


def classify_source(src: Optional[str]) -> str:
    """Classify the data source with clinical traceability."""
    if not src:
        return "UNAVAILABLE"
    s = str(src).lower()
    if s in ("demo", "sim", "simulated", "hardware_sim"):
        return "SIMULATED"
    if s in ("manual", "user_entry"):
        return "MANUAL"
    if s in ("serial", "sensor", "max30102", "esp32", "usb_serial"):
        return "UNVERIFIED_SENSOR"
    if s in ("lab", "laboratory", "cbc", "reference"):
        return "MEASURED_LAB_REFERENCE"
    return "ESTIMATED"


def analyze(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a complete, structured, and clinically sound screening evaluation
    built strictly from supplied screening parameters.
    """
    ctx = sanitize(ctx or {})

    # Extract patient context
    age = num(find(ctx, ["age", "page"]))
    gender = find(ctx, ["gender", "pgen", "sex"])
    preg = bool(find(ctx, ["preg", "ppreg", "pregnancy"]))

    # Extract eye and nail analyses (handles both flat and nested API structures)
    eye_obj = ctx.get("eyeAnalysis") or ctx.get("eye") or {}
    nail_obj = ctx.get("nailAnalysis") or ctx.get("nail") or {}

    # Extract pallor scores
    eye_pallor = num(find(eye_obj, ["pallorscore", "pallor", "score"])) if isinstance(eye_obj, dict) else None
    nail_pallor = num(find(nail_obj, ["pallorscore", "pallor", "score"])) if isinstance(nail_obj, dict) else None

    # Fallback to general search if not in specific sub-objects
    if eye_pallor is None:
        eye_pallor = num(find(ctx, ["eye_pallor", "eyepallor"]))
    if nail_pallor is None:
        nail_pallor = num(find(ctx, ["nail_pallor", "nailpallor"]))

    # Check image status/quality
    eye_status = str(find(eye_obj, ["status", "result"]) or ("available" if eye_pallor is not None else "not_scanned")).lower()
    nail_status = str(find(nail_obj, ["status", "result"]) or ("available" if nail_pallor is not None else "not_scanned")).lower()

    # Extract sensor readings
    sensor_obj = ctx.get("hemoglobinSensor") or ctx.get("sensor") or {}
    hb_val = num(find(sensor_obj, ["value", "hb", "hbvalue"])) if isinstance(sensor_obj, dict) else None
    if hb_val is None:
        hb_val = num(find(ctx, ["hb", "hbvalue", "haemoglobin", "hemoglobin"]))

    hb_unit = find(sensor_obj, ["unit"]) or "g/dL"
    hb_src_raw = find(sensor_obj, ["source", "hbsrc", "hbsource"]) or find(ctx, ["hbsource", "hbsrc", "source", "src"])
    hb_source = classify_source(hb_src_raw)

    hb_reads = find(sensor_obj, ["reads", "readings"]) or find(ctx, ["hbreads", "reads"]) or []
    hb_diff = num(find(sensor_obj, ["diff", "hbdiff"])) or num(find(ctx, ["hbdiff", "diff"]))

    # Extract vitals (MAX30102 / manual)
    vitals_obj = ctx.get("vitals") or {}
    pulse = num(find(vitals_obj, ["hr", "pulse", "heartrate"])) if isinstance(vitals_obj, dict) else None
    if pulse is None:
        pulse = num(find(ctx, ["hr", "pulse", "heartrate", "pulserate"]))

    spo2 = num(find(vitals_obj, ["spo2", "spo₂", "saturation"])) if isinstance(vitals_obj, dict) else None
    if spo2 is None:
        spo2 = num(find(ctx, ["spo2", "spo₂"]))

    lab_ref = num(find(ctx, ["labhb", "laboratory_hb", "lab_hb", "ref_hb"]))

    present, missing, warnings, inconsistencies = [], [], [], []

    # 1. Completeness Check
    if hb_val is not None:
        present.append(f"Hemoglobin sensor reading ({hb_val} {hb_unit}, {hb_source})")
    else:
        missing.append("Hemoglobin sensor reading")

    if eye_pallor is not None and "reject" not in eye_status:
        present.append(f"Lower eyelid image analysis (Pallor score: {eye_pallor:.0f}/100)")
    else:
        missing.append("Valid lower eyelid image analysis")

    if nail_pallor is not None and "reject" not in nail_status:
        present.append(f"Nail bed image analysis (Pallor score: {nail_pallor:.0f}/100)")
    else:
        missing.append("Valid nail bed image analysis")

    if pulse is not None:
        present.append(f"Pulse rate ({pulse:.0f} bpm)")
    else:
        missing.append("Pulse rate reading")

    if spo2 is not None:
        present.append(f"Oxygen saturation SpO2 ({spo2:.1f}%)")
    else:
        missing.append("Oxygen saturation reading")

    if lab_ref is not None:
        present.append(f"Laboratory reference Hb ({lab_ref:.1f} g/dL)")

    # 2. Physiological Plausibility & Sensor Quality Check
    if hb_val is not None and not (2.0 <= hb_val <= 25.0):
        warnings.append(f"Reported Hb value ({hb_val} g/dL) is outside the physiological range (2–25 g/dL). Re-test required.")

    if pulse is not None:
        if not (30 <= pulse <= 220):
            warnings.append(f"Pulse rate ({pulse:.0f} bpm) is outside the measurable human range. Likely sensor motion artifact.")
        elif pulse > 100:
            warnings.append(f"Tachycardia detected ({pulse:.0f} bpm). Fast heart rate is a common compensatory symptom in anemia.")

    if spo2 is not None:
        if not (50 <= spo2 <= 100):
            warnings.append(f"SpO2 reading ({spo2:.1f}%) is physiologically improbable. Check sensor placement.")
        elif spo2 < 90:
            warnings.append(f"CRITICAL: Low oxygen saturation (SpO2 {spo2:.1f}%). Requires immediate medical attention.")
        elif spo2 < 94:
            warnings.append(f"Borderline low oxygen saturation ({spo2:.1f}%). Clinical review advised.")

    # 3. Two-Reading Sensor Consistency Check
    sensor_tolerance_ok = True
    if hb_diff is not None:
        if hb_diff > HB_TOLERANCE:
            sensor_tolerance_ok = False
            msg = f"Sensor repeatability check failed: readings differ by {hb_diff:.1f} g/dL (maximum allowed tolerance is {HB_TOLERANCE} g/dL)."
            warnings.append(msg)
            inconsistencies.append(msg)

    # 4. Image Pallor Estimates and Dual-Site Consistency
    eye_est_hb = hb_from_pallor(eye_pallor) if eye_pallor is not None else None
    nail_est_hb = hb_from_pallor(nail_pallor) if nail_pallor is not None else None

    image_disagreement = None
    if eye_est_hb is not None and nail_est_hb is not None:
        img_diff = round(abs(eye_est_hb - nail_est_hb), 1)
        if img_diff > 1.2:
            image_disagreement = (
                f"Image analysis discrepancy: nail-bed pallor suggests ~{nail_est_hb} g/dL whereas "
                f"conjunctiva suggests ~{eye_est_hb} g/dL (difference: {img_diff} g/dL). "
                "Possible causes: uneven illumination, flash glare, peripheral cold, or nail varnish."
            )
            warnings.append(image_disagreement)
            inconsistencies.append(image_disagreement)

    # 5. Sensor vs Image Correlation
    sensor_image_disagreement = None
    mean_img_hb = None
    if eye_est_hb is not None and nail_est_hb is not None:
        mean_img_hb = round((eye_est_hb + nail_est_hb) / 2.0, 1)
    elif eye_est_hb is not None:
        mean_img_hb = eye_est_hb
    elif nail_est_hb is not None:
        mean_img_hb = nail_est_hb

    if hb_val is not None and mean_img_hb is not None:
        delta = round(abs(hb_val - mean_img_hb), 1)
        if delta > 2.0:
            sensor_image_disagreement = (
                f"Cross-modal disagreement: Hemoglobin sensor reading ({hb_val} g/dL) differs by {delta} g/dL "
                f"from image colorimetric estimate (~{mean_img_hb} g/dL). "
                "Neither reading is definitive. Laboratory confirmation is essential."
            )
            warnings.append(sensor_image_disagreement)
            inconsistencies.append(sensor_image_disagreement)

    # 6. WHO Category & Clinical Risk Assessment
    cutoffs = get_who_cutoffs(age, gender, preg)
    primary_hb = hb_val if hb_val is not None else mean_img_hb

    risk_category = "INSUFFICIENT_DATA"
    who_classification = "Indeterminate"
    if primary_hb is not None:
        if primary_hb >= cutoffs[0]:
            who_classification = "Non-anemic"
            risk_category = "NORMAL_SCREENING_RANGE"
        elif primary_hb >= cutoffs[1]:
            who_classification = "Mild Anemia range"
            risk_category = "MILD_RISK"
        elif primary_hb >= cutoffs[2]:
            who_classification = "Moderate Anemia range"
            risk_category = "MODERATE_RISK"
        else:
            who_classification = "Severe Anemia range"
            risk_category = "HIGH_RISK"

    if inconsistencies or not sensor_tolerance_ok:
        risk_category = "NEEDS_FURTHER_TESTING"

    # 7. Unreliable Measurement Factors
    unreliable_factors = [
        "Ambient lighting variation (color temperature and lux) altering tissue reflection.",
        "Camera sensor auto-white-balance adjustments and flash illumination artifacts.",
        "Optical path obstacles including nail polish, fungal nail changes, or conjunctival inflammation.",
        "Peripheral vasoconstriction due to cold room temperatures or poor capillary refill.",
        "MAX30102 optical sensors measure photoplethysmographic absorption, not direct laboratory hemoglobin."
    ]

    # 8. Plain-English Summary
    summary_parts = []
    if primary_hb is not None:
        summary_parts.append(
            f"Screening indicates an estimated hemoglobin level of {primary_hb:.1f} g/dL "
            f"({who_classification} against WHO reference threshold of {cutoffs[0]:.1f} g/dL)."
        )
    else:
        summary_parts.append("Incomplete screening data: neither sensor reading nor valid image analysis is available.")

    if inconsistencies:
        summary_parts.append(f"Notice: {len(inconsistencies)} data inconsistency/inconsistencies detected. Repeat screening under controlled lighting.")

    if hb_source == "SIMULATED":
        summary_parts.append("Note: The sensor value was generated via hardware simulation / DEMO mode, not an actual biological measurement.")
    elif hb_source == "UNVERIFIED_SENSOR":
        summary_parts.append("Note: Optical sensor values represent uncalibrated PPG signals and require clinical correlation.")

    # 9. Recommendation
    recommendation = (
        "Confirm this screening indication with a formal venous blood test (Complete Blood Count) "
        "and medical evaluation. Non-invasive screening cannot replace a medical diagnosis."
    )
    if risk_category in ("MODERATE_RISK", "HIGH_RISK") or (primary_hb is not None and primary_hb < 8.0):
        recommendation = "URGENT: Hemoglobin is in the moderate-to-severe anemia range. Consult a healthcare provider promptly for diagnostic laboratory testing."

    return {
        "status": "ok",
        "data_present": present,
        "data_missing": missing,
        "values": {
            "hb_g_dl": hb_val,
            "hb_unit": hb_unit,
            "hb_source_classification": hb_source,
            "estimated_image_hb_g_dl": mean_img_hb,
            "eye_pallor_score": eye_pallor,
            "nail_pallor_score": nail_pallor,
            "pulse_bpm": pulse,
            "spo2_percent": spo2,
            "lab_reference_hb_g_dl": lab_ref,
            "who_cutoff_g_dl": cutoffs[0]
        },
        "who_classification": who_classification,
        "screening_risk_category": risk_category,
        "sensor_tolerance_verified": sensor_tolerance_ok,
        "inconsistencies": inconsistencies,
        "warnings": warnings,
        "unreliable_measurement_reasons": unreliable_factors,
        "summary": " ".join(summary_parts),
        "recommendation": recommendation,
        "clinical_disclaimer": (
            "Screening only. Not a medical diagnosis. Non-invasive optical and computer-vision methods "
            "provide screening estimates and must be verified by certified laboratory hematology."
        )
    }
