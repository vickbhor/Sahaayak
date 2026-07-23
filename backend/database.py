import sqlite3
import json

DB_NAME = "sahaayak.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute("PRAGMA table_info(triage_reports)")
    columns = [column[1] for column in cursor.fetchall()]

    if "reasoning" not in columns:
        cursor.execute("ALTER TABLE triage_reports ADD COLUMN reasoning TEXT DEFAULT ''")

    conn.commit()
    conn.close()


def create_user(name: str, email: str, phone: str, pwd_hash: str, salt: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, phone, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
        (name, email, phone, pwd_hash, salt),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str) -> dict:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO triage_reports (
            user_id, patient_name, patient_age, patient_gender,
            symptoms_extracted, predicted_disease, urgency, specialist,
            confidence, medicines, vitals, transcript, reasoning
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(medicines),
            json.dumps(vitals),
            json.dumps(transcript),
            reasoning,
        ),
    )
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def list_reports(user_id: int) -> list:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM triage_reports WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    reports = []
    for r in rows:
        item = dict(r)
        item["medicines"] = json.loads(item["medicines"]) if item.get("medicines") else {}
        item["vitals"] = json.loads(item["vitals"]) if item.get("vitals") else {}
        item["transcript"] = json.loads(item["transcript"]) if item.get("transcript") else []
        if "reasoning" not in item or item["reasoning"] is None:
            item["reasoning"] = ""
        reports.append(item)
    return reports


def get_report(report_id: int, user_id: int) -> dict:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM triage_reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    item["medicines"] = json.loads(item["medicines"]) if item.get("medicines") else {}
    item["vitals"] = json.loads(item["vitals"]) if item.get("vitals") else {}
    item["transcript"] = json.loads(item["transcript"]) if item.get("transcript") else []
    if "reasoning" not in item or item["reasoning"] is None:
        item["reasoning"] = ""
    return item