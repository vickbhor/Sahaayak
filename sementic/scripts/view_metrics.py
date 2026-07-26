import json
import os

def display_metrics():
    file_path = "semantic_eval_results.json"
    
    if not os.path.exists(file_path):
        print("\n❌ ERROR: 'semantic_eval_results.json' nahi mili!")
        print("Pehle 'python build_semantic_index.py' run karo taaki model train/evaluate ho sake.\n")
        return

    with open(file_path, "r") as f:
        data = json.load(f)

    print("\n" + "="*70)
    print(" 🤖 SAHAAYAK AI - SEMANTIC ENGINE EVALUATION METRICS 🤖".center(70))
    print("="*70)
    
    print(f" 🔹 Embedding Model     :  {data.get('embedding_model', 'N/A')}")
    print(f" 🔹 K-Nearest Neighbors :  {data.get('k', 'N/A')}")
    print("-" * 70)
    
    split_acc = data.get('split_test_accuracy', 0) * 100
    holdout_acc = data.get('holdout_accuracy', 0) * 100
    para_acc = data.get('paraphrase_accuracy', 0) * 100
    
    print(f" ✅ Train/Test Split (70:30) Accuracy :  {split_acc:.2f}%")
    print(f" ✅ Unseen Holdout Data Accuracy      :  {holdout_acc:.2f}%")
    print(f" ✅ Edge-Case Paraphrase Accuracy     :  {para_acc:.2f}%")
    
    print("-" * 70)
    print(" 🩺 PARAPHRASE REAL-WORLD SYMPTOM TESTING:\n")
    
    for row in data.get('paraphrase_rows', []):
        status = "🟢 PASS" if row['match'] else "🔴 FAIL"
        expected = row['expected']
        predicted = row['predicted']
        
        print(f"  {status} | Expected: {expected:<24} | Predicted: {predicted}")

    per_class = data.get('split_test_per_class_report')
    if per_class:
        print("-" * 70)
        print(" 📊 PER-CLASS PRECISION / RECALL / F1 (70:30 split test set):\n")
        print(f"  {'Disease':38s} | {'Prec':>6} | {'Recall':>6} | {'F1':>6} | {'Support':>7}")
        for disease, m in sorted(per_class.items(), key=lambda kv: kv[1].get("support", 0) if isinstance(kv[1], dict) else 0):
            if disease in ("accuracy", "macro avg", "weighted avg"):
                continue
            print(f"  {disease:38s} | {m['precision']:6.2f} | {m['recall']:6.2f} | {m['f1-score']:6.2f} | {int(m['support']):7d}")
        macro = per_class.get("macro avg")
        if macro:
            print(f"  {'MACRO AVG':38s} | {macro['precision']:6.2f} | {macro['recall']:6.2f} | {macro['f1-score']:6.2f} |")

    print("="*70)

    e2e_path = "end_to_end_eval_results.json"
    if os.path.exists(e2e_path):
        with open(e2e_path, "r") as f:
            e2e = json.load(f)
        print("\n" + "="*70)
        print(" 🔗 END-TO-END PIPELINE (retrieval + Groq verification) 🔗".center(70))
        print("="*70)
        for set_name, label in [("split_test", "70:30 split test"), ("holdout", "Holdout"), ("paraphrase", "Paraphrase (41 cases)")]:
            if set_name in e2e:
                acc = e2e[set_name]["accuracy"] * 100
                ovr = e2e[set_name]["override_rate"] * 100
                print(f" 🔹 {label:<20} : accuracy {acc:6.2f}% | verification-capped {ovr:5.1f}%")
        print("="*70 + "\n")
    else:
        print(
            "\nℹ️  No end-to-end results found. Run 'python evaluate_end_to_end.py' "
            "(after build_semantic_index.py) to evaluate the full pipeline, not just "
            "the retrieval layer.\n"
        )

if __name__ == "__main__":
    display_metrics()