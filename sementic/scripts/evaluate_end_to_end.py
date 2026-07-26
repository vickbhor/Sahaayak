"""
End-to-end pipeline evaluation.

build_semantic_index.py's evaluate() only measures the raw k-NN retrieval
layer (embed -> query OpenSearch -> majority vote). It never calls the Groq
verification step or the red-flag escalation ratchet, even though both are
already wired into SemanticMedicalClassifier.predict() in backend/. That gap
was flagged as the paper's own "most consequential limitation" -- this script
closes it by running the exact same predict() coroutine the live app uses,
against the same three eval sets (70:30 split test, holdout, paraphrase), and
reports:

  - end-to-end accuracy on each set (retrieval + Groq verification combined)
  - the Groq *override rate*: how often verification changed the retrieval
    layer's top prediction (this is the number reviewers will ask for --
    "how often does the LLM verification step actually do something?")
  - confidence after the confidence-cap-on-override rule (min(confidence, 0.5))

PREREQUISITE: run build_semantic_index.py first so the OpenSearch index is
already populated with the *training* split (this script does NOT rebuild
the index -- it reuses whatever is already indexed, and only evaluates
end-to-end predictions on the held-out rows). It uses the identical
random_state=42 / test_size=0.30 split as build_semantic_index.py so the
"held-out" rows here are guaranteed to be the same rows that were excluded
from the index, not rows the retrieval layer has already seen.

Requires GROQ_API_KEY set (in backend/.env) since this exercises the real
Groq verification call, not a mock.

Usage:
    python evaluate_end_to_end.py
"""
import asyncio
import json
import os
import sys

import pandas as pd
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..", "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

backend_env_path = os.path.join(BACKEND_DIR, ".env")
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path, override=True)
else:
    load_dotenv(override=True)

from semantic_classifier import SemanticMedicalClassifier  # noqa: E402
from build_semantic_index import CV_POOL, HOLDOUT, PARAPHRASE_CASES  # noqa: E402

CV_POOL_PATH = os.path.join(SCRIPT_DIR, CV_POOL)
HOLDOUT_PATH = os.path.join(SCRIPT_DIR, HOLDOUT)


async def evaluate_set(classifier, df, set_name):
    correct = 0
    overridden = 0
    rows = []
    for _, row in df.iterrows():
        symptoms, expected = row["symptom_text"], row["prognosis"]
        result = await classifier.predict(symptoms)
        predicted = result["predicted_disease"]
        match = predicted == expected
        # An "override" is detectable from the outside as confidence capped
        # at <= 0.5 by the verification step (see semantic_classifier.py's
        # `confidence = min(confidence, 0.5)` on disconfirm-with-alternative).
        # This is a proxy, not a perfect signal, but it's the only one
        # observable from predict()'s return value without changing its
        # contract.
        was_capped = result["confidence"] <= 0.5
        overridden += was_capped
        correct += match
        rows.append({
            "input": symptoms,
            "expected": expected,
            "predicted": predicted,
            "confidence": result["confidence"],
            "urgency": result["urgency"],
            "match": match,
            "verification_likely_overrode_retrieval": was_capped,
        })
    n = len(df)
    print(f"\n=== {set_name} (n={n}) ===")
    print(f"End-to-end accuracy (retrieval + Groq verification): {correct/n:.3f}")
    print(f"Groq verification touched / capped confidence on: {overridden}/{n} ({overridden/n:.1%})")
    return {
        "accuracy": correct / n,
        "override_rate": overridden / n,
        "rows": rows,
    }


async def main():
    classifier = SemanticMedicalClassifier()
    if classifier.fallback_mode:
        print(
            "SemanticMedicalClassifier came up in FALLBACK_MODE, which means "
            "either OpenSearch isn't reachable or the index doesn't exist yet. "
            "Run build_semantic_index.py first, then re-run this script."
        )
        return

    cv_pool = pd.read_csv(CV_POOL_PATH)
    holdout = pd.read_csv(HOLDOUT_PATH)
    para_df = pd.DataFrame(PARAPHRASE_CASES, columns=["symptom_text", "prognosis"])

    # Same split as build_semantic_index.py -- these test_df rows were
    # excluded from the index, so this is a fair end-to-end evaluation.
    _, test_df = train_test_split(
        cv_pool, test_size=0.30, random_state=42, stratify=cv_pool["prognosis"]
    )

    results = {}
    results["split_test"] = await evaluate_set(classifier, test_df, "70:30 split test set")
    results["holdout"] = await evaluate_set(classifier, holdout, "Untouched holdout set")
    results["paraphrase"] = await evaluate_set(classifier, para_df, "Paraphrase set (41 cases)")

    out_path = os.path.join(SCRIPT_DIR, "end_to_end_eval_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
