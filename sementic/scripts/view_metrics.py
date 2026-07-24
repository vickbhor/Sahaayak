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
        
    print("="*70 + "\n")

if __name__ == "__main__":
    display_metrics()