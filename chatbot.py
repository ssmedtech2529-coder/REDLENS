"""
Red Lens AI Assistant & Chatbot Engine.
Handles conversational AI queries, prompt construction with biomedical safety constraints,
and robust fallback answers for standard clinical screening inquiries.
"""

import os
import json
from typing import Any, Dict, List, Optional
import httpx

SYSTEM_PROMPT = """You are Red Lens AI Assistant, a biomedical software engineer and clinical education helper within the Red Lens Anemia Screening System.

Core Operating Principles:
1. Communication Style:
   - Use clear, empathetic, and concise language.
   - Avoid overly dense medical jargon without explaining it.
   - Reply in {lang_name}.

2. Clinical & Safety Boundaries:
   - You are an educational screening assistant, NOT a doctor. You CANNOT give a definitive medical diagnosis or prescribe medications.
   - Always clarify that this system is a RESEARCH & SCREENING PROTOTYPE.
   - Explain that non-invasive image pallor and optical sensors (such as MAX30102) provide screening estimates and cannot replace a laboratory Complete Blood Count (CBC) test.
   - Always encourage confirmatory laboratory testing and consultation with a qualified medical professional.

3. Verified Screening Context (Ground Truth):
   - When VERIFIED SCREENING DATA is provided, base your answers strictly on this data. NEVER invent, alter, or hallucinate patient measurements, sensor numbers, or image findings.
   - If image analysis and sensor readings disagree, highlight this inconsistency clearly, explain common physical causes (lighting, shadow, skin perfusion, nail polish), and recommend laboratory re-testing.
   - If critical symptoms or low SpO2 (<90%) are present, advise urgent medical care.

4. Educational Topics You Cover:
   - What anemia is (deficiency in hemoglobin or red blood cells reducing oxygen delivery).
   - Common symptoms (fatigue, pale skin/conjunctiva, dizziness, shortness of breath, tachycardia).
   - Dietary sources of iron (spinach, lentils, dates, jaggery, poultry, fish) and vitamin C for absorption enhancers.
   - The difference between optical screening (surface reflectance) and certified venous blood laboratory tests.
"""

CLINICAL_KNOWLEDGE_BASE = {
    "what is anemia": (
        "Anemia is a medical condition where the concentration of hemoglobin (the oxygen-carrying protein in red blood cells) "
        "falls below physiological requirements. Symptoms can include persistent fatigue, weakness, dizziness, and pale skin. "
        "A definitive diagnosis requires a laboratory Complete Blood Count (CBC) test and evaluation by a healthcare provider."
    ),
    "symptoms": (
        "Common symptoms of anemia include:\n"
        "• Unexplained tiredness or fatigue\n"
        "• Paleness in the lower eyelids (conjunctiva), nail beds, or gums\n"
        "• Dizziness, lightheadedness, or headaches\n"
        "• Shortness of breath during mild exertion\n"
        "• Rapid or irregular heartbeat (tachycardia)\n"
        "These signs warrant a laboratory blood test to identify the underlying cause."
    ),
    "causes": (
        "Low hemoglobin can result from:\n"
        "• Nutritional deficiencies (insufficient dietary iron, vitamin B12, or folate)\n"
        "• Blood loss (menstruation, gastrointestinal bleeding, ulcers, or injuries)\n"
        "• Increased physiological demand (pregnancy, lactation, rapid adolescent growth)\n"
        "• Chronic inflammatory conditions, infections, or genetic hemoglobin variants\n"
        "A doctor determines the exact cause through specific blood tests."
    ),
    "iron": (
        "To support healthy hemoglobin levels, consider an iron-rich diet:\n"
        "• Plant sources: Dark leafy greens (spinach, moringa), beans, lentils, chickpeas, jaggery, dates, raisins, and sesame seeds.\n"
        "• Animal sources: Eggs, poultry, fish, and lean meats (contain high-absorption heme iron).\n"
        "• Absorption Tip: Pair iron foods with Vitamin C (citrus fruits, amla, guava, tomatoes), and avoid tea/coffee immediately around meals."
    ),
    "red lens": (
        "Red Lens is an AI-assisted non-invasive anemia screening prototype. It captures photos of the lower eyelid (conjunctiva) "
        "and fingernail bed, extracts colorimetric pallor metrics using OpenCV (RGB, HSV, and CIE Lab a* channel), and combines them "
        "with optical sensor readings. It is an initial screening indicator designed to identify who needs formal laboratory testing."
    ),
    "max30102": (
        "The MAX30102 is a photoplethysmography (PPG) optical sensor that shines red (660 nm) and infrared (880 nm) light through capillary beds. "
        "By measuring cyclic light absorption changes, it derives heart rate and blood oxygen saturation (SpO2). "
        "Important: Standard optical PPG sensors are not clinically certified for direct hemoglobin measurement without specialized calibration."
    ),
    "laboratory": (
        "A certified laboratory Complete Blood Count (CBC) directly measures hemoglobin concentration from venous blood using automated hematology analyzers. "
        "It is the gold standard diagnostic reference. Non-invasive screening systems like Red Lens serve only as early-detection flags to indicate who requires laboratory referral."
    ),
    "limitations": (
        "Non-invasive screening has several known clinical limitations:\n"
        "• Ambient lighting variations and flash reflections alter skin color analysis.\n"
        "• Cosmetics, nail polish, or conjunctival inflammation skew pallor scores.\n"
        "• Peripheral coldness or vasoconstriction reduces capillary blood flow.\n"
        "• Optical sensors are uncalibrated for standalone hemoglobin diagnosis."
    ),
    "explain report": (
        "To review your screening report: Look at the final screening classification, the agreement between eye and nail pallor, "
        "and any data quality warnings. If signals disagree or show possible anemia, visit a clinic for a confirmatory venous blood test."
    )
}


def build_demo_reply(message: str, lang: str, agent_summary: Optional[Dict[str, Any]]) -> str:
    """Generate intelligent fallback response based on clinical rules when API key is missing."""
    msg = message.lower().strip()

    # If the user asks about an attached screening report
    if agent_summary and any(kw in msg for kw in ["report", "screening", "result", "my", "this", "explain", "findings"]):
        summary = agent_summary.get("summary", "")
        recs = agent_summary.get("recommendation", "")
        warnings = agent_summary.get("warnings", [])
        disagreement = agent_summary.get("inconsistencies", [])
        values = agent_summary.get("values", {})
        risk = agent_summary.get("screening_risk_category", "N/A")

        parts = [
            "[DEMO MODE — Rule-Based Clinical Analysis]",
            f"Screening Summary: {summary}",
            f"Assessed Risk Category: {risk}",
            f"Key Parameters: Sensor Hb: {values.get('hb_g_dl', 'N/A')} g/dL ({values.get('hb_source_classification', 'N/A')}), "
            f"Eye Pallor: {values.get('eye_pallor_score', 'N/A')}/100, Nail Pallor: {values.get('nail_pallor_score', 'N/A')}/100."
        ]
        if warnings:
            parts.append("Quality Observations: " + " | ".join(warnings))
        if disagreement:
            parts.append("Cross-modal Disagreement: " + " | ".join(disagreement))
        parts.append(f"Recommended Next Steps: {recs}")
        parts.append(
            "\nNote: To ask open-ended questions to the Generative AI agent, please configure OPENAI_API_KEY in backend/.env."
        )
        return "\n\n".join(parts)

    # Search clinical knowledge base
    for key, text in CLINICAL_KNOWLEDGE_BASE.items():
        if key in msg or all(w in msg for w in key.split()):
            return f"[DEMO MODE]\n\n{text}\n\n(Tip: Add OPENAI_API_KEY in backend/.env to unlock conversational AI reasoning.)"

    return (
        "[DEMO MODE: AI API Key not configured]\n\n"
        "I am currently running in offline DEMO mode because no OpenAI or Gemini API key was found in backend/.env.\n\n"
        "You can ask me any of the following standard questions:\n"
        "• What is anemia?\n"
        "• What are the common symptoms of anemia?\n"
        "• What causes low hemoglobin?\n"
        "• Which foods contain iron?\n"
        "• How does the Red Lens system work?\n"
        "• How does the MAX30102 sensor work?\n"
        "• What are the limitations of AI-based anemia screening?\n"
        "• Why is a laboratory Hb test important?\n\n"
        "To enable real-time generative responses, copy .env.example to backend/.env and add your OPENAI_API_KEY."
    )


async def llm_reply(
    message: str,
    history: List[Dict[str, str]],
    lang: str = "en",
    agent_summary: Optional[Dict[str, Any]] = None
) -> str:
    """
    Call external LLM API securely from backend with strict biomedical system constraints.
    Supports standard OpenAI, OpenAI-compatible APIs (OpenRouter, Groq, Ollama), or Gemini.
    """
    key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise LookupError("NO_API_KEY")

    lang_name = "Tamil" if lang == "ta" else "simple English"
    system_text = SYSTEM_PROMPT.format(lang_name=lang_name)

    if agent_summary:
        system_text += "\n\n--- VERIFIED SCREENING DATA (Ground Truth from Backend Analysis) ---\n"
        system_text += json.dumps(agent_summary, indent=2)
        system_text += "\nDo not contradict or hallucinate any metrics above."

    messages = [{"role": "system", "content": system_text}]

    # Include recent sanitized chat history
    for h in history[-8:]:
        role = h.get("role")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:1000]})

    messages.append({"role": "user", "content": message.strip()})

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # If user provided a Google Gemini API key and standard Gemini URL
    if "generativelanguage.googleapis.com" in base_url or os.getenv("GEMINI_API_KEY"):
        # Google's OpenAI-compatible endpoint accepts Authorization Bearer
        pass

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.3
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)

    response.raise_for_status()
    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise ValueError("AI provider returned an empty response.")

    return choices[0]["message"]["content"].strip()
