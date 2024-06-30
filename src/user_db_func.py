import sqlite3
import bcrypt


# Initializing the DataBase
def init_db():
    conn = sqlite3.connect('../USER.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# Function to hash a password
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


# Method used to get user data from database
def get_user(username):
    conn = sqlite3.connect('../USER.db')
    c = conn.cursor()
    c.execute('''
        SELECT username FROM users
        WHERE username = ?
        ORDER BY id DESC LIMIT 1
    ''', (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# Method to store a new user with hashed password
def store_user(username, password):
    conn = sqlite3.connect('../USER.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print("User registered successfully.")
    except sqlite3.IntegrityError:
        print("Username already exists.")
    conn.close()


# Method to verify the user's password
def verify_password(username, password):
    conn = sqlite3.connect('../USER.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()

    if result is None:
        print("User not found.")
        return False

    stored_hashed_password = result[0]
    if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        print("Password is correct.")
        return True
    else:
        print("Password is incorrect.")
        return False


# Test
"""if __name__ == "__main__":
    init_db()
    store_user('john_doe', 'securepassword123')
    print(verify_password('john_doe', 'securepassword123'))
    print(verify_password('john_doe', 'wrongpassword'))"""
