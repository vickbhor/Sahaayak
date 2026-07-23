import json
import os

_LABELS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "sementic", "scripts", "phase1_artifacts", "labels.json",
)


def _load_reference():
    try:
        with open(_LABELS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {
            entry["name"]: {"urgency": entry["urgency"], "specialist": entry["specialist"]}
            for entry in raw.values()
        }
    except Exception as e:
        print(f"Warning: could not load disease reference table ({e}). Using empty table.")
        return {}


DISEASE_REFERENCE = _load_reference()
KNOWN_DISEASE_NAMES = sorted(DISEASE_REFERENCE.keys())


def lookup(disease_name: str):
    """Case-insensitive lookup against the canonical table. Returns None if unknown."""
    if not disease_name:
        return None
    if disease_name in DISEASE_REFERENCE:
        return DISEASE_REFERENCE[disease_name]
    lower_map = {k.lower(): v for k, v in DISEASE_REFERENCE.items()}
    return lower_map.get(disease_name.strip().lower())
