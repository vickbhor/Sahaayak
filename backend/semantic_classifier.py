import os
from collections import Counter

from embedder import MultilingualEmbedder
from groq_helpers import verify_prediction_with_groq, escalate_for_red_flags, URGENCY_RANK

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
                "predicted_disease": "Common Cold",
                "urgency": escalate_for_red_flags(extracted_symptoms, "LOW"),
                "specialist": "General Physician",
                "confidence": 0.5,
                "reasoning": "Fallback classification mode active.",
            }

        try:
            query_vec = self.embedder.embed(extracted_symptoms)
            body = {
                "size": K_NEIGHBORS,
                "query": {"knn": {"embedding": {"vector": query_vec.tolist(), "k": K_NEIGHBORS}}},
            }
            res = self.client.search(index=INDEX_NAME, body=body)
            hits = res["hits"]["hits"]
            if not hits:
                return {
                    "predicted_disease": "Unknown Condition",
                    "urgency": escalate_for_red_flags(extracted_symptoms, "LOW"),
                    "specialist": "General Physician",
                    "confidence": 0.0,
                    "reasoning": "No index vector matches found.",
                }

            votes = Counter(h["_source"]["disease"] for h in hits)
            top_disease, vote_count = votes.most_common(1)[0]
            confidence = vote_count / len(hits)
            top_hit = next(h for h in hits if h["_source"]["disease"] == top_disease)
            urgency = top_hit["_source"]["urgency"]
            specialist = top_hit["_source"]["specialist"]

            verified = await verify_prediction_with_groq(extracted_symptoms, top_disease, confidence)
            reasoning = verified.get("reasoning", "")

            if verified.get("confirmed") is False and verified.get("alternative"):
                top_disease = verified["alternative"]
                confidence = min(confidence, 0.5)
                if verified.get("urgency"):
                    urgency = verified["urgency"]
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
                "predicted_disease": "Error processing symptoms",
                "urgency": "UNKNOWN",
                "specialist": "N/A",
                "confidence": 0.0,
                "reasoning": "Error occurred during semantic classification.",
            }