import sqlite3

conn = sqlite3.connect('2fa_database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    secret_key TEXT NOT NULL
)
''')

print("Create database '2fa_database.db' and table 'users' successfully!")

conn.commit()
conn.close()
