import json
import os
from collections import Counter
import warnings
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_env_path = os.path.join(script_dir, "..", "..", "backend", ".env")

if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path, override=True)
    print(f"Loaded .env from: {backend_env_path}")
else:
    load_dotenv(override=True)  # Fallback
    print("WARNING: backend/.env not found at expected path, using fallback load_dotenv()")
# -----------------------------------------------------------

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from embedder import MultilingualEmbedder

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

CV_POOL = "phase1_artifacts/cv_pool_v4.csv"
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
K_SWEEP = [3, 5, 7, 9]  # evaluated in addition to K, no re-indexing needed

# Expanded from the original 12-case set to one paraphrased case per class
# (41/41 classes covered, up from 12/41). Each row is a hand-written,
# differently-worded restatement of that disease's typical presentation --
# never copied from cv_pool_v4.csv/holdout.csv -- so this still measures
# generalization to novel phrasing rather than memorized wording. The
# previous 12-case set had a Wilson 95% CI of roughly 39-86%, too wide to be
# a meaningful headline number; a full 41-case set narrows that considerably
# and gives per-class signal instead of a single aggregate.
PARAPHRASE_CASES = [
    ("severe muscle wasting, chronic diarrhea, recurring infections, very low immunity", "AIDS"),
    ("blackheads and whiteheads on face, oily skin, occasional painful pimples", "Acne"),
    ("swollen belly, yellowish eyes, loss of appetite after years of heavy drinking", "Alcoholic Hepatitis"),
    ("sneezing fits, itchy watery eyes, runny nose after being near dust or pollen", "Allergy"),
    ("stiff and swollen finger joints, worse in the morning, painful to grip things", "Arthritis"),
    ("tight chest, whistling sound while breathing, breathless after light exertion", "Bronchial Asthma"),
    ("stiff neck, tingling down the arm, dull ache at the back of the head", "Cervical Spondylosis"),
    ("itchy fluid-filled blisters all over the body, mild fever, came on over a day", "Chicken Pox"),
    ("persistent itching all over the body, pale stools, yellow-tinted skin", "Chronic Cholestasis"),
    ("blocked nose, mild throat irritation, sneezing, no high fever", "Common Cold"),
    ("sudden high fever, severe joint and muscle pain, rash, pain behind the eyes", "Dengue"),
    ("always thirsty, urinating a lot, unexplained weight loss, tired all the time", "Diabetes"),
    ("painful lump near the anus, bleeding during bowel movements, discomfort sitting", "Dimorphic Hemorrhoids"),
    ("skin rash and itching that started right after starting a new tablet", "Drug Reaction"),
    ("ring-shaped itchy rash on the skin, flaky patches that won't go away", "Fungal Infection"),
    ("watery loose motions, stomach cramps, mild fever, feeling dehydrated", "Gastroenteritis"),
    ("burning sensation in the chest after meals, sour taste rising in the throat", "Gastroesophageal Reflux Disease"),
    ("crushing chest pressure, sweating heavily, pain shooting down the left arm", "Heart Attack"),
    ("sudden nausea and fatigue, mild fever, slight yellowing of the eyes, short-lived", "Hepatitis A"),
    ("long-standing fatigue, joint pain, dark urine, yellowing skin, history of exposure", "Hepatitis B"),
    ("chronic tiredness, mild abdominal discomfort, gradually worsening jaundice", "Hepatitis C"),
    ("sudden worsening of existing liver disease, jaundice, severe fatigue", "Hepatitis D"),
    ("acute jaundice and nausea in a pregnant woman, contaminated water exposure", "Hepatitis E"),
    ("frequent headaches, chest discomfort, consistently high blood pressure readings", "Hypertension"),
    ("racing heartbeat, unexplained weight loss, sweating, hand tremors", "Hyperthyroidism"),
    ("shakiness, cold sweats, confusion, hunger between meals, low blood sugar reading", "Hypoglycemia"),
    ("constant tiredness, weight gain, feeling cold all the time, dry skin", "Hypothyroidism"),
    ("honey-colored crusty sores around the mouth and nose, mildly itchy", "Impetigo"),
    ("yellow tint to the skin and eyes, dark-colored urine, general weakness", "Jaundice"),
    ("recurring bouts of high fever with chills and sweating every couple of days", "Malaria"),
    ("throbbing one-sided headache, nausea, can't stand bright light", "Migraine"),
    ("knee and hip pain that's worse after activity, stiffness that eases with movement", "Osteoarthritis"),
    ("sudden weakness down one side of the body, difficulty speaking, severe headache", "Paralysis (Brain Hemorrhage)"),
    ("gnawing pain in the upper stomach that worsens on an empty stomach", "Peptic Ulcer Disease"),
    ("high fever with chills, cough with phlegm, sharp pain on breathing in", "Pneumonia"),
    ("thick silvery scaly patches on the skin, itching, worse on elbows and scalp", "Psoriasis"),
    ("cough lasting for weeks, coughing up blood-tinged sputum, night sweats, weight loss", "Tuberculosis"),
    ("prolonged fever that steps up gradually day by day, stomach pain, weakness", "Typhoid"),
    ("stinging pain while urinating, needing to urinate often, cloudy urine", "Urinary Tract Infection"),
    ("bulging, twisted veins visible under the skin on the legs, heaviness by evening", "Varicose Veins"),
    ("spinning sensation when turning the head, brief episodes, mild nausea", "Vertigo (Benign Paroxysmal Positional)"),
]


def get_client():
    from opensearchpy import OpenSearch
    print(f"Connecting to OpenSearch: host={OPENSEARCH_HOST} port={OPENSEARCH_PORT} "
          f"use_ssl={OPENSEARCH_USE_SSL} user={OPENSEARCH_USER}")
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASS),
        use_ssl=OPENSEARCH_USE_SSL,
        verify_certs=False, 
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

    # --- Per-class precision/recall/F1 on the split test set ---
    # Raw accuracy alone hides class imbalance: several CRITICAL-urgency
    # diseases (Heart Attack=10, AIDS=9, Paralysis=9 total examples) have far
    # fewer training examples than common LOW/MEDIUM ones (Chicken Pox=118,
    # Diabetes=118), so a high overall accuracy could still mask the model
    # doing poorly on exactly the cases where a miss is most dangerous.
    y_true = [r["expected"] for r in test_rows]
    y_pred = [r["predicted"] for r in test_rows]
    per_class_report = classification_report(
        y_true, y_pred, zero_division=0, output_dict=True
    )
    print("\n=== Per-class precision / recall / F1 (70:30 split test set) ===")
    print(f"{'Disease':38s} | {'Prec':>6} | {'Recall':>6} | {'F1':>6} | {'Support':>7}")
    for disease, m in sorted(per_class_report.items(), key=lambda kv: kv[1].get("support", 0) if isinstance(kv[1], dict) else 0):
        if disease in ("accuracy", "macro avg", "weighted avg"):
            continue
        print(f"{disease:38s} | {m['precision']:6.2f} | {m['recall']:6.2f} | {m['f1-score']:6.2f} | {int(m['support']):7d}")
    macro = per_class_report["macro avg"]
    print(f"{'MACRO AVG (unweighted across classes)':38s} | {macro['precision']:6.2f} | {macro['recall']:6.2f} | {macro['f1-score']:6.2f} |")

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
            "split_test_per_class_report": per_class_report,
            "holdout_accuracy": holdout_acc,
            "paraphrase_accuracy": para_acc,
            "paraphrase_rows": para_rows,
            "k": K,
            "embedding_model": embedder.model.__class__.__name__,
        }, f, indent=2)
    print("\nWrote semantic_eval_results.json")

    # --- K sweep: compare accuracy across different K values, no re-indexing needed ---
    print("\n=== K sweep comparison (same index, different K at query time) ===")
    print(f"{'K':>3} | {'Split':>7} | {'Holdout':>8} | {'Paraphrase':>10}")
    for k_val in sorted(set(K_SWEEP + [K])):
        s_acc, _ = evaluate(client, embedder, test_df, k=k_val)
        h_acc, _ = evaluate(client, embedder, holdout, k=k_val)
        p_acc, _ = evaluate(client, embedder, para_df, k=k_val)
        marker = " <- current SEMANTIC_K" if k_val == K else ""
        print(f"{k_val:>3} | {s_acc*100:>6.2f}% | {h_acc*100:>7.2f}% | {p_acc*100:>9.2f}%{marker}")


if __name__ == "__main__":
    main()