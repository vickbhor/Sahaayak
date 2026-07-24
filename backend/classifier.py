import os

TORCH_AVAILABLE = True
try:
    import torch
    import torch.nn as nn

    class SahaayakNet(nn.Module):
        def __init__(self, input_dim, num_classes):
            super(SahaayakNet, self).__init__()
            self.layer1 = nn.Linear(input_dim, 256)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.3)
            self.layer2 = nn.Linear(256, 128)
            self.layer3 = nn.Linear(128, num_classes)

        def forward(self, x):
            out = self.layer1(x)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.layer2(out)
            out = self.relu(out)
            out = self.layer3(out)
            return out

except ImportError:
    TORCH_AVAILABLE = False

try:
    import joblib
except ImportError:
    joblib = None


ADVANCED_LABELS = {
    0: {"name": "Psoriasis", "urgency": "LOW", "specialist": "Dermatologist"},
    1: {"name": "Varicose Veins", "urgency": "LOW", "specialist": "Vascular Surgeon"},
    2: {"name": "Peptic Ulcer Disease", "urgency": "MEDIUM", "specialist": "Gastroenterologist"},
    3: {"name": "Drug Reaction", "urgency": "HIGH", "specialist": "Allergist / ER"},
    4: {"name": "Gastroesophageal Reflux Disease", "urgency": "LOW", "specialist": "Gastroenterologist"},
    5: {"name": "Allergy", "urgency": "MEDIUM", "specialist": "Allergist"},
    6: {"name": "Urinary Tract Infection", "urgency": "MEDIUM", "specialist": "Urologist / General Physician"},
    7: {"name": "Malaria", "urgency": "HIGH", "specialist": "Infectious Disease Specialist"},
    8: {"name": "Jaundice", "urgency": "HIGH", "specialist": "Hepatologist"},
    9: {"name": "Cervical Spondylosis", "urgency": "LOW", "specialist": "Orthopedist / Neurologist"},
    10: {"name": "Migraine", "urgency": "MEDIUM", "specialist": "Neurologist"},
    11: {"name": "Hypertension", "urgency": "HIGH", "specialist": "Cardiologist"},
    12: {"name": "Bronchial Asthma", "urgency": "HIGH", "specialist": "Pulmonologist"},
    13: {"name": "Osteoarthritis", "urgency": "LOW", "specialist": "Orthopedist"},
    14: {"name": "Deep Vein Thrombosis", "urgency": "CRITICAL", "specialist": "Vascular Surgeon / ER"},
    15: {"name": "Pneumonia", "urgency": "HIGH", "specialist": "Pulmonologist"},
    16: {"name": "Dimorphic Hemorrhoids", "urgency": "MEDIUM", "specialist": "Proctologist / General Surgeon"},
    17: {"name": "Arthritis", "urgency": "LOW", "specialist": "Rheumatologist"},
    18: {"name": "Acne", "urgency": "LOW", "specialist": "Dermatologist"},
    19: {"name": "Impetigo", "urgency": "MEDIUM", "specialist": "Dermatologist / Pediatrician"},
    20: {"name": "Fungal Infection", "urgency": "LOW", "specialist": "Dermatologist"},
    21: {"name": "Common Cold", "urgency": "LOW", "specialist": "General Physician"},
    22: {"name": "Dengue", "urgency": "CRITICAL", "specialist": "Infectious Disease Specialist / ER"},
    23: {"name": "Typhoid", "urgency": "HIGH", "specialist": "General Physician / Infectious Disease"},
}


class MedicalClassifier:
    def __init__(self, model_dir="models/hingrobert_model"):
        self.fallback_mode = os.getenv("FALLBACK_MODE", "false").lower() == "true"
        self.id2label_advanced = ADVANCED_LABELS

        if not TORCH_AVAILABLE or joblib is None:
            self.fallback_mode = True

        if not self.fallback_mode:
            try:
                print(f"Loading custom PyTorch model from {model_dir}...")
                self.vectorizer = joblib.load(os.path.join(model_dir, "vectorizer.joblib"))
                input_dim = len(self.vectorizer.get_feature_names_out())
                num_classes = len(self.id2label_advanced)
                self.model = SahaayakNet(input_dim, num_classes)
                self.model.load_state_dict(
                    torch.load(os.path.join(model_dir, "model.pt"), weights_only=True)
                )
                self.model.eval()
                print("PyTorch Model loaded successfully!")
            except Exception as e:
                print(f"Warning: Failed to load model. Error: {e}")
                print("Switching to FALLBACK_MODE.")
                self.fallback_mode = True

    async def predict(self, extracted_symptoms: str) -> dict:
        if self.fallback_mode:
            lower_symps = extracted_symptoms.lower()
            if "headache" in lower_symps or "sir dard" in lower_symps or "sar dard" in lower_symps:
                return {"predicted_disease": "Migraine", "urgency": "MEDIUM", "specialist": "Neurologist", "confidence": 0.85}
            elif "fever" in lower_symps or "bukhar" in lower_symps or "tez bukhar" in lower_symps:
                return {"predicted_disease": "Typhoid", "urgency": "HIGH", "specialist": "General Physician / Infectious Disease", "confidence": 0.75}
            elif "cough" in lower_symps or "khansi" in lower_symps:
                return {"predicted_disease": "Bronchial Asthma", "urgency": "MEDIUM", "specialist": "Pulmonologist", "confidence": 0.70}
            else:
                return {"predicted_disease": "Common Cold", "urgency": "LOW", "specialist": "General Physician", "confidence": 0.60}

        try:
            X = self.vectorizer.transform([extracted_symptoms]).toarray()
            X_tensor = torch.FloatTensor(X)

            with torch.no_grad():
                outputs = self.model(X_tensor)

            probs = torch.nn.functional.softmax(outputs, dim=1)
            predicted_class_id = probs.argmax().item()
            confidence = probs.max().item()

            disease_data = self.id2label_advanced.get(
                predicted_class_id,
                {"name": "Unknown Condition", "urgency": "LOW", "specialist": "General Physician"},
            )

            return {
                "predicted_disease": disease_data["name"],
                "urgency": disease_data["urgency"],
                "specialist": disease_data["specialist"],
                "confidence": round(confidence, 4),
            }
        except Exception as e:
            print(f"Prediction Error: {e}")
            return {"predicted_disease": "Error processing symptoms", "urgency": "UNKNOWN", "specialist": "N/A", "confidence": 0.0}
