import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

USER_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, 'r') as f:
        return json.load(f)

def save_user(username, password, email='', phone=''):
    users = load_users()
    users[username] = {
        'password': generate_password_hash(password),
        'email': email,
        'phone': phone
    }
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

def verify_user(username, password):
    users = load_users()
    if username not in users:
        return False
    return check_password_hash(users[username]['password'], password)