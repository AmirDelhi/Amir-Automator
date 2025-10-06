import sqlite3
import hashlib
import secrets

def get_db_connection():
    """Get database connection - SIMPLE AND RELIABLE"""
    conn = sqlite3.connect('automations.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables - MINIMAL AND SAFE"""
    conn = None
    try:
        conn = get_db_connection()
        
        # ONLY TWO ESSENTIAL TABLES - minimal setup
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, 
            description TEXT, 
            user_prompt TEXT, 
            ai_generated_code TEXT,
            status TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

def hash_password(password):
    """Hash a password for storing"""
    try:
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${password_hash}"
    except Exception:
        return None

def verify_password(stored_hash, provided_password):
    """Verify a stored password against one provided by user"""
    try:
        if not stored_hash or '$' not in stored_hash:
            return False
        salt, stored_hashed = stored_hash.split('$', 1)
        computed_hash = hashlib.sha256((salt + provided_password).encode()).hexdigest()
        return computed_hash == stored_hashed
    except Exception:
        return False

def create_user(email, name, password):
    """Create a new user with password"""
    conn = None
    try:
        conn = get_db_connection()
        password_hash = hash_password(password)
        if not password_hash:
            return False
            
        conn.execute(
            "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)", 
            (email, name, password_hash)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # User already exists
    except Exception as e:
        print(f"User creation error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return user
    except Exception as e:
        print(f"Get user error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def verify_user_login(email, password):
    """Verify user login credentials"""
    try:
        user = get_user_by_email(email)
        if user and verify_password(user['password_hash'], password):
            return user
        return None
    except Exception as e:
        print(f"Login verification error: {e}")
        return None
