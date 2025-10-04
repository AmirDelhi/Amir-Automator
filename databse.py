import sqlite3
from contextlib import contextmanager
import hashlib
import secrets

@contextmanager 
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect('automations.db')
    conn.row_factory = sqlite3.Row  # Get rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password):
    """Hash a password for storing"""
    salt = secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"

def verify_password(stored_hash, provided_password):
    """Verify a stored password against one provided by user"""
    if not stored_hash or '$' not in stored_hash:
        return False
    salt, stored_hashed = stored_hash.split('$', 1)
    computed_hash = hashlib.sha256((salt + provided_password).encode()).hexdigest()
    return computed_hash == stored_hashed

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
        
        # API integrations table
        db.execute("""CREATE TABLE IF NOT EXISTS api_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT,
            service_type TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Pre-built automations table
        db.execute("""CREATE TABLE IF NOT EXISTS prebuilt_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            category TEXT,
            steps_json TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Updated users table with password hash
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # User automations table
        db.execute("""CREATE TABLE IF NOT EXISTS user_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            automation_name TEXT,
            automation_data TEXT,
            status TEXT DEFAULT 'active',
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # Leads table
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Workflows table
        db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, steps_json TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        print("✅ Database initialized successfully!")

def create_user(email, name, password):
    """Create a new user with password"""
    with get_db() as db:
        try:
            password_hash = hash_password(password)  # Hash the password
            db.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)", 
                (email, name, password_hash)
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # User already exists

def get_user_by_email(email):
    """Get user by email"""
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", 
            (email,)
        ).fetchone()
        return user

def get_user_by_id(user_id):
    """Get user by ID"""
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", 
            (user_id,)
        ).fetchone()
        return user

def verify_user_login(email, password):
    """Verify user login credentials"""
    user = get_user_by_email(email)
    if user and verify_password(user['password_hash'], password):
        return user
    return None
