# Sahaayak AI Backend — Setup

## 1. Prerequisites
- Python 3.10+
- Docker (for running the OpenSearch vector database)

## 2. Install dependencies
```text
cd backend
python -m venv venv
venv\Scripts\activate        (Windows)
source venv/bin/activate     (Mac/Linux)
pip install -r requirements.txt
```

## 3. Environment variables
Your `.env` should have `GROQ_API_KEY`, `JWT_SECRET`, and OpenSearch configurations (`OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USER`, `OPENSEARCH_PASS`). Keep this file private — never commit it or share it.

## 4. Start the Vector Database & Build Index
Before starting the backend, you must have OpenSearch running and the semantic index built:
```text
docker compose up -d
python build_semantic_index.py
```

## 5. Run the server
```text
python app.py
```
Server runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

## 6. What changed from Phase 1
- **Semantic Search Upgrade**: Completely replaced the old PyTorch/TF-IDF pipeline with OpenSearch k-NN and Sentence-Transformers embeddings.
- **2-Factor Verification**: Groq LLM now acts as a secondary "sanity-checker" for the diagnoses retrieved from OpenSearch.
- Added user accounts: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- `/api/triage` now requires a login token (`Authorization: Bearer <token>` header) and accepts optional `vitals`, `patient_name`, `patient_age`, `patient_gender` fields.
- Every generated report is now saved to a local `sahaayak.db` SQLite file, tied to the logged-in user.
- New `/api/reports` (list) and `/api/reports/{id}` (detail with full chat transcript).
- New `/api/medications` — every medicine the AI has ever suggested across all of a user's past consultations.
- New `/api/hospitals/nearby?lat=..&lon=..` and `/api/hospitals/search?query=..` — free, no-API-key hospital lookup using OpenStreetMap (Overpass + Nominatim).

## 7. Notes
- `sahaayak.db` is created automatically on first run, right next to `app.py`.
- The legacy `models/hingrobert_model/` and PyTorch classifiers are now deprecated in favor of the `sahaayak-symptoms` OpenSearch index.