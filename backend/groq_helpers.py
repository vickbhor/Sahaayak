import os
import json
from typing import List
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
groq_client = AsyncGroq(api_key=GROQ_API_KEY)


def convert_messages_for_llm(messages) -> List[dict]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]


async def get_ai_response(messages, system_prompt: str) -> str:
    try:
        groq_messages = convert_messages_for_llm(messages)
        response = await groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}] + groq_messages,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq Error: {e}")
        return "I'm having trouble understanding. Could you tell me more about your symptoms?"


async def extract_symptoms_with_groq(messages) -> str:
    conversation_text = "\n".join(
        [f"{'Patient' if msg.role == 'user' else 'Assistant'}: {msg.content}" for msg in messages]
    )

    system_prompt = """You are a medical symptom extractor for an Indian healthcare system.
Analyze the conversation and extract ALL physical symptoms/complaints mentioned by the patient.
Translate Hindi/Hinglish symptoms to clear English medical terms.
Return ONLY a comma-separated list of symptoms. NO extra text. If no symptoms found, return "none"
Example output: High fever, severe headache, body ache"""

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation_text},
            ],
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq Error: {e}")
        return "none"


async def assess_conversation_readiness(messages) -> bool:
    user_messages = [m for m in messages if m.role == "user"]
    if len(user_messages) < 2:
        return False

    conversation_text = "\n".join(
        f"{'Patient' if m.role == 'user' else 'Assistant'}: {m.content}" for m in messages
    )

    system_prompt = """You are deciding whether a patient/AI health conversation contains
enough concrete information to generate a medical triage report.

Answer READY only if the patient has named at least one specific physical
symptom or health complaint AND given some supporting detail about it
(such as how long it has lasted, how severe it is, where it is located,
or what triggers/relieves it).

Answer NOT_READY if the conversation so far is only greetings, small talk,
pleasantries ("I'm good, how are you"), or vague statements with no named
symptom yet.

Respond with exactly one word: READY or NOT_READY."""

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation_text},
            ],
            model=GROQ_MODEL,
            temperature=0,
            max_tokens=5,
        )
        verdict = response.choices[0].message.content.strip().upper()
        return verdict.startswith("READY")
    except Exception as e:
        print(f"Groq Readiness Error: {e}")
        return False


IMPOSSIBLE_LOCATION_TERMS = [
    "mars", "moon", "jupiter", "saturn", "venus", "pluto", "neptune", "uranus",
    "mercury", "outer space", "dusri planet", "doosri planet", "another planet",
    "andromeda", "galaxy", "chand par", "mangal par", "mangal grah",
]


async def check_input_plausibility(latest_message: str, previous_bot_question: str = "") -> dict:
    """
    Two-level sanity check that runs BEFORE the main conversational reply is
    generated. Catches physically impossible, joke, or off-topic answers
    (e.g. "I'm on Mars") so the main assistant never gets a chance to build
    an elaborate, escalating response on top of a fake premise.

    Level 1 - deterministic keyword check (instant, free, 100% reliable for
    the obvious cases like celestial bodies/space). Runs first so we don't
    even spend an LLM call on the clearest cases.

    Level 2 - a separate, cheap, low-token LLM classification call for
    everything else. A dedicated check like this is far more reliable than
    hoping one line buried in a big conversational system prompt gets
    followed on every single turn.
    """
    text = (latest_message or "").lower()
    if any(term in text for term in IMPOSSIBLE_LOCATION_TERMS):
        return {"plausible": False, "level": "rule"}

    system_prompt = """You are a fast sanity-checker for a medical triage chatbot.
You will see the assistant's last question (if any) and the patient's latest reply.

Decide if the patient's reply is a genuine, physically possible answer to a
real health conversation - even if vague, incomplete, or in Hindi/Hinglish/English.

Answer IMPLAUSIBLE only if the reply is clearly a joke, sarcasm, a physically
impossible claim (e.g. being on another planet, being a fictional/non-human
entity), or completely unrelated nonsense that no real patient reply would be.

Answer PLAUSIBLE for everything else, including short answers like "na", "haan",
"pata nahi", vague symptom descriptions, or emotional reactions - these are all
normal real patient behavior, not implausible.

Respond with exactly one word: PLAUSIBLE or IMPLAUSIBLE."""

    user_prompt = (
        f'Assistant\'s last question: "{previous_bot_question}"\n'
        f'Patient\'s reply: "{latest_message}"'
    )

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0,
            max_tokens=5,
        )
        verdict = response.choices[0].message.content.strip().upper()
        is_plausible = not verdict.startswith("IMPLAUSIBLE")
        return {"plausible": is_plausible, "level": "llm"}
    except Exception as e:
        print(f"Groq Plausibility Check Error: {e}")
        # Fail open: if the check itself errors out, don't block the conversation.
        return {"plausible": True, "level": "llm_error"}


def clean_json_block(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


REMEDY_LANGUAGE_INSTRUCTIONS = {
    "en": "Write every \"name\", \"purpose\", and \"note\" in clear, plain English.",
    "hi": "Write every \"name\", \"purpose\", and \"note\" in Hindi, in Devanagari script "
          "(e.g. \"पानी अधिक मात्रा में पिएं\"), using correct, natural grammar - not a "
          "word-for-word transliteration.",
    "hinglish": "Write every \"name\", \"purpose\", and \"note\" in short, NATURAL Hinglish, the way "
                "a person actually types it casually, e.g. \"Zyada paani piyein\" or \"Garam paani se "
                "gargle karein\". Each \"name\" must be a single clean 2-5 word phrase - never repeat "
                "or duplicate a verb (e.g. do not write both 'pina' and 'peele' together), and never "
                "produce a phrase that could be misread as an unrelated word (e.g. keep 'pila'/'pi le' "
                "clearly meaning 'drink it', not 'peela' meaning 'yellow').",
}
REMEDY_LANGUAGE_DEFAULT = "en"


async def extract_medicines_with_groq(messages, predicted_disease: str, urgency: str, language_key: str = "") -> dict:
    conversation_text = "\n".join(
        [f"{'Patient' if msg.role == 'user' else 'Assistant'}: {msg.content}" for msg in messages]
    )

    language_key = (language_key or "").lower()
    language_instruction = REMEDY_LANGUAGE_INSTRUCTIONS.get(language_key, REMEDY_LANGUAGE_INSTRUCTIONS[REMEDY_LANGUAGE_DEFAULT])

    system_prompt = f"""You are a cautious clinical assistant for a rural Indian telehealth triage app.
Based on the patient conversation and the predicted condition, produce two separate lists:

1. "medicines": general over-the-counter medicine categories only (e.g. "Paracetamol (OTC)",
   "Antacid", "Oral rehydration salts"). Never give exact dosages or prescription-only medicines.
2. "home_remedies": home-care and lifestyle measures that are not medicines at all (e.g. rest,
   hydration, steam inhalation, warm compress, dietary advice).

If urgency is CRITICAL or HIGH, keep both lists short and clearly secondary to seeking immediate
medical attention - do not imply self-medication replaces a doctor visit.

LANGUAGE: {language_instruction}
Regardless of language, each "name" field is a short LABEL (2-5 words), not a full sentence, and
must read naturally to a native speaker - re-read it before answering and reject anything that
sounds redundant, garbled, or ambiguous. Put any extra detail in "purpose"/"note" instead of
stuffing it into "name".

Return ONLY valid JSON with no markdown fences and no extra text, in this exact shape:
{{"medicines": [{{"name": "...", "purpose": "...", "note": "..."}}], "home_remedies": [{{"name": "...", "purpose": "...", "note": "..."}}]}}
Each list should have at most 4 items. If nothing appropriate applies, return an empty list for it."""

    user_prompt = f"""Predicted condition: {predicted_disease}
Urgency: {urgency}

Conversation:
{conversation_text}"""

    empty_result = {"medicines": [], "home_remedies": []}

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        cleaned = clean_json_block(raw)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            return empty_result

        def clean_list(items):
            valid = []
            if not isinstance(items, list):
                return valid
            for item in items:
                if isinstance(item, dict) and item.get("name"):
                    valid.append(
                        {
                            "name": str(item.get("name"))[:120],
                            "purpose": str(item.get("purpose", ""))[:200],
                            "note": str(item.get("note", ""))[:200],
                        }
                    )
            return valid[:4]

        return {
            "medicines": clean_list(parsed.get("medicines")),
            "home_remedies": clean_list(parsed.get("home_remedies")),
        }
    except Exception as e:
        print(f"Groq Medicine Extraction Error: {e}")
        return empty_result


RED_FLAG_TERMS = [
    "numbness", "numb", "weakness", "difficulty with movement", "can't move",
    "cannot move", "paralysis", "loss of bladder", "loss of bowel",
    "bladder control", "bowel control", "chest pain", "difficulty breathing",
    "shortness of breath", "can't breathe", "cannot breathe", "slurred speech",
    "one-sided weakness", "sudden vision loss", "loss of vision", "fainting",
    "loss of consciousness", "unconscious", "severe bleeding", "coughing blood",
    "blood in vomit", "suicidal", "seizure",
]

URGENCY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def escalate_for_red_flags(symptoms_text: str, urgency: str) -> str:
    text = (symptoms_text or "").lower()
    if any(term in text for term in RED_FLAG_TERMS):
        current_rank = URGENCY_RANK.get((urgency or "LOW").upper(), 0)
        if current_rank < URGENCY_RANK["HIGH"]:
            return "HIGH"
    return urgency


async def verify_prediction_with_groq(
    symptoms_text: str,
    predicted_disease: str,
    confidence: float,
    known_diseases: list = None,
) -> dict:
    grounding_line = ""
    if known_diseases:
        # Ground any "alternative" suggestion in our own verified disease
        # reference table (disease_reference.py) instead of letting the
        # model free-associate a diagnosis we have no urgency/specialist
        # data for. Capped to keep the prompt small.
        sample = ", ".join(known_diseases[:400])
        grounding_line = (
            "\nIf you propose an alternative, prefer a name from this known "
            f"disease list when one clearly matches: {sample}. If nothing on "
            "the list fits, you may still name an alternative outside the list."
        )

    system_prompt = f"""You are a clinical sanity-checker for a symptom-triage system.
You will be given a patient's reported symptoms and a disease predicted by a
retrieval-based classifier. Decide if the prediction is plausible given the
symptoms.

Return ONLY valid JSON, no markdown fences, in this exact shape:
{{"confirmed": true or false, "alternative": "<disease name or null>", "urgency": "<LOW|MEDIUM|HIGH|CRITICAL>", "reasoning": "<one short sentence>"}}

If you agree the prediction is plausible, set confirmed=true, alternative=null,
and still set "urgency" to your own best-judgment urgency for these symptoms
(reason about it yourself, do not just echo the model's confidence).
If a different diagnosis clearly fits the symptoms better, set confirmed=false,
name that alternative, and set "urgency" to the correct urgency level FOR THAT
ALTERNATIVE diagnosis, not the original one. Only disagree on a clear mismatch --
don't nitpick borderline calls.

Err toward a higher urgency whenever symptoms include red flags such as numbness,
weakness, difficulty moving, chest pain, breathing difficulty, sudden neurological
symptoms, or loss of bladder/bowel control - these should never be graded LOW.{grounding_line}"""

    user_prompt = f'Symptoms: "{symptoms_text}"\nPredicted disease: {predicted_disease}\nModel confidence: {confidence:.2f}'

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        cleaned = clean_json_block(raw)
        parsed = json.loads(cleaned)
        urgency = str(parsed.get("urgency", "")).upper()
        if urgency not in URGENCY_RANK:
            urgency = None
        return {
            "confirmed": bool(parsed.get("confirmed", True)),
            "alternative": parsed.get("alternative"),
            "urgency": urgency,
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception as e:
        print(f"Groq Verification Error: {e}")
        return {"confirmed": True, "alternative": None, "urgency": None, "reasoning": "verification unavailable"}