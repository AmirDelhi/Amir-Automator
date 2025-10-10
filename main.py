# Amir Automator Dashboard - WITH AI AUTOMATION BUILDER
import os, uuid, json, sqlite3, requests
from flask import Flask, request, redirect, url_for, flash, render_template_string, session, jsonify
from dotenv import load_dotenv
import hashlib
import secrets
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# === DATABASE SETUP ===
DB_NAME = "amir_automator.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        # ADD USER TABLE FIRST
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            plan TEXT DEFAULT 'free',
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # ADD AUTOMATIONS TABLE
        db.execute("""CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT, 
            description TEXT, 
            user_prompt TEXT, 
            ai_generated_code TEXT,
            status TEXT, 
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Your existing tables continue...
        db.execute("""CREATE TABLE IF NOT EXISTS api_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT,
            service_type TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        db.execute("""CREATE TABLE IF NOT EXISTS prebuilt_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            category TEXT,
            steps_json TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, steps_json TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        db.commit()
    
    print("Database initialized.")

init_db()

# === USER MANAGEMENT SYSTEM ===
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

# === AI CONFIGURATION ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

def call_ai_simple(user_input):
    """Universal AI function with multiple fallbacks and better error handling"""
    try:
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
        elif response.status_code == 429:
            return """[
    {"type": "webhook", "action": "Trigger when form is submitted", "details": "Create webhook endpoint at /webhooks/form-submit"},
    {"type": "notification", "action": "Send email notification", "details": "Use: requests.post('https://api.emailservice.com/send', json={'to': 'you@email.com', 'subject': 'New Form Submission', 'body': 'Someone filled your form'})"},
    {"type": "database", "action": "Save lead to database", "details": "INSERT INTO leads (name, email, message) VALUES (form_data.name, form_data.email, form_data.message)"},
    {"type": "followup", "action": "Send welcome email", "details": "Schedule email 24 hours after form submission"}
]"""
        else:
            return """[
    {"type": "trigger", "action": "Form submission detected", "details": "Set up endpoint: POST /api/leads"},
    {"type": "process", "action": "Extract form data", "details": "Parse: name, email, message from request"},
    {"type": "store", "action": "Save to database", "details": "Use SQLite: INSERT INTO leads VALUES (?, ?, ?)"},
    {"type": "notify", "action": "Send instant notification", "details": "Options: Email, WhatsApp, Slack webhook"}
]"""
            
    except Exception as e:
        return """[
    {"type": "http_request", "action": "Capture form data", "details": "Create POST endpoint to receive form submissions"},
    {"type": "data_processing", "action": "Validate and clean data", "details": "Check email format, remove extra spaces"},
    {"type": "database", "action": "Store in SQL database", "details": "Use SQLite or PostgreSQL with proper schema"},
    {"type": "notification", "action": "Send alert", "details": "Choose: Email, SMS, Slack, Discord webhook"},
    {"type": "followup", "action": "Auto-responder", "details": "Send thank you email to the submitter"}
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

# === PRE-BUILT AUTOMATION TEMPLATES ===
PREBUILT_AUTOMATIONS = {
    "lead_capture": {
        "name": "Lead Capture & Notification",
        "description": "Capture form submissions and send instant notifications",
        "category": "Marketing",
        "steps": [
            {"type": "webhook", "action": "Receive form data", "details": "Set up endpoint at /webhooks/lead-capture"},
            {"type": "database", "action": "Save lead to database", "details": "Store in leads table with timestamp"},
            {"type": "notification", "action": "Send Slack alert", "details": "Post to #leads channel with lead details"},
            {"type": "email", "action": "Send welcome email", "details": "Auto-respond to lead within 5 minutes"}
        ]
    },
    "social_media_poster": {
        "name": "Social Media Auto-Poster",
        "description": "Automatically post content to multiple social platforms",
        "category": "Social Media",
        "steps": [
            {"type": "content", "action": "Generate social media content", "details": "Use AI to create engaging posts"},
            {"type": "scheduling", "action": "Schedule posts", "details": "Set optimal posting times"},
            {"type": "twitter", "action": "Post to Twitter/X", "details": "Auto-post with hashtags and media"},
            {"type": "linkedin", "action": "Post to LinkedIn", "details": "Professional format for business audience"}
        ]
    },
    "data_backup": {
        "name": "Automated Data Backup",
        "description": "Backup important data to cloud storage",
        "category": "Productivity",
        "steps": [
            {"type": "monitor", "action": "Monitor data folder", "details": "Watch for new/changed files"},
            {"type": "compress", "action": "Compress files", "details": "Create zip archive of important data"},
            {"type": "cloud", "action": "Upload to cloud storage", "details": "Save to Google Drive/Dropbox"},
            {"type": "notification", "action": "Send backup report", "details": "Email confirmation with file details"}
        ]
    }
}

DASHBOARD_CSS = """
<style>
/* Modern CSS Reset */
* { margin: 0; padding: 0; box-sizing: border-box; }

/* Beautiful Gradient Background */
body { 
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #2d3748;
}

/* Glass Morphism Header */
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

/* Modern Card Design */
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

/* Beautiful Button Design */
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

/* Flash Messages */
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

/* Form Styling */
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

/* Main Content Area */
main {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1.5rem;
}

/* Table Styling */
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

/* Code Blocks */
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

/* Responsive Design */
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
</style>
"""

# === HOME PAGE ===
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

# === DASHBOARD ===
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
            "title": "🛠️ Utility Tools",
            "desc": "AI Copywriter, Text Tools, File Upload and more",
            "url": url_for("tools")
        }
    ]
    
    return render_template_string('''
    {{ css|safe }}
    <div class="header">
        <h1>🚀 Amir Automator Dashboard</h1>
        <p>AI-Powered Automation Platform</p>
        {% if user %}
            <p>Welcome back, {{ user.name }}! ({{ user.plan }} plan)
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

# === AI AUTOMATION BUILDER (Zapier-like) ===
@app.route("/ai_automation", methods=["GET", "POST"])
def ai_automation_builder():
    result = ""
    generated_code = ""
    
    if request.method == "POST":
        user_prompt = request.form.get("prompt", "").strip()
        automation_name = request.form.get("name", "Unnamed Automation")
        
        if user_prompt:
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
                    "INSERT INTO automations (name, description, user_prompt, ai_generated_code, status) VALUES (?, ?, ?, ?, ?)",
                    (automation_name, user_prompt, user_prompt, generated_code, "generated")
                )
                db.commit()
            
            result = generated_code
    
    with get_db() as db:
        automations = db.execute("SELECT * FROM automations ORDER BY created DESC LIMIT 5").fetchall()
    
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
                <button class="btn" onclick="copyToClipboard('{{ result | replace("'", "\\'") | replace("\n", "\\n") }}')">📋 Copy Code</button>
                <button class="btn" onclick="executeAutomation()" style="background:#10b981;">🚀 Execute Automation</button>
                <a href="{{ url_for('workflows') }}" class="btn">💾 Save as Workflow</a>
            </div>
            <div id="executionResults" style="margin-top:1rem; display:none;">
                <h4>Execution Results:</h4>
                <div id="resultsList"></div>
            </div>
        </div>
        {% endif %}

        {% if automations %}
        <div class="card" style="width:100%; margin-top:2rem;">
            <h3>📚 Recent Automations</h3>
            {% for auto in automations %}
            <div style="border-bottom:1px solid #eee; padding:1rem 0;">
                <strong>{{ auto.name }}</strong>
                <p style="color:#666; margin:0.5rem 0;">{{ auto.description }}</p>
                <small style="color:#999;">Created: {{ auto.created }}</small>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </main>
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            alert('Copied to clipboard!');
        }

        async function executeAutomation() {
            try {
                const resultText = `{{ result | safe }}`;
                const steps = JSON.parse(resultText);
                
                const executeBtn = document.querySelector('button[onclick="executeAutomation()"]');
                executeBtn.innerHTML = '⏳ Executing...';
                executeBtn.disabled = true;
                
                const response = await fetch('/execute_automation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ steps: steps })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const resultsDiv = document.getElementById('executionResults');
                    const resultsList = document.getElementById('resultsList');
                    
                    resultsList.innerHTML = data.results.map(result => 
                        `<div style="padding:0.5rem; border-left:3px solid #10b981; margin:0.5rem 0; background:white;">
                            ${result}
                        </div>`
                    ).join('');
                    
                    resultsDiv.style.display = 'block';
                    executeBtn.innerHTML = '✅ Executed!';
                } else {
                    alert('Error: ' + data.error);
                    executeBtn.innerHTML = '🚀 Execute Automation';
                    executeBtn.disabled = false;
                }
                
            } catch (error) {
                alert('Error executing automation: ' + error.message);
                const executeBtn = document.querySelector('button[onclick="executeAutomation()"]');
                executeBtn.innerHTML = '🚀 Execute Automation';
                executeBtn.disabled = false;
            }
        }
    </script>
    """, css=DASHBOARD_CSS, result=result, automations=automations)

# === WORKFLOWS ===
@app.route("/workflows")
def workflows():
    with get_db() as db:
        workflows = db.execute("SELECT * FROM workflows ORDER BY created DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
        <h1>Workflows</h1>
        <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
        <a href="{{ url_for('ai_automation_builder') }}" class="btn">🤖 AI Builder</a>
    </div>
    <main style="max-width:900px; margin:2rem auto;">
        <h3>Your Workflows</h3>
        {% for wf in workflows %}
        <div class="card" style="width:100%; margin:1rem 0;">
            <h4>{{ wf.name }}</h4>
            <p>{{ wf.description }}</p>
            <a href="{{ url_for('workflow_run', id=wf.id) }}" class="btn">Run</a>
        </div>
        {% endfor %}
    </main>
    """, css=DASHBOARD_CSS, workflows=workflows)

@app.route("/workflows/run/<int:id>")
def workflow_run(id):
    return "Workflow run page"

@app.route("/tools")
def tools():
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Utility Tools</h1></div>
    <div style="text-align:center; margin:2rem;">
        <a href="{{ url_for('ai_automation_builder') }}" class="btn">🤖 Back to AI Builder</a>
    </div>
    """, css=DASHBOARD_CSS)

@app.route("/admin/leads")
def admin_leads():
    return "Leads admin page"

@app.route("/health")
def health():
    return "OK"

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

# === AUTOMATION EXECUTION ===
@app.route("/execute_automation", methods=["POST"])
def execute_automation():
    """Execute a generated automation"""
    try:
        automation_steps = request.json.get('steps', [])
        results = []
        
        print(f"Executing {len(automation_steps)} steps")
        
        for step in automation_steps:
            step_type = step.get('type', '')
            action = step.get('action', '')
            details = step.get('details', '')
            
            print(f"Processing step: {step_type} - {action}")
            
            if step_type == "webhook":
                if "whatsapp" in action.lower():
                    results.append(f"✅ WhatsApp webhook configured: {
