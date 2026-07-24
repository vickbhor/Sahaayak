import json
import os
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from embedder import MultilingualEmbedder

CV_POOL = "phase1_artifacts/cv_pool.csv"
HOLDOUT = "phase1_artifacts/holdout.csv"
LABELS = "phase1_artifacts/labels.json"


OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASS = os.getenv("OPENSEARCH_PASS")

OPENSEARCH_USE_SSL = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"

if not OPENSEARCH_PASS:
    raise RuntimeError(
        "OPENSEARCH_PASS environment variable is not set. Set it in your .env file - "
        "do not hardcode a default here, this file is committed to a public repo."
    )
INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "sahaayak-symptoms")
K = int(os.getenv("SEMANTIC_K", "5"))

PARAPHRASE_CASES = [
    ("high fever, headache, body ache, chills, nausea", "Typhoid"),
    ("high fever, joint pain, rash, pain behind the eyes, vomiting", "Dengue"),
    ("chest pain, sweating, breathlessness, pain radiating to left arm", "Heart Attack"),
    ("cyclical fever, chills, sweating, headache, nausea", "Malaria"),
    ("cough, runny nose, sneezing, mild fever, sore throat", "Common Cold"),
    ("wheezing, breathlessness, chest tightness, cough", "Bronchial Asthma"),
    ("yellowing of skin, yellowing of eyes, dark urine, fatigue", "Jaundice"),
    ("burning urination, frequent urination, lower abdominal pain", "Urinary Tract Infection"),
    ("throbbing headache, nausea, sensitivity to light", "Migraine"),
    ("itching, skin rash, red spots, dischromic patches", "Fungal Infection"),
    ("persistent cough, weight loss, night sweats, blood in sputum", "Tuberculosis"),
    ("excessive thirst, frequent urination, fatigue, blurred vision", "Diabetes"),
]


def get_client():
    from opensearchpy import OpenSearch
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASS),
        # Fix: Now using the environment variable instead of hardcoded True
        use_ssl=OPENSEARCH_USE_SSL,
        verify_certs=OPENSEARCH_USE_SSL,
    )


def create_index(client, dim: int):
    if client.indices.exists(index=INDEX_NAME):
        client.indices.delete(index=INDEX_NAME)
    client.indices.create(
        index=INDEX_NAME,
        body={
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "embedding": {"type": "knn_vector", "dimension": dim},
                    "disease": {"type": "keyword"},
                    "urgency": {"type": "keyword"},
                    "specialist": {"type": "keyword"},
                    "symptom_text": {"type": "text"},
                }
            },
        },
    )


def bulk_index(client, df, embeddings, meta_by_name):
    from opensearchpy.helpers import bulk
    actions = []
    for (_, row), vec in zip(df.iterrows(), embeddings):
        prognosis = row["prognosis"]
        
        # Fix: Catching the silent bug and logging a warning
        if prognosis not in meta_by_name:
            print(f"⚠️ WARNING: '{prognosis}' not found in labels.json! Defaulting to LOW urgency/General Physician.")
            meta = {"urgency": "LOW", "specialist": "General Physician"}
        else:
            meta = meta_by_name[prognosis]

        actions.append({
            "_index": INDEX_NAME,
            "_source": {
                "embedding": vec.tolist(),
                "disease": prognosis,
                "urgency": meta["urgency"],
                "specialist": meta["specialist"],
                "symptom_text": row["symptom_text"],
            },
        })
    bulk(client, actions)
    client.indices.refresh(index=INDEX_NAME)


def knn_query(client, embedder, text, k=K):
    vec = embedder.embed(text)
    res = client.search(index=INDEX_NAME, body={
        "size": k,
        "query": {"knn": {"embedding": {"vector": vec.tolist(), "k": k}}},
    })
    hits = res["hits"]["hits"]
    if not hits:
        return None, 0.0
    votes = Counter(h["_source"]["disease"] for h in hits)
    disease, count = votes.most_common(1)[0]
    return disease, count / len(hits)


def evaluate(client, embedder, df, k=K):
    correct = 0
    rows = []
    for _, row in df.iterrows():
        pred, conf = knn_query(client, embedder, row["symptom_text"], k=k)
        match = pred == row["prognosis"]
        correct += match
        rows.append({"input": row["symptom_text"], "expected": row["prognosis"], "predicted": pred, "confidence": conf, "match": match})
    return correct / len(df), rows


def main():
    cv_pool = pd.read_csv(CV_POOL)
    holdout = pd.read_csv(HOLDOUT)
    labels = json.load(open(LABELS))
    meta_by_name = {v["name"]: v for v in labels.values()}

    print("Loading multilingual embedding model (downloads on first run)...")
    embedder = MultilingualEmbedder()

    train_df, test_df = train_test_split(
        cv_pool, test_size=0.30, random_state=42, stratify=cv_pool["prognosis"]
    )
    print(f"Train: {len(train_df)} rows | 30% test: {len(test_df)} rows")

    print("Embedding training rows...")
    train_vecs = embedder.embed(train_df["symptom_text"].tolist())

    client = get_client()
    create_index(client, dim=embedder.dim)
    bulk_index(client, train_df, train_vecs, meta_by_name)
    print(f"Indexed {len(train_df)} rows into OpenSearch index '{INDEX_NAME}'")

    test_acc, test_rows = evaluate(client, embedder, test_df)
    print(f"70:30 split test accuracy (k={K}): {test_acc:.3f}")

    holdout_acc, holdout_rows = evaluate(client, embedder, holdout)
    print(f"Untouched holdout accuracy (k={K}): {holdout_acc:.3f}")

    para_df = pd.DataFrame(PARAPHRASE_CASES, columns=["symptom_text", "prognosis"])
    para_acc, para_rows = evaluate(client, embedder, para_df)
    print(f"Paraphrase test accuracy (k={K}): {para_acc:.3f}")
    for r in para_rows:
        flag = "OK " if r["match"] else "MISS"
        print(f"  [{flag}] {r['expected']:28s} -> {r['predicted']}")

    with open("semantic_eval_results.json", "w") as f:
        json.dump({
            "split_test_accuracy": test_acc,
            "holdout_accuracy": holdout_acc,
            "paraphrase_accuracy": para_acc,
            "paraphrase_rows": para_rows,
            "k": K,
            "embedding_model": embedder.model.__class__.__name__,
        }, f, indent=2)
    print("\nWrote semantic_eval_results.json")


if __name__ == "__main__":
    main()