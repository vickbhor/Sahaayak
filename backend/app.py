from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging

import database
import auth
import hospitals
from semantic_classifier import SemanticMedicalClassifier as MedicalClassifier
from groq_helpers import (
    get_ai_response,
    extract_symptoms_with_groq,
    extract_medicines_with_groq,
    assess_conversation_readiness,
    check_input_plausibility,
)

load_dotenv()
database.init_db()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sahaayak Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

classifier = MedicalClassifier()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class TriageRequest(BaseModel):
    messages: List[ChatMessage]
    generate_report: bool = False
    vitals: Optional[Dict] = None
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    preferred_language: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class TriageResponse(BaseModel):
    reply: str
    is_report: bool = False
    analysis: Dict = {}
    report_id: Optional[int] = None
    suggest_report: bool = False
    nearby_hospitals: Optional[List[Dict]] = None

_DUMMY_HASH, _DUMMY_SALT = auth.hash_password("timing-safety-dummy-password")

CRITICAL_EMERGENCY_TERMS = [
    "chest pain", "heart attack", "stroke", "cannot breathe", "suicide", "suicidal",
    "paralyzed", "severe bleeding", "blood in vomit", "unconscious", "choking", 
    "seizure", "heart is stopping"
]

@app.post("/api/auth/register")
async def register(payload: RegisterRequest):
    email = payload.email.lower()
    existing = database.get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    pwd_hash, salt = auth.hash_password(payload.password)
    user_id = database.create_user(name, email, payload.phone, pwd_hash, salt)
    token = auth.create_token(user_id, email)
    return {"token": token, "user": {"id": user_id, "name": name, "email": email}}

@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    email = payload.email.lower()
    user = database.get_user_by_email(email)

    if user:
        password_ok = auth.verify_password(payload.password, user["salt"], user["password_hash"])
    else:
        auth.verify_password(payload.password, _DUMMY_SALT, _DUMMY_HASH)
        password_ok = False

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth.create_token(user["id"], user["email"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}

@app.get("/api/auth/me")
async def me(current_user=Depends(auth.get_current_user)):
    return {"id": current_user["id"], "name": current_user["name"], "email": current_user["email"]}

LANGUAGE_INSTRUCTIONS = {
    "en": "The patient has chosen ENGLISH as the conversation language. Reply ONLY in clear, plain English. Do not mix in Hindi or Hinglish words.",
    "hi": "The patient has chosen HINDI as the conversation language. Reply ONLY in Hindi, written in Devanagari script. Do not switch to English or Roman-script Hindi.",
    "hinglish": "The patient has chosen HINGLISH as the conversation language. Reply in casual Hinglish - Hindi words spelled out in Roman/English letters, mixed naturally with English.",
}

LANGUAGE_EXAMPLES = {
    "en": 'Example: "I am sorry to hear you are feeling unwell. How long have you had this pain?"',
    "hi": 'उदाहरण: "मुझे सुनकर खेद है कि आपको तकलीफ हो रही है। यह दर्द कब से शुरू हुआ?"',
    "hinglish": 'Example: "Mujhe sunkar dukh hua ki aapko takleef ho rahi hai. Ye dard kab se shuru hua?"',
}

DEFAULT_LANGUAGE_INSTRUCTION = (
    "The patient has not set a language preference. Reply in the SAME language/script the "
    "patient just used in their latest message (English, Hindi, or Hinglish) - mirror them, "
    "do not default to Hindi if they are writing in English."
)

def format_vitals(vitals) -> str:
    if not vitals:
        return ""
    label_map = {
        "temperature": "Temperature", "blood_pressure": "Blood Pressure",
        "heart_rate": "Heart Rate", "spo2": "SpO2", "weight": "Weight",
        "allergies": "Known Allergies", "conditions": "Existing Conditions",
    }
    parts = [f"{label}: {vitals.get(key)}" for key, label in label_map.items() if vitals.get(key)]
    return ", ".join(parts)

@app.post("/api/triage", response_model=TriageResponse)
async def process_triage(request: TriageRequest, current_user=Depends(auth.get_current_user)):
    if not request.messages:
        return TriageResponse(reply="Please describe your symptoms so I can help you.", is_report=False)

    for msg in request.messages:
        if len(msg.content) > 1500:
            msg.content = msg.content[:1500] + "... (truncated)"

    latest_user_msg = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    
    if latest_user_msg and not request.generate_report:
        text_lower = latest_user_msg.lower()
        if any(term in text_lower for term in CRITICAL_EMERGENCY_TERMS):
            emergency_msg = (
                "🚨 **URGENT WARNING:** Your symptoms sound potentially critical. "
                "Please STOP chatting and immediately seek emergency medical care or visit the nearest hospital."
            )
            return TriageResponse(reply=emergency_msg, is_report=False, suggest_report=True)

    try:
        if request.generate_report:
            previous_condition = ""
            previous_reports = database.list_reports(current_user["id"])
            if previous_reports:
                last = previous_reports[0]
                created = (last.get("created_at") or "")[:10]
                previous_condition = f"{last.get('predicted_disease')} (reported {created})" if created else last.get("predicted_disease", "")

            extracted_symptoms = await extract_symptoms_with_groq(request.messages, previous_condition=previous_condition)

            if not extracted_symptoms or extracted_symptoms.lower() == "none":
                return TriageResponse(
                    reply="I couldn't find specific symptoms in our conversation. Could you describe your main health concerns?",
                    is_report=False,
                )

            try:
                prediction = await classifier.predict(extracted_symptoms)
            except Exception as e:
                logger.error(f"Classifier Engine Error: {e}")
                prediction = {
                    "predicted_disease": "Classification Engine Offline",
                    "confidence": 0.0,
                    "urgency": "MEDIUM",
                    "specialist": "General Physician",
                    "reasoning": "Semantic search engine is currently offline."
                }

            disease = prediction["predicted_disease"]
            conf = prediction["confidence"]
            urgency = prediction["urgency"]
            specialist = prediction["specialist"]
            reasoning = prediction.get("reasoning", "")

            remedy_data = await extract_medicines_with_groq(request.messages, disease, urgency, language_key=(request.preferred_language or ""))
            medicines_list = remedy_data.get("medicines", [])
            home_remedies_list = remedy_data.get("home_remedies", [])

            if urgency in ["CRITICAL", "HIGH"]:
                assessment = f"URGENT: {disease}"
                recommendation = f"Please consult a {specialist} immediately. Seek emergency care if symptoms worsen."
            elif conf > 0.6:
                assessment = f"LIKELY {disease}"
                recommendation = f"Please visit a {specialist} for confirmation and treatment."
            else:
                assessment = f"POSSIBLE {disease} (mixed symptoms)"
                recommendation = "Please get a professional medical checkup."

            reasoning_block = f"\nClinical Rationale:\n{reasoning}\n" if reasoning else ""

            nearby_hospitals = None
            hospitals_block = ""
            if urgency in ["CRITICAL", "HIGH"] and request.latitude is not None and request.longitude is not None:
                try:
                    nearby_hospitals = await hospitals.fetch_nearby_hospitals(request.latitude, request.longitude, limit=5)
                    if nearby_hospitals:
                        lines = [f"- {h['name']} ({h['distance_km']} km){' - ' + h['phone'] if h.get('phone') else ''}" for h in nearby_hospitals]
                        hospitals_block = "\nNearby Hospitals:\n" + "\n".join(lines) + "\n"
                except Exception as e:
                    logger.error(f"Auto hospital lookup failed: {e}")

            report = f"""MEDICAL TRIAGE REPORT

Symptoms Reported:
{extracted_symptoms}

Assessment:
{assessment}
Urgency Level: {urgency}
Confidence: {conf * 100:.1f}%
{reasoning_block}
Recommendation:
{recommendation}
{hospitals_block}
DISCLAIMER: This is an AI-assisted triage tool and NOT a substitute for professional medical advice."""

            transcript = [{"role": m.role, "content": m.content} for m in request.messages]

            try:
                report_id = database.create_report(
                    user_id=current_user["id"],
                    patient_name=request.patient_name or current_user["name"],
                    patient_age=request.patient_age,
                    patient_gender=request.patient_gender,
                    symptoms_extracted=extracted_symptoms,
                    predicted_disease=disease,
                    urgency=urgency,
                    specialist=specialist,
                    confidence=conf,
                    medicines=remedy_data,
                    vitals=request.vitals or {},
                    transcript=transcript,
                    reasoning=reasoning,
                )
            except Exception as e:
                logger.error(f"Database Save Error: {e}")
                report_id = None

            return TriageResponse(
                reply=report,
                is_report=True,
                analysis={
                    "symptoms_extracted": extracted_symptoms,
                    "predicted_disease": disease,
                    "urgency": urgency,
                    "specialist": specialist,
                    "confidence": conf,
                    "reasoning": reasoning,
                    "medicines": medicines_list,
                    "home_remedies": home_remedies_list,
                },
                report_id=report_id,
                nearby_hospitals=nearby_hospitals,
            )

        vitals_context = format_vitals(request.vitals)
        vitals_line = f"Patient vitals on record: {vitals_context}." if vitals_context else ""

        previous_bot_msg = next((m.content for m in reversed(request.messages[:-1]) if m.role != "user"), "")
        if latest_user_msg:
            plausibility = await check_input_plausibility(latest_user_msg, previous_bot_msg)
            if not plausibility.get("plausible", True):
                clarify_replies = {
                    "en": "I didn't quite follow that — could you answer in simple, real terms?",
                    "hi": "मुझे यह समझ नहीं आया — क्या आप सीधे और सही शब्दों में बता सकते हैं?",
                    "hinglish": "Yeh samajh nahi aaya - seedha aur real jawab de sakte hain?",
                }
                lang_key = (request.preferred_language or "en").lower()
                return TriageResponse(reply=clarify_replies.get(lang_key, clarify_replies["en"]), is_report=False)

        has_symptoms = await assess_conversation_readiness(request.messages)
        wind_down_line = (
            "The patient has already shared a reasonable amount of detail. Do not keep asking new "
            "clarifying questions in every reply - acknowledge what they said, and only ask a follow-up "
            "if something important is genuinely still unclear. It is fine for the conversation to feel "
            "complete; you do not need to keep probing."
            if has_symptoms else ""
        )

        language_key = (request.preferred_language or "").lower()
        language_line = LANGUAGE_INSTRUCTIONS.get(language_key, DEFAULT_LANGUAGE_INSTRUCTION)
        example_line = LANGUAGE_EXAMPLES.get(language_key, LANGUAGE_EXAMPLES["en"])

        system_prompt = f"""You are Dr. Sahaayak, a highly professional, empathetic, and serious medical triage assistant in India.
Your job is to safely gather symptom information. You must behave like a seasoned, respectful doctor.

🚨 STRICT CLINICAL & PERSONA RULES (MUST OBEY):
1. ZERO POSITIVE SENTIMENT FOR PAIN: NEVER use words like "maja", "achha", "badhiya", "good", or "great" when a patient describes symptoms, pain, or illness. Illness is NEVER fun or good. Do not ask if they "enjoy" it or how water "tastes".
2. MANDATORY EMPATHY: When a patient reports suffering or pain, your VERY FIRST sentence MUST be empathetic (e.g., "I'm sorry you are in pain", "Mujhe sunkar dukh hua ki aapko takleef hai").
3. ONE QUESTION ONLY: After showing empathy, ask EXACTLY ONE focused clinical question (e.g., duration, severity, or exact location). Do not bombard the patient with multiple questions.
4. RESPECTFUL TONE: If using Hindi or Hinglish, ALWAYS use "Aap". NEVER use "Tu" or "Tum". Maintain a serious, mature, and caring tone.

Be conversational, not robotic. Do not repeat the same question in different words across turns.
Keep responses brief (1-2 sentences max).
If they greet you, greet back warmly as a doctor. Then ask how you can help them today.
Never mention reports, buttons, or that you are conducting a triage - just be a helpful doctor.
Never include any bracketed text or instructions in your reply - respond only in natural conversational language.

You are a TEXT CHAT assistant only. You have no body, cannot see or hear the patient, cannot travel
to them, and cannot physically examine them or take a reading yourself. Never say things like "I'm
coming to you", "main aapke paas aa raha hoon", "I'll check your temperature", or any phrase implying
physical presence or action on your part. If you need a vital (temperature, BP, pulse, etc.), ask the
patient to measure it themselves with their own thermometer/device and tell you the number.
This app does not currently connect patients to a live human doctor in real time - there is no such
feature yet. Never promise to "call a doctor for you", say a doctor "will come" or "will see you now",
or imply any live handoff is happening. If the case sounds serious, say so plainly and tell them to see
a doctor or go to a hospital in person/on their own - do not claim the app will arrange it for them.

If a patient's answer is physically impossible, clearly a joke, or doesn't make sense as a real answer
to the question you just asked, do NOT build a scenario on top of it. Just say lightly that you didn't quite follow, and ask them to answer in simple, real terms.

Never invent a causal or predictive relationship between two symptoms/answers unless it is well-established clinically. Just acknowledge what they told you factually.
{language_line}
{vitals_line}
{wind_down_line}
{example_line}"""

        ai_reply = await get_ai_response(request.messages, system_prompt)
        return TriageResponse(reply=ai_reply, is_report=False, suggest_report=has_symptoms)

    except Exception as e:
        logger.error(f"Unhandled Triage Error: {e}", exc_info=True)
        return TriageResponse(reply="Our servers are experiencing heavy load or a technical glitch. Please try again.", is_report=False)

@app.get("/api/reports")
async def get_reports(current_user=Depends(auth.get_current_user)):
    return database.list_reports(current_user["id"])

@app.get("/api/reports/{report_id}")
async def get_report_detail(report_id: int, current_user=Depends(auth.get_current_user)):
    report = database.get_report(report_id, current_user["id"])
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.get("/api/medications")
async def get_medications(current_user=Depends(auth.get_current_user)):
    return database.list_medications(current_user["id"])

@app.get("/api/hospitals/nearby")
async def hospitals_nearby(lat: float, lon: float, current_user=Depends(auth.get_current_user)):
    try:
        results = await hospitals.fetch_nearby_hospitals(lat, lon)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch nearby hospitals: {e}")

@app.get("/api/hospitals/search")
async def hospitals_search(query: str, current_user=Depends(auth.get_current_user)):
    try:
        location = await hospitals.geocode_location(query)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        results = await hospitals.fetch_nearby_hospitals(location["latitude"], location["longitude"])
        return {"location": location, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not search hospitals: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "fallback_mode": classifier.fallback_mode}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)