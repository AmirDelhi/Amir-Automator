import sqlite3
from contextlib import contextmanager

@contextmanager 
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect('automations.db')
    conn.row_factory = sqlite3.Row  # Get rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database with all tables"""
    with get_db() as db:
        # Your existing automations table
        db.execute("""CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, 
            user_prompt TEXT, ai_generated_code TEXT,
            status TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add users table
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add user_automations table
        db.execute("""CREATE TABLE IF NOT EXISTS user_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            automation_name TEXT,
            automation_data TEXT,
            status TEXT DEFAULT 'active',
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        print("✅ Database initialized successfully!")
