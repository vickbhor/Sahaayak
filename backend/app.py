from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from dotenv import load_dotenv

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
    if not user or not auth.verify_password(payload.password, user["salt"], user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth.create_token(user["id"], user["email"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}


@app.get("/api/auth/me")
async def me(current_user=Depends(auth.get_current_user)):
    return {"id": current_user["id"], "name": current_user["name"], "email": current_user["email"]}


LANGUAGE_INSTRUCTIONS = {
    "en": "The patient has chosen ENGLISH as the conversation language. Reply ONLY in clear, "
          "plain English. Do not mix in Hindi or Hinglish words.",
    "hi": "The patient has chosen HINDI as the conversation language. Reply ONLY in Hindi, "
          "written in Devanagari script. Do not switch to English or Roman-script Hindi.",
    "hinglish": "The patient has chosen HINGLISH as the conversation language. Reply in casual "
                "Hinglish - Hindi words spelled out in Roman/English letters, mixed naturally "
                "with English, the way people text casually in India.",
}

LANGUAGE_EXAMPLES = {
    "en": 'Example: "Got it, how long have you had this headache? And how severe is it?"',
    "hi": 'उदाहरण: "समझ गया, ये सर दर्द कब से हो रहा है? और कितना गंभीर है?"',
    "hinglish": 'Example: "Samjha maine, toh kab se ye sar dard ho raha hai? Aur kitna severe hai?"',
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
        "temperature": "Temperature",
        "blood_pressure": "Blood Pressure",
        "heart_rate": "Heart Rate",
        "spo2": "SpO2",
        "weight": "Weight",
        "allergies": "Known Allergies",
        "conditions": "Existing Conditions",
    }
    parts = []
    for key, label in label_map.items():
        value = vitals.get(key)
        if value:
            parts.append(f"{label}: {value}")
    return ", ".join(parts)


@app.post("/api/triage", response_model=TriageResponse)
async def process_triage(request: TriageRequest, current_user=Depends(auth.get_current_user)):
    try:
        if request.generate_report:
            # Pull the patient's most recent report (if any) so the extractor
            # can read new symptoms in context (e.g. a recurrence / follow-up)
            # instead of every conversation starting from zero.
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

            prediction = await classifier.predict(extracted_symptoms)
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

            # For urgent cases, auto-fetch nearby hospitals if the client sent
            # a location. If no location was sent, we just skip this quietly --
            # nothing breaks, the patient just doesn't get the extra list.
            nearby_hospitals = None
            hospitals_block = ""
            if urgency in ["CRITICAL", "HIGH"] and request.latitude is not None and request.longitude is not None:
                try:
                    nearby_hospitals = await hospitals.fetch_nearby_hospitals(
                        request.latitude, request.longitude, limit=5
                    )
                except Exception as e:
                    print(f"Auto hospital lookup failed: {e}")
                    nearby_hospitals = None

                if nearby_hospitals:
                    lines = [
                        f"- {h['name']} ({h['distance_km']} km){' - ' + h['phone'] if h.get('phone') else ''}"
                        for h in nearby_hospitals
                    ]
                    hospitals_block = "\nNearby Hospitals:\n" + "\n".join(lines) + "\n"

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

        # --- Plausibility gate: runs BEFORE the main reply is generated ---
        # Catches jokes/impossible claims (e.g. "I'm on Mars") so the main
        # assistant never sees them and can't build an escalating scenario
        # on top of a fake premise.
        latest_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        previous_bot_msg = next(
            (m.content for m in reversed(request.messages[:-1]) if m.role != "user"), ""
        )
        if latest_user_msg:
            plausibility = await check_input_plausibility(latest_user_msg, previous_bot_msg)
            if not plausibility.get("plausible", True):
                clarify_replies = {
                    "en": "I didn't quite follow that — could you answer in simple, real terms?",
                    "hi": "मुझे यह समझ नहीं आया — क्या आप सीधे और सही शब्दों में बता सकते हैं?",
                    "hinglish": "Yeh samajh nahi aaya - seedha aur real jawab de sakte hain?",
                }
                lang_key = (request.preferred_language or "en").lower()
                return TriageResponse(
                    reply=clarify_replies.get(lang_key, clarify_replies["en"]),
                    is_report=False,
                )

        has_symptoms = await assess_conversation_readiness(request.messages)
        wind_down_line = (
            "The patient has already shared a reasonable amount of detail. Do not keep asking new "
            "clarifying questions in every reply - acknowledge what they said, and only ask a follow-up "
            "if something important is genuinely still unclear. It is fine for the conversation to feel "
            "complete; you do not need to keep probing."
            if has_symptoms
            else ""
        )

        language_key = (request.preferred_language or "").lower()
        language_line = LANGUAGE_INSTRUCTIONS.get(language_key, DEFAULT_LANGUAGE_INSTRUCTION)
        example_line = LANGUAGE_EXAMPLES.get(language_key, LANGUAGE_EXAMPLES["en"])

        system_prompt = f"""You are Sahaayak, a friendly medical assistant in an Indian healthcare system.
Your goal is to have a natural, empathetic conversation while gradually gathering information about their symptoms.
Be conversational, not robotic. Ask follow-up questions about their symptoms naturally, but do not repeat
the same question in different words across turns.
Keep responses brief (1-2 sentences max).
If they greet you, greet back warmly. Then ask about their health.
If they describe symptoms, acknowledge and ask clarifying questions.
Never mention reports, buttons, or that you are conducting a triage - just be a friendly helper.
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
to the question you just asked (for example, claiming to be on another planet, a fictional location, or
giving an answer unrelated to what was asked), do NOT build a scenario on top of it or treat it as a real
fact. Just say lightly that you didn't quite follow, and ask them to answer in simple, real terms - do not
escalate urgency or invent elaborate hypothetical advice based on an answer you don't believe is genuine.

Never invent a causal or predictive relationship between two symptoms/answers unless it is well-established
clinically (e.g. do NOT say things like "your throat feels less dry, so your headache should improve soon" -
those are unrelated and that claim is false and could mislead the patient). Just acknowledge what they told
you factually, without speculating about how one answer affects another symptom's outcome.
{language_line}
{vitals_line}
{wind_down_line}
{example_line}"""

        ai_reply = await get_ai_response(request.messages, system_prompt)

        return TriageResponse(reply=ai_reply, is_report=False, suggest_report=has_symptoms)

    except Exception as e:
        print(f"Triage Error: {e}")
        return TriageResponse(reply="I encountered an error. Please try again.", is_report=False)


@app.get("/api/reports")
async def get_reports(current_user=Depends(auth.get_current_user)):
    return database.list_reports(current_user["id"])


@app.get("/api/reports/{report_id}")
async def get_report_detail(report_id: int, current_user=Depends(auth.get_current_user)):
    report = database.get_report(report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
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