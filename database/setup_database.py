import sqlite3

DATABASE_FILE = '2fa_database.db'

def initialize_database():
    # Kết nối tới database (sẽ tự động tạo file nếu chưa có)
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Câu lệnh SQL để tạo bảng
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        phone_number TEXT,
        password_hash TEXT NOT NULL,
        secret_key TEXT 
    );
    """
    
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()
