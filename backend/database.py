import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sahaayak.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
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
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(name, email, phone, password_hash, salt):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, phone, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, phone, password_hash, salt, now_iso()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_report(
    user_id,
    patient_name,
    patient_age,
    patient_gender,
    symptoms_extracted,
    predicted_disease,
    urgency,
    specialist,
    confidence,
    medicines,
    vitals,
    transcript,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports
        (user_id, patient_name, patient_age, patient_gender, symptoms_extracted,
         predicted_disease, urgency, specialist, confidence, medicines, vitals, transcript, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
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
            now_iso(),
        ),
    )
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def list_reports(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, patient_name, patient_age, patient_gender, predicted_disease,
               urgency, specialist, confidence, created_at
        FROM reports WHERE user_id = ? ORDER BY id DESC
        """,
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_report(report_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    raw_medicines = json.loads(data["medicines"]) if data["medicines"] else {"medicines": [], "home_remedies": []}
    if isinstance(raw_medicines, list):
        raw_medicines = {"medicines": raw_medicines, "home_remedies": []}
    data["medicines"] = raw_medicines.get("medicines", [])
    data["home_remedies"] = raw_medicines.get("home_remedies", [])
    data["vitals"] = json.loads(data["vitals"]) if data["vitals"] else {}
    data["transcript"] = json.loads(data["transcript"]) if data["transcript"] else []
    return data


def list_medications(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, predicted_disease, urgency, medicines, created_at
        FROM reports WHERE user_id = ? ORDER BY id DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        raw = json.loads(r["medicines"]) if r["medicines"] else {"medicines": [], "home_remedies": []}
        if isinstance(raw, list):
            raw = {"medicines": raw, "home_remedies": []}
        for category, entries in (("medicine", raw.get("medicines", [])), ("home_remedy", raw.get("home_remedies", []))):
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
