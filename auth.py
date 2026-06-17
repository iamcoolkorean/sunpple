import json
import hashlib
from pathlib import Path
from datetime import datetime

USERS_FILE = "data/users.json"

def _load_users():
    if not Path(USERS_FILE).exists():
        Path("data").mkdir(exist_ok=True)
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_users(users):
    Path("data").mkdir(exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(user_id, password, name):
    users = _load_users()
    if user_id in users:
        return False
    users[user_id] = {
        "password": _hash_password(password),
        "name": name,
        "messages": [],
        "created_at": str(datetime.now())
    }
    _save_users(users)
    return True

def authenticate(user_id, password):
    users = _load_users()
    if user_id not in users:
        return None
    if users[user_id]["password"] == _hash_password(password):
        return users[user_id]
    return None

def get_user_data(user_id):
    users = _load_users()
    return users.get(user_id)

def save_user_data(user_id, data):
    users = _load_users()
    if user_id in users:
        users[user_id].update(data)
        _save_users(users)
