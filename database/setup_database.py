import sqlite3

# Kết nối tới database (sẽ tự động tạo file nếu chưa có)
conn = sqlite3.connect('2fa_database.db')
cursor = conn.cursor()


#Câu lệnh SQL để tạo bảng
# - id: Khóa chính, tự động tăng
# - username: Tên người dùng, là duy nhất (không thể trùng)
# - secret_key: Chuỗi Base32 chứa secret key cho 2FA
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    secret_key TEXT NOT NULL
)
''')

conn.commit()
conn.close()
