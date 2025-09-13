import sqlite3
import os

def setup_database():
    """Thiết lập database với đầy đủ các bảng và trường cần thiết"""
    
    # Đảm bảo thư mục tồn tại
    os.makedirs('database', exist_ok=True)
    
    # Kết nối tới database
    conn = sqlite3.connect('database/2fa_database.db')
    cursor = conn.cursor()

    # Tạo bảng users với đầy đủ thông tin
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        secret_key TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')

    # Tạo bảng otp_attempts để theo dõi các lần xác thực OTP
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS otp_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        otp_code TEXT,
        is_success BOOLEAN,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database setup completed successfully!")

if __name__ == "__main__":
    setup_database()