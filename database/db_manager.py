# db_manager.py

import sqlite3
import pyotp
# pip install werkzeug (nếu chưa cài)
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_FILE = '2fa_database.db'

def add_new_user(username: str, email: str, password: str, phone_number: str = None) -> tuple[bool, str]:
"""
    Adds a new user to the database.
    Parameters:
        username (str)
        email (str)
        password (str)
        phone_number (str, optional)
    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating success and a message.
"""
    hashed_password = generate_password_hash(password)
  
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, email, phone_number, password_hash) VALUES (?, ?, ?, ?)",
            (username, email, phone_number, hashed_password)
        )
        conn.commit()
        print(f"User '{username}' added successfully.")
        return (True, "REGISTERED SUCCESSFULLY!")
    except sqlite3.IntegrityError:
        error_message = f"Error: Username or Email already exists."
        print(error_message)
        return (False, error_message)
    finally:
        conn.close()

def enable_2fa_for_user(username: str) -> str | None:
"""
    Enables two-factor authentication for the specified user by generating a secret key,
    updating it in the database, and returning the secret key if successful.
    Returns None if the user is not found.
"""
    secret_key = pyotp.random_base32()
  
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET secret_key = ? WHERE username = ?", (secret_key, username))
    
    if cursor.rowcount == 0:
        conn.close()
        print(f"User '{username}' not found to enable 2FA.")
        return None
        
    conn.commit()
    conn.close()

    print(f"Enabled 2FA and created secret key for user '{username}'.")
    return secret_key

def get_user_secret(username: str) -> str | None:
"""
    Retrieve the secret key for two-factor authentication (2FA) for the given username.
    Args:
        username (str): The username whose secret key is to be retrieved.
    Returns:
        str | None: The secret key if found, otherwise None.
"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT secret_key FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
  
    if result:
        return result[0] 
    else:
        print(f"User '{username}' not found in the database.")
        return None

def get_password_hash(username: str) -> str | None:
"""
    Retrieves the password hash for the given username from the database.
    Args:
        username (str): The username to look up.
    Returns:
        str | None: The password hash if the user exists, otherwise None.
"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0] 
    else:
        return None

def update_password(username: str, new_password: str) -> bool:
"""
    Update the password for a given user.
    Parameters:
        username (str): The username of the user whose password is to be updated.
        new_password (str): The new password to set for the user.
    Returns:
        bool: True if the password was updated successfully, False otherwise.
"""
    hashed_password = generate_password_hash(new_password)
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hashed_password, username)
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"Password updated successfully for user '{username}'.")
            return True
        else:
            print(f"User '{username}' not found.")
            return False
    except sqlite3.Error as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        conn.close()

def delete_user(username: str) -> bool:
"""
    Deletes a user from the database by username.
    Args:
        username (str): The username of the user to delete.
    Returns:
        bool: True if the user was deleted successfully, False otherwise.
"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"User '{username}' deleted successfully.")
            return True
        else:
            print(f"User '{username}' not found.")
            return False
    except sqlite3.Error as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()

def get_user_info(username: str) -> dict | None:
"""
    Retrieve user information from the database.
    Parameters:
        username (str): The username of the user to retrieve.
    Returns:
        dict: A dictionary containing 'username', 'email', and 'phone_number' if the user is found.
        None: If the user is not found.
"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT username, email, phone_number FROM users WHERE username = ?",
        (username,)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "username": result[0],
            "email": result[1],
            "phone_number": result[2]
        }
    else:
        print(f"User '{username}' not found.")
        return None
