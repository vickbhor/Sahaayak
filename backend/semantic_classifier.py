import asyncio
import os
from collections import Counter

from embedder import MultilingualEmbedder
from groq_helpers import verify_prediction_with_groq, escalate_for_red_flags, URGENCY_RANK
from disease_reference import KNOWN_DISEASE_NAMES, lookup as lookup_disease

INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "sahaayak-symptoms")
K_NEIGHBORS = int(os.getenv("SEMANTIC_K", "5"))


class SemanticMedicalClassifier:
    def __init__(self):
        self.fallback_mode = os.getenv("FALLBACK_MODE", "false").lower() == "true"
        if self.fallback_mode:
            return
        try:
            from opensearchpy import OpenSearch
            self.embedder = MultilingualEmbedder()
            self.client = OpenSearch(
                hosts=[{
                    "host": os.getenv("OPENSEARCH_HOST", "localhost"),
                    "port": int(os.getenv("OPENSEARCH_PORT", "9200")),
                }],
                http_auth=(os.getenv("OPENSEARCH_USER", "admin"), os.getenv("OPENSEARCH_PASS", "admin")),
                use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
                verify_certs=False,
            )
            if not self.client.indices.exists(index=INDEX_NAME):
                raise RuntimeError(
                    f"OpenSearch index '{INDEX_NAME}' doesn't exist yet -- "
                    f"run scripts/build_semantic_index.py first."
                )
            print("Semantic classifier (embeddings + OpenSearch) loaded successfully!")
        except Exception as e:
            print(f"Warning: semantic classifier init failed ({e}). Switching to FALLBACK_MODE.")
            self.fallback_mode = True

    async def predict(self, extracted_symptoms: str) -> dict:
        if self.fallback_mode:
            return {
                "predicted_disease": "Unable to classify (semantic engine offline)",
                "urgency": escalate_for_red_flags(extracted_symptoms, "MEDIUM"),
                "specialist": "General Physician",
                "confidence": 0.0,
                "reasoning": "Semantic classifier is offline (OpenSearch unreachable or index missing) — "
                             "this is not a real diagnosis. Please consult a doctor.",
            }

        try:
            query_vec = await asyncio.to_thread(self.embedder.embed, extracted_symptoms)
            body = {
                "size": K_NEIGHBORS,
                "query": {"knn": {"embedding": {"vector": query_vec.tolist(), "k": K_NEIGHBORS}}},
            }
            res = await asyncio.to_thread(self.client.search, index=INDEX_NAME, body=body)
            hits = res["hits"]["hits"]
            if not hits:
                return {
                    "predicted_disease": "Unknown Condition (no similar cases in knowledge base)",
                    "urgency": escalate_for_red_flags(extracted_symptoms, "MEDIUM"),
                    "specialist": "General Physician",
                    "confidence": 0.0,
                    "reasoning": "No similar cases found in the knowledge base — this is not a "
                                 "confirmed diagnosis. Please consult a doctor.",
                }

            votes = Counter(h["_source"]["disease"] for h in hits)
            top_disease, vote_count = votes.most_common(1)[0]
            confidence = vote_count / len(hits)
            top_hit = next(h for h in hits if h["_source"]["disease"] == top_disease)
            urgency = top_hit["_source"]["urgency"]
            specialist = top_hit["_source"]["specialist"]

            verified = await verify_prediction_with_groq(
                extracted_symptoms, top_disease, confidence, KNOWN_DISEASE_NAMES
            )
            reasoning = verified.get("reasoning", "")

            if verified.get("confirmed") is False and verified.get("alternative"):
                top_disease = verified["alternative"]
                confidence = min(confidence, 0.5)
                if verified.get("urgency"):
                    urgency = verified["urgency"]

                ref = lookup_disease(top_disease)
                if ref:
                    specialist = ref.get("specialist", specialist)
                    if URGENCY_RANK.get(ref.get("urgency"), 0) > URGENCY_RANK.get(urgency, 0):
                        urgency = ref["urgency"]
            elif verified.get("urgency"):
                if URGENCY_RANK.get(verified["urgency"], 0) > URGENCY_RANK.get(urgency, 0):
                    urgency = verified["urgency"]

            urgency = escalate_for_red_flags(extracted_symptoms, urgency)

            return {
                "predicted_disease": top_disease,
                "urgency": urgency,
                "specialist": specialist,
                "confidence": round(confidence, 4),
                "reasoning": reasoning,
            }
        except Exception as e:
            print(f"Semantic prediction error: {e}")
            return {
                "predicted_disease": "Unable to classify (an error occurred)",
                "urgency": escalate_for_red_flags(extracted_symptoms, "MEDIUM"),
                "specialist": "General Physician",
                "confidence": 0.0,
                "reasoning": "A technical error occurred during classification — this is not a "
                             "real diagnosis. Please consult a doctor, especially if symptoms are severe.",
            }