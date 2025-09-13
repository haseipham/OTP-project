import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash #Password hashing (for security)
# Used in: backend/app.py, backend/api_v2.py
from datetime import datetime

DATABASE_FILE = 'database/2fa_database.db'

def get_db_connection():
    """Kết nối đến database"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Trả về kết quả dạng dictionary
    return conn

def add_new_user(username: str, password: str, email: str = '', phone: str = '') -> tuple[bool, str]:
    """Thêm user mới vào database"""
    
    # Chỉ dành cho mục đích tạo secret key random (không dùng cho mục đích bảo mật)
    import pyotp
    secret = pyotp.random_base32()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Hash password trước khi lưu
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            """INSERT INTO users (username, password, email, phone, secret_key) 
               VALUES (?, ?, ?, ?, ?)""",
            (username, hashed_password, email, phone, secret)
        )
        conn.commit()
        print(f"User '{username}' added successfully.")
        return (True, secret)
    except sqlite3.IntegrityError:
        error_message = f"Error: User '{username}' already exists."
        print(error_message)
        return (False, error_message)
    except Exception as e:
        error_message = f"Error adding user: {str(e)}"
        print(error_message)
        return (False, error_message)
    finally:
        conn.close()

def get_user_secret(username: str) -> str | None:
    """Lấy secret key của user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT secret_key FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result['secret_key']
    
    print(f"User '{username}' not found in the database.")
    return None

def verify_user_credentials(username: str, password: str) -> bool:
    """Xác thực thông tin đăng nhập của user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and check_password_hash(result['password'], password):
        # Cập nhật thời gian đăng nhập cuối
        update_last_login(username)
        return True
    
    return False

def update_last_login(username: str):
    """Cập nhật thời gian đăng nhập cuối cùng"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE username = ?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username)
    )
    conn.commit()
    conn.close()

def log_otp_attempt(user_id: int, otp_code: str, is_success: bool):
    """Ghi log attempt OTP"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO otp_attempts (user_id, otp_code, is_success) VALUES (?, ?, ?)",
        (user_id, otp_code, is_success)
    )
    conn.commit()
    conn.close()

def get_user_id(username: str) -> int | None:
    """Lấy ID của user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result['id']
    
    return None

def user_exists(username: str) -> bool:
    """Kiểm tra user có tồn tại không"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result is not None

# Chạy thiết lập database khi import module
if not os.path.exists(DATABASE_FILE):
    from . import setup_database
    setup_database.setup_database()