import sqlite3
import hashlib
import secrets

def get_db_connection():
    """Get database connection - ABSOLUTELY SIMPLE"""
    conn = sqlite3.connect('automations.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database - ONLY ONE SIMPLE TABLE"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            name TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database ready")

def create_user(email, name):
    """Simple user creation - no password for now"""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO users (email, name) VALUES (?, ?)", 
        (email, name)
    )
    conn.commit()
    conn.close()
    return True

def get_user_by_email(email):
    """Simple user retrieval"""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", 
        (email,)
    ).fetchone()
    conn.close()
    return user
