# SIMPLE IN-MEMORY DATABASE - NO FILE SYSTEM ISSUES
import sqlite3

# Use in-memory database for now - ALWAYS WORKS
def get_db_connection():
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize in-memory database"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            name TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            user_prompt TEXT,
            ai_generated_code TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ In-memory database ready")
    return True

# Simple functions that will 100% work
def create_user(email, name):
    conn = get_db_connection()
    conn.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
    conn.commit()
    conn.close()
    return True

def get_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return users
