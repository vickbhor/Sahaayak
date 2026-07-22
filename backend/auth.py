import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
import database

JWT_SECRET = os.getenv("JWT_SECRET", "sahaayak-dev-secret-change-this-please-32bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return pwd_hash, salt


def verify_password(password, salt, expected_hash):
    pwd_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pwd_hash, expected_hash)


def create_token(user_id, email):
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    user = database.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
