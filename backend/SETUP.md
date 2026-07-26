# Sahaayak AI — Backend Setup

This guide covers everything needed to get the FastAPI backend, the OpenSearch semantic index, and the Groq-powered triage pipeline running locally.

---

## 1. Prerequisites

Make sure you have the following installed before starting:

* **Python 3.10+**
* **Docker** (required for running OpenSearch, the vector database used for semantic symptom retrieval)
* A free **[Groq API key](https://console.groq.com)** — needed for the conversational engine and verification step

---

## 2. Start OpenSearch (Vector Database)

OpenSearch stores the semantic symptom index and must be running before you build the index or start the API.

```bash
cd sementic/scripts
docker compose up -d
```

This spins up OpenSearch in the background using the provided `docker-compose.yml`. Leave it running for the rest of setup.

---

## 3. Set Up the Python Environment

```bash
cd backend
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy the example env file and fill in your own values:

```bash
cp .env.example .env        # macOS / Linux
copy .env.example .env      # Windows
```

Edit `.env` and set:

| Variable | Description |
| --- | --- |
| `GROQ_API_KEY` | Your Groq API key (conversation engine + verification) |
| `JWT_SECRET` | Secret used to sign authentication tokens |
| OpenSearch credentials | Connection details for the OpenSearch instance started in step 2 |
| `SEMANTIC_K` | *(optional)* Number of nearest neighbors used at query time — tune this after running the K-sweep in step 5 |

> ⚠️ **Never commit `.env`.** It's already covered by `.gitignore`. Only `.env.example` (with blank values) should be tracked in git.

---

## 5. Build the Semantic Index

From the `sementic/scripts` folder, build the vector index that powers symptom-to-disease retrieval:

```bash
cd ../sementic/scripts
python build_semantic_index.py
```

This single command:

* Embeds the training data and populates the OpenSearch index
* Runs the full accuracy report automatically — no separate evaluation step needed:
  * **70:30 split accuracy** and **untouched holdout accuracy**
  * **Per-class precision / recall / F1**, saved to `semantic_eval_results.json`
  * **Paraphrase accuracy** across 41 hand-written, per-class symptom descriptions not seen in training
  * **K-sweep comparison** at `K = 3, 5, 7, 9` so you can pick the best-performing `SEMANTIC_K` value for `.env`

The run is deterministic (fixed `random_state`) and safe to re-run any time — it overwrites the report and index in place rather than duplicating them.

### (Optional) View the report again later

```bash
python view_metrics.py
```

Re-displays the last saved accuracy report without rebuilding anything.

### (Optional) Evaluate the full end-to-end pipeline

To evaluate retrieval + Groq verification + red-flag escalation together (i.e. what a live request actually goes through):

```bash
python evaluate_end_to_end.py
```

Requires `GROQ_API_KEY` to be set, since it makes real verification calls. Writes `end_to_end_eval_results.json`, which `view_metrics.py` will also pick up automatically if present.

---

## 6. Start the Backend Server

```bash
cd ../../backend
python app.py
```

The API serves at **`http://localhost:8000`**. Interactive Swagger documentation is available at **`http://localhost:8000/docs`**.

---

## 7. Verify Everything Is Working

* `GET /api/auth/me` should return `401` without a token (auth is wired up)
* `GET /api/hospitals/nearby?lat=&lon=` should return results for a known location (OpenStreetMap integration is reachable)
* `POST /api/triage` should return a response with an urgency level, specialist suggestion, and confidence score (Groq + OpenSearch pipeline is working end to end)

If any of these fail, double-check `.env` values and confirm the OpenSearch container from step 2 is still running (`docker ps`).

---

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Backend fails to start / connection refused to OpenSearch | OpenSearch container isn't running — re-run `docker compose up -d` in `sementic/scripts` |
| `build_semantic_index.py` fails with an auth error | OpenSearch credentials in `.env` don't match the running container |
| Triage requests return errors mentioning Groq | `GROQ_API_KEY` missing or invalid in `.env` |
| Login/token errors | `JWT_SECRET` not set in `.env` |

---

For the full project overview, architecture, and API reference, see the root [README.md](../README.md).