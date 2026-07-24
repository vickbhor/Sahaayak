"""
Merge Symptom2Disease (natural-language, 24 classes, 50/class) into the
existing cv_pool.csv (keyword-list style, 41 classes, 4-9/class).

What this does:
  1. Normalizes Symptom2Disease labels to the exact disease names used in
     labels.json (case differences only -- e.g. "urinary tract infection"
     -> "Urinary Tract Infection").
  2. Drops exact-duplicate text rows from Symptom2Disease (47 found).
  3. Appends the cleaned Symptom2Disease rows to cv_pool.csv, producing
     cv_pool_v2.csv. The 17 diseases NOT covered by Symptom2Disease keep
     their original (small) cv_pool rows untouched.
  4. Leaves holdout.csv and the PARAPHRASE_CASES in build_semantic_index.py
     COMPLETELY UNTOUCHED -- those must stay a genuinely unseen test set.

Output: cv_pool_v2.csv, plus a short report printed to stdout.
"""
import json
import pandas as pd

CV_POOL = "cv_pool.csv"
S2D = "Symptom2Disease.csv"
LABELS = "labels.json"
OUT = "cv_pool_v2.csv"


def main():
    cv_pool = pd.read_csv(CV_POOL)
    s2d = pd.read_csv(S2D)
    labels = json.load(open(LABELS))
    canonical_names = {v["name"] for v in labels.values()}
    lower_to_canonical = {n.lower(): n for n in canonical_names}

    # --- normalize labels ---
    s2d["prognosis"] = s2d["label"].apply(lambda x: lower_to_canonical.get(x.lower(), x))
    unmatched = set(s2d["prognosis"]) - canonical_names
    if unmatched:
        print(f"WARNING: {len(unmatched)} Symptom2Disease labels didn't match labels.json: {unmatched}")

    # --- dedupe exact-duplicate symptom text ---
    before = len(s2d)
    s2d = s2d.drop_duplicates(subset=["text"])
    print(f"Deduped Symptom2Disease: {before} -> {len(s2d)} rows ({before - len(s2d)} exact duplicates removed)")

    s2d_clean = s2d.rename(columns={"text": "symptom_text"})[["symptom_text", "prognosis"]]

    # --- combine ---
    merged = pd.concat([cv_pool[["symptom_text", "prognosis"]], s2d_clean], ignore_index=True)
    merged = merged.drop_duplicates(subset=["symptom_text"])
    merged.to_csv(OUT, index=False)

    # --- report ---
    print("\n=== Per-disease row counts (cv_pool_v2.csv) ===")
    counts = merged["prognosis"].value_counts().sort_values()
    print(counts.to_string())
    print(f"\nTotal rows: {len(merged)}  |  Classes: {merged['prognosis'].nunique()}")
    print(f"Wrote {OUT}")

    still_thin = counts[counts < 10]
    if len(still_thin):
        print(f"\nNOTE: {len(still_thin)} classes still have <10 examples "
              f"(no Symptom2Disease coverage for these -- consider LLM-augmenting "
              f"these specifically): {list(still_thin.index)}")


if __name__ == "__main__":
    main()
