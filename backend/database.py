import sqlite3
import json
import os
from datetime import datetime, timezone

# Absolute path so the DB location doesn't depend on the working directory
# the server happens to be launched from (fixes "why is my data empty" bugs
# when running uvicorn from a different folder).
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sahaayak.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS triage_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            patient_name TEXT,
            patient_age TEXT,
            patient_gender TEXT,
            symptoms_extracted TEXT,
            predicted_disease TEXT,
            urgency TEXT,
            specialist TEXT,
            confidence REAL,
            medicines TEXT,
            vitals TEXT,
            transcript TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Lightweight migration: add the reasoning column for installs that
    # created their sahaayak.db before the Trust Layer feature existed.
    cursor.execute("PRAGMA table_info(triage_reports)")
    columns = [column[1] for column in cursor.fetchall()]
    if "reasoning" not in columns:
        cursor.execute("ALTER TABLE triage_reports ADD COLUMN reasoning TEXT DEFAULT ''")

    conn.commit()
    conn.close()


def _split_remedy_json(raw_medicines_json) -> tuple:
    """
    create_report() stores remedy_data as ONE JSON blob shaped like
    {"medicines": [...], "home_remedies": [...]}. The frontend (ReportDetail.js)
    expects two separate flat arrays: report.medicines and report.home_remedies,
    each with .length checked directly.

    Before this fix, get_report()/list_reports() returned the raw dict as-is
    under the "medicines" key - so report.medicines was an OBJECT, not an
    array. `report.medicines.length` is undefined on a plain object, the
    frontend's `medicines.length > 0` check silently failed, and the whole
    "Suggested Medicines" section never rendered - even when Groq had
    generated real medicine suggestions that were sitting in the DB the
    whole time.
    """
    if not raw_medicines_json:
        return [], []
    raw = json.loads(raw_medicines_json)
    if isinstance(raw, list):
        # Very old rows saved before this shape existed.
        return raw, []
    return raw.get("medicines", []), raw.get("home_remedies", [])


def create_user(name: str, email: str, phone: str, pwd_hash: str, salt: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, phone, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, phone, pwd_hash, salt, now_iso()),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_report(
    user_id: int,
    patient_name: str,
    patient_age: str,
    patient_gender: str,
    symptoms_extracted: str,
    predicted_disease: str,
    urgency: str,
    specialist: str,
    confidence: float,
    medicines: dict,
    vitals: dict,
    transcript: list,
    reasoning: str = "",
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO triage_reports (
            user_id, patient_name, patient_age, patient_gender,
            symptoms_extracted, predicted_disease, urgency, specialist,
            confidence, medicines, vitals, transcript, reasoning, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            patient_name,
            patient_age,
            patient_gender,
            symptoms_extracted,
            predicted_disease,
            urgency,
            specialist,
            confidence,
            json.dumps(medicines if medicines is not None else {"medicines": [], "home_remedies": []}),
            json.dumps(vitals or {}),
            json.dumps(transcript or []),
            reasoning,
            now_iso(),
        ),
    )
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def list_reports(user_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM triage_reports WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    reports = []
    for r in rows:
        item = dict(r)
        item["medicines"], item["home_remedies"] = _split_remedy_json(item.get("medicines"))
        item["vitals"] = json.loads(item["vitals"]) if item.get("vitals") else {}
        item["transcript"] = json.loads(item["transcript"]) if item.get("transcript") else []
        if not item.get("reasoning"):
            item["reasoning"] = ""
        reports.append(item)
    return reports


def get_report(report_id: int, user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM triage_reports WHERE id = ? AND user_id = ?",
        (report_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    item["medicines"], item["home_remedies"] = _split_remedy_json(item.get("medicines"))
    item["vitals"] = json.loads(item["vitals"]) if item.get("vitals") else {}
    item["transcript"] = json.loads(item["transcript"]) if item.get("transcript") else []
    if not item.get("reasoning"):
        item["reasoning"] = ""
    return item


def list_medications(user_id: int) -> list:
    """
    Flattens every report's medicines + home_remedies into one list for the
    /api/medications endpoint.

    NOTE: app.py already calls database.list_medications(...) but this
    function did not exist in this file before -- that endpoint would have
    crashed with an AttributeError the first time anyone hit it. Fixed here.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, predicted_disease, urgency, medicines, created_at "
        "FROM triage_reports WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        raw = json.loads(r["medicines"]) if r["medicines"] else {"medicines": [], "home_remedies": []}
        if isinstance(raw, list):
            raw = {"medicines": raw, "home_remedies": []}
        for category, entries in (
            ("medicine", raw.get("medicines", [])),
            ("home_remedy", raw.get("home_remedies", [])),
        ):
            for m in entries:
                result.append(
                    {
                        "report_id": r["id"],
                        "condition": r["predicted_disease"],
                        "urgency": r["urgency"],
                        "date": r["created_at"],
                        "type": category,
                        "name": m.get("name"),
                        "purpose": m.get("purpose"),
                        "note": m.get("note"),
                    }
                )
    return result