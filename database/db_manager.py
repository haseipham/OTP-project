import sqlite3
import pyotp

DATABASE_FILE = '2fa_database.db'

def add_new_user(username: str) -> tuple[bool, str]:
  
    secret = pyotp.random_base32()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, secret_key) VALUES (?, ?)",
            (username, secret)
        )
        conn.commit()
        print(f"User '{username}' added successfully.")
        return (True, secret)
    except sqlite3.IntegrityError:
        error_message = f"Error: User '{username}' already exists."
        print(error_message)
        return (False, error_message)
      
    finally:
        conn.close()

def get_user_secret(username: str) -> str | None:
  
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT secret_key FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]  
    
    print(f"User '{username}' not found in the database.")
    return None
  
