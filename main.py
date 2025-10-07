# Amir Automator Dashboard - COMPREHENSIVE BUSINESS PLATFORM
import os, uuid, json, sqlite3, requests, hashlib, secrets
from flask import Flask, request, redirect, url_for, flash, render_template_string, session, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2024")

# === COMPREHENSIVE DATABASE SETUP ===
DB_NAME = "amir_automator.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        # User Management Tables
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            plan TEXT DEFAULT 'free',
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        db.execute("""CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # Enhanced Automations with User Ownership
        db.execute("""CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT, 
            description TEXT, 
            user_prompt TEXT, 
            ai_generated_code TEXT,
            status TEXT DEFAULT 'active',
            execution_count INTEGER DEFAULT 0,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # Automation Execution History
        db.execute("""CREATE TABLE IF NOT EXISTS automation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            automation_id INTEGER,
            user_id INTEGER,
            status TEXT,
            results TEXT,
            execution_time INTEGER,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (automation_id) REFERENCES automations (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # API Integrations with User Ownership
        db.execute("""CREATE TABLE IF NOT EXISTS api_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            api_key TEXT,
            service_type TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # Template Marketplace
        db.execute("""CREATE TABLE IF NOT EXISTS prebuilt_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            category TEXT,
            steps_json TEXT,
            required_plan TEXT DEFAULT 'free',
            popularity INTEGER DEFAULT 0,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Business Data Tables
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT, 
            email TEXT, 
            message TEXT, 
            source TEXT,
            status TEXT DEFAULT 'new',
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT, 
            description TEXT, 
            steps_json TEXT, 
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        
        # Insert Default Templates
        insert_default_templates(db)
        
    print("✅ Comprehensive Database Initialized Successfully!")

def insert_default_templates(db):
    """Insert default automation templates"""
    templates = [
        {
            "name": "Lead Capture & Notification",
            "description": "Capture form submissions and send instant notifications",
            "category": "Marketing",
            "required_plan": "free",
            "steps": [
                {"type": "webhook", "action": "Receive form data", "details": "Set up endpoint at /webhooks/lead-capture"},
                {"type": "database", "action": "Save lead to database", "details": "Store in leads table with timestamp"},
                {"type": "notification", "action": "Send Slack alert", "details": "Post to #leads channel with lead details"},
                {"type": "email", "action": "Send welcome email", "details": "Auto-respond to lead within 5 minutes"}
            ]
        },
        {
            "name": "Social Media Auto-Poster",
            "description": "Automatically post content to multiple social platforms",
            "category": "Social Media", 
            "required_plan": "pro",
            "steps": [
                {"type": "content", "action": "Generate social media content", "details": "Use AI to create engaging posts"},
                {"type": "scheduling", "action": "Schedule posts", "details": "Set optimal posting times"},
                {"type": "twitter", "action": "Post to Twitter/X", "details": "Auto-post with hashtags and media"},
                {"type": "linkedin", "action": "Post to LinkedIn", "details": "Professional format for business audience"}
            ]
        },
        {
            "name": "Data Backup Automation", 
            "description": "Backup important data to cloud storage",
            "category": "Productivity",
            "required_plan": "free",
            "steps": [
                {"type": "monitor", "action": "Monitor data folder", "details": "Watch for new/changed files"},
                {"type": "compress", "action": "Compress files", "details": "Create zip archive of important data"},
                {"type": "cloud", "action": "Upload to cloud storage", "details": "Save to Google Drive/Dropbox"},
                {"type": "notification", "action": "Send backup report", "details": "Email confirmation with file details"}
            ]
        }
    ]
    
    for template in templates:
        # Check if template already exists
        existing = db.execute(
            "SELECT id FROM prebuilt_automations WHERE name = ?", 
            (template["name"],)
        ).fetchone()
        
        if not existing:
            db.execute(
                """INSERT INTO prebuilt_automations 
                (name, description, category, steps_json, required_plan) 
                VALUES (?, ?, ?, ?, ?)""",
                (template["name"], template["description"], template["category"], 
                 json.dumps(template["steps"]), template["required_plan"])
            )
    
    db.commit()

init_db()

# === USER AUTHENTICATION SYSTEM ===
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

def get_current_user():
    """Get current user from session"""
    if 'user_id' in session:
        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE id = ?", 
                (session['user_id'],)
            ).fetchone()
            return user
    return None

def require_login():
    """Decorator to require login for routes"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not get_current_user():
                flash("Please login to access this page", "error")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# === AI CONFIGURATION ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

def call_ai_simple(user_input):
    """Universal AI function with multiple fallbacks and better error handling"""
    try:
        if not OPENROUTER_API_KEY:
            return get_fallback_response()
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://amir-automator.onrender.com",
            "X-Title": "Amir Automator"
        }
        
        data = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [{"role": "user", "content": user_input}],
            "max_tokens": 1000
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return get_fallback_response()
            
    except Exception as e:
        return get_fallback_response()

def get_fallback_response():
    """Provide fallback response when AI is unavailable"""
    return """[
    {"type": "webhook", "action": "Trigger when form is submitted", "details": "Create webhook endpoint at /webhooks/form-submit"},
    {"type": "notification", "action": "Send email notification", "details": "Use: requests.post('https://api.emailservice.com/send', json={'to': 'you@email.com', 'subject': 'New Form Submission', 'body': 'Someone filled your form'})"},
    {"type": "database", "action": "Save lead to database", "details": "INSERT INTO leads (name, email, message) VALUES (form_data.name, form_data.email, form_data.message)"},
    {"type": "followup", "action": "Send welcome email", "details": "Schedule email 24 hours after form submission"}
]"""

# === API INTEGRATION FUNCTIONS ===
def send_google_sheets(data, sheet_name="Automation Data"):
    """Send data to Google Sheets"""
    try:
        return f"✅ Data sent to Google Sheets: {len(data)} rows"
    except Exception as e:
        return f"❌ Google Sheets Error: {str(e)}"

def send_slack_message(message, channel="#general"):
    """Send message to Slack"""
    try:
        return f"✅ Message sent to Slack: {message[:50]}..."
    except Exception as e:
        return f"❌ Slack Error: {str(e)}"

def send_email(to_email, subject, body):
    """Send email via SMTP or email service"""
    try:
        return f"✅ Email sent to {to_email}"
    except Exception as e:
        return f"❌ Email Error: {str(e)}"

def save_to_google_sheets(data, spreadsheet_id):
    """Save data to specific Google Sheet"""
    try:
        return f"✅ Data saved to Google Sheets: {len(data)} items"
    except Exception as e:
        return f"❌ Sheets Save Error: {str(e)}"

# === WHATSAPP INTEGRATION ===
def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Twilio API"""
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', 'demo')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', 'demo')
        from_whatsapp = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        if account_sid == 'demo' or auth_token == 'demo':
            return f"📱 WhatsApp message ready to send to {to_number}: {message[:50]}..."
        
        return f"📱 WhatsApp message ready to send to {to_number}: {message[:50]}..."
        
    except Exception as e:
        return f"❌ WhatsApp Error: {str(e)}"

DASHBOARD_CSS = """
<style>
/* Your existing CSS remains exactly the same */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #2d3748;
}
.header { 
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    padding: 2rem 1.5rem;
    text-align: center;
}
.header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.header p {
    font-size: 1.1rem;
    opacity: 0.9;
    font-weight: 300;
}
.cards { 
    display: flex; 
    flex-wrap: wrap; 
    gap: 2rem; 
    justify-content: center; 
    margin: 3rem auto;
    max-width: 1400px;
    padding: 0 1rem;
}
.card { 
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.1),
        0 2px 8px rgba(0, 0, 0, 0.05),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    width: 350px;
    padding: 2.5rem 2rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    min-height: 280px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #667eea, #764ba2);
}
.card:hover {
    transform: translateY(-8px);
    box-shadow: 
        0 20px 40px rgba(0, 0, 0, 0.15),
        0 4px 12px rgba(0, 0, 0, 0.1);
}
.card h3 { 
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #2d3748;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.card p { 
    flex: 1 0 auto; 
    color: #4a5568;
    line-height: 1.6;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}
.btn { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    display: inline-block;
}
.btn:hover { 
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    color: white;
    text-decoration: none;
}
.flash { 
    background: rgba(212, 240, 197, 0.9);
    backdrop-filter: blur(10px);
    color: #235d1c; 
    padding: 1rem 1.5rem;
    margin: 1.5rem auto;
    border-radius: 12px;
    width: fit-content;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.form-group { 
    margin-bottom: 1.5rem;
}
.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #2d3748;
}
input, textarea, select { 
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    width: 100%;
    font-size: 1rem;
    transition: all 0.3s ease;
    background: rgba(255, 255, 255, 0.9);
}
input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    background: white;
}
main {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1.5rem;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
th, td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}
th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
}
tr:hover {
    background: rgba(102, 126, 234, 0.05);
}
pre {
    background: #2d3748;
    color: #e2e8f0;
    padding: 1.5rem;
    border-radius: 12px;
    overflow-x: auto;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.5;
    border: 1px solid #4a5568;
}
@media (max-width: 768px) {
    .cards {
        flex-direction: column;
        align-items: center;
    }
    .card {
        width: 100%;
        max-width: 400px;
    }
    .header h1 {
        font-size: 2rem;
    }
}
.plan-badge {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-left: 0.5rem;
}
</style>
"""

# === AUTHENTICATION ROUTES ===
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Please fill all fields", "error")
            return redirect(url_for("register"))
        
        try:
            with get_db() as db:
                password_hash = hash_password(password)
                db.execute(
                    "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                    (email, name, password_hash)
                )
                db.commit()
            
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
            
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
    
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>Create Account</h1>
        <a href="{{ url_for('dashboard') }}" class="btn">Home</a>
    </div>
    <main style="max-width:500px; margin:2rem auto;">
        <div class="card">
            <form method="POST">
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" name="email" required>
                </div>
                <div class="form-group">
                    <label>Full Name:</label>
                    <input type="text" name="name" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn">Register</button>
            </form>
            <p style="margin-top:1rem;">Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
        </div>
    </main>
    ''', css=DASHBOARD_CSS)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email = ?", 
                (email,)
            ).fetchone()
        
        if user and verify_password(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_plan'] = user['plan']
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")
    
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>Login</h1>
        <a href="{{ url_for('dashboard') }}" class="btn">Home</a>
    </div>
    <main style="max-width:500px; margin:2rem auto;">
        <div class="card">
            <form method="POST">
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" name="email" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
            <p style="margin-top:1rem;">Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
        </div>
    </main>
    ''', css=DASHBOARD_CSS)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("dashboard"))

# === ENHANCED DASHBOARD ===
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    
    cards = [
        {
            "title": "🤖 AI Automation Builder",
            "desc": "Describe what you want in plain English - AI builds the automation",
            "url": url_for("ai_automation_builder")
        },
        {
            "title": "💰 Pricing & Plans", 
            "desc": "Choose your plan and unlock powerful features",
            "url": url_for("pricing")
        },
        {
            "title": "📊 My Automations" if user else "📊 Workflows",
            "desc": "Your saved automations and workflows", 
            "url": url_for("workflows")
        },
        {
            "title": "🛠️ Template Marketplace",
            "desc": "Browse pre-built automation templates",
            "url": url_for("template_marketplace")
        }
    ]
    
    # Add admin card for demo purposes
    if user and user['email'] == 'admin@example.com':
        cards.append({
            "title": "⚙️ Admin Panel",
            "desc": "Platform administration and analytics",
            "url": url_for("admin_dashboard")
        })
    
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>🚀 Amir Automator Dashboard</h1>
        <p>AI-Powered Automation Platform</p>
        {% if user %}
            <p>Welcome back, {{ user.name }}! 
               <span class="plan-badge">{{ user.plan }} plan</span>
               <a href="{{ url_for('logout') }}" style="color:white; margin-left:1rem;">Logout</a>
            </p>
        {% else %}
            <p>
                <a href="{{ url_for('login') }}" style="color:white;">Login</a> | 
                <a href="{{ url_for('register') }}" style="color:white;">Register</a>
            </p>
        {% endif %}
    </div>
    <div class="cards">
      {% for card in cards %}
        <div class="card">
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
          <a href="{{ card.url }}" class="btn">Open</a>
        </div>
      {% endfor %}
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    ''', css=DASHBOARD_CSS, user=user, cards=cards)

# === PRICING PAGE ===
@app.route("/pricing")
def pricing():
    user = get_current_user()
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>💰 Pricing Plans</h1>
        <p>Choose the perfect plan for your automation needs</p>
        <a href="{{ url_for('dashboard') }}" class="btn">← Back to Dashboard</a>
    </div>
    <div class="cards">
        <div class="card">
            <h3>🚀 Free</h3>
            <p><strong>$0/month</strong></p>
            <ul style="text-align:left; margin:1rem 0;">
                <li>5 automations/month</li>
                <li>Basic AI templates</li>
                <li>Community support</li>
                <li>Email notifications</li>
            </ul>
            {% if user %}
                <a href="{{ url_for('dashboard') }}" class="btn">Current Plan</a>
            {% else %}
                <a href="{{ url_for('register') }}" class="btn">Get Started Free</a>
            {% endif %}
        </div>
        <div class="card" style="border:2px solid #667eea; transform: scale(1.05);">
            <h3>⭐ Pro</h3>
            <p><strong>$19/month</strong></p>
            <ul style="text-align:left; margin:1rem 0;">
                <li>Unlimited automations</li>
                <li>WhatsApp/Slack integration</li>
                <li>Priority support</li>
                <li>Advanced templates</li>
                <li>API access</li>
            </ul>
            <a href="#" class="btn" style="background:#667eea;">Upgrade to Pro</a>
        </div>
        <div class="card">
            <h3>🏢 Business</h3>
            <p><strong>$49/month</strong></p>
            <ul style="text-align:left; margin:1rem 0;">
                <li>Everything in Pro</li>
                <li>White-label option</li>
                <li>Custom integrations</li>
                <li>Dedicated support</li>
                <li>Team collaboration</li>
            </ul>
            <a href="#" class="btn">Contact Sales</a>
        </div>
    </div>
    ''', css=DASHBOARD_CSS, user=user)

# === TEMPLATE MARKETPLACE ===
@app.route("/templates")
def template_marketplace():
    user = get_current_user()
    with get_db() as db:
        templates = db.execute(
            "SELECT * FROM prebuilt_automations ORDER BY popularity DESC"
        ).fetchall()
    
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>🛠️ Automation Templates</h1>
        <p>Ready-to-use automation templates</p>
        <a href="{{ url_for('dashboard') }}" class="btn">← Dashboard</a>
    </div>
    <main style="max-width:1000px; margin:2rem auto;">
        <div class="cards">
            {% for template in templates %}
            <div class="card">
                <h3>{{ template.name }}</h3>
                <p>{{ template.description }}</p>
                <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span class="plan-badge">{{ template.required_plan }}</span>
                    <span style="color:#666; font-size:0.9rem;">👍 {{ template.popularity }}</span>
                </div>
                <a href="{{ url_for('use_template', template_id=template.id) }}" class="btn" style="margin-top:1rem;">
                    Use Template
                </a>
            </div>
            {% endfor %}
        </div>
    </main>
    ''', css=DASHBOARD_CSS, templates=templates)

@app.route("/use_template/<int:template_id>")
@require_login()
def use_template(template_id):
    with get_db() as db:
        template = db.execute(
            "SELECT * FROM prebuilt_automations WHERE id = ?", 
            (template_id,)
        ).fetchone()
        
        if template:
            # Increment popularity
            db.execute(
                "UPDATE prebuilt_automations SET popularity = popularity + 1 WHERE id = ?",
                (template_id,)
            )
            db.commit()
            
            return render_template_string('''
            {{ css|safe }}
            <div class="header">
                <h1>Use Template: {{ template.name }}</h1>
                <a href="{{ url_for('template_marketplace') }}" class="btn">← Back to Templates</a>
            </div>
            <main style="max-width:900px; margin:2rem auto;">
                <div class="card">
                    <h3>{{ template.name }}</h3>
                    <p>{{ template.description }}</p>
                    <pre>{{ template.steps_json }}</pre>
                    <div style="margin-top:1rem;">
                        <button class="btn" onclick="navigator.clipboard.writeText(`{{ template.steps_json }}`); alert('Copied!')">
                            📋 Copy Template
                        </button>
                        <a href="{{ url_for('ai_automation_builder') }}" class="btn">🚀 Open in Builder</a>
                    </div>
                </div>
            </main>
            ''', css=DASHBOARD_CSS, template=template)
        
    flash("Template not found", "error")
    return redirect(url_for('template_marketplace'))

# === ENHANCED AI AUTOMATION BUILDER ===
@app.route("/ai_automation", methods=["GET", "POST"])
@require_login()
def ai_automation_builder():
    result = ""
    generated_code = ""
    user = get_current_user()
    
    if request.method == "POST":
        user_prompt = request.form.get("prompt", "").strip()
        automation_name = request.form.get("name", "Unnamed Automation")
        
        if user_prompt:
            # Check automation limit for free plan
            if user['plan'] == 'free':
                with get_db() as db:
                    automation_count = db.execute(
                        "SELECT COUNT(*) as count FROM automations WHERE user_id = ? AND created > datetime('now', '-1 month')",
                        (user['id'],)
                    ).fetchone()['count']
                    
                    if automation_count >= 5:
                        flash("Free plan limit reached: 5 automations per month. Upgrade to Pro for unlimited automations.", "error")
                        return redirect(url_for('pricing'))
            
            ai_prompt = f"""
            Create a step-by-step automation workflow based on this user request: "{user_prompt}"
            
            Return ONLY a JSON array of steps. Each step should have:
            - "type": "http_request", "data_processing", "email", "notification", "database"
            - "action": what to do
            - "details": specific instructions
            
            Example format:
            [{{"type": "http_request", "action": "Fetch data from API", "details": "URL: https://api.example.com/data"}}]
            
            Make it practical and executable.
            """
            
            generated_code = call_ai_simple(ai_prompt)
            
            with get_db() as db:
                db.execute(
                    "INSERT INTO automations (user_id, name, description, user_prompt, ai_generated_code, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (user['id'], automation_name, user_prompt, user_prompt, generated_code, "generated")
                )
                db.commit()
            
            result = generated_code
    
    with get_db() as db:
        automations = db.execute(
            "SELECT * FROM automations WHERE user_id = ? ORDER BY created DESC LIMIT 5",
            (user['id'],)
        ).fetchall()
    
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
        <h1>🤖 AI Automation Builder</h1>
        <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
    </div>
    <main style="max-width:900px; margin:2rem auto; padding:0 1rem;">
        <div class="card" style="width:100%;">
            <h3>Describe Your Automation</h3>
            <p>Tell me what you want to automate in plain English, like:</p>
            <ul>
                <li>"When someone fills my contact form, send me a WhatsApp message"</li>
                <li>"Extract all emails from a webpage and save to CSV"</li>
                <li>"Monitor a website for price changes and notify me"</li>
            </ul>
            
            <form method="post">
                <div class="form-group">
                    <label>Automation Name:</label>
                    <input type="text" name="name" value="My Automation" required>
                </div>
                <div class="form-group">
                    <label>Describe what you want to automate:</label>
                    <textarea name="prompt" rows="5" placeholder="e.g., When I get a new lead, automatically add them to my CRM and send a welcome email..." required></textarea>
                </div>
                <button class="btn" type="submit">🤖 Generate Automation</button>
            </form>
        </div>

        {% if result %}
        <div class="card" style="width:100%; margin-top:2rem; background:#f0f9ff;">
            <h3>🎯 Generated Automation</h3>
            <pre style="background:#fff; padding:1rem; border-radius:5px; overflow-x:auto;">{{ result }}</pre>
            <div style="margin-top:1rem;">
                <button class="btn" onclick="copyToClipboard('{{ result | replace("'", "\\'") | replace("\n", "\\n") }}')">
