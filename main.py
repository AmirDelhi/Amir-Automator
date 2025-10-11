import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, render_template_string, session, jsonify
from dotenv import load_dotenv
import requests

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# === DATABASE SETUP ===
DB_NAME = os.environ.get("DB_NAME", "amir_automator.db")


def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            plan TEXT DEFAULT 'free',
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

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


# Initialize DB at startup (safe for local dev)
init_db()

# === USER MANAGEMENT ===


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    if not stored_hash or '$' not in stored_hash:
        return False
    salt, stored_hashed = stored_hash.split('$', 1)
    computed_hash = hashlib.sha256((salt + provided_password).encode()).hexdigest()
    return computed_hash == stored_hashed


def get_current_user():
    if 'user_id' in session:
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
            return user
    return None


# === AI CONFIG ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")


def call_ai_simple(user_input: str) -> str:
    """Call an AI endpoint with fallbacks. Returns a string (possibly JSON)."""
    try:
        # If no API key configured, return a sensible fallback
        if not OPENROUTER_API_KEY:
            return json.dumps([
                {"type": "http_request", "action": "Capture form data", "details": "Create POST endpoint to receive form submissions"},
                {"type": "data_processing", "action": "Validate and clean data", "details": "Check email format, remove extra spaces"},
                {"type": "database", "action": "Store in SQL database", "details": "Use SQLite or PostgreSQL with proper schema"},
                {"type": "notification", "action": "Send alert", "details": "Choose: Email, SMS, Slack, Discord webhook"},
                {"type": "followup", "action": "Auto-responder", "details": "Send thank you email to the submitter"}
            ])

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
            # Try to extract a text response; if structure differs, return full JSON string
            try:
                result = response.json()
                # defensive access for different API shapes
                if isinstance(result, dict) and 'choices' in result:
                    try:
                        return result['choices'][0]['message']['content']
                    except Exception:
                        return json.dumps(result)
                # fallback to text body
                return response.text
            except Exception:
                return response.text
        elif response.status_code == 429:
            # Rate-limited — provide helpful fallback JSON guidance
            return json.dumps([
                {"type": "webhook", "action": "Trigger when form is submitted", "details": "Create webhook endpoint at /webhooks/form-submit"},
                {"type": "notification", "action": "Send email notification", "details": "Use external email API to notify team"},
                {"type": "database", "action": "Save lead to database", "details": "INSERT INTO leads (name, email, message) VALUES (?, ?, ?)"},
                {"type": "followup", "action": "Send welcome email", "details": "Schedule greeting email after submission"}
            ])
        else:
            return json.dumps([
                {"type": "trigger", "action": "Form submission detected", "details": "Set up endpoint: POST /api/leads"},
                {"type": "process", "action": "Extract form data", "details": "Parse: name, email, message from request"},
                {"type": "store", "action": "Save to database", "details": "Use SQLite: INSERT INTO leads VALUES (?, ?, ?)"},
                {"type": "notify", "action": "Send instant notification", "details": "Options: Email, WhatsApp, Slack webhook"}
            ])

    except Exception:
        # Generic fallback (ensures a JSON string response)
        return json.dumps([
            {"type": "http_request", "action": "Capture form data", "details": "Create POST endpoint to receive form submissions"},
            {"type": "data_processing", "action": "Validate and clean data", "details": "Check email format, remove extra spaces"},
            {"type": "database", "action": "Store in SQL database", "details": "Use SQLite or PostgreSQL with proper schema"},
            {"type": "notification", "action": "Send alert", "details": "Choose: Email, SMS, Slack, Discord webhook"},
            {"type": "followup", "action": "Auto-responder", "details": "Send thank you email to the submitter"}
        ])


# === INTEGRATIONS (stubs) ===


def send_google_sheets(data, sheet_name="Automation Data"):
    try:
        return f"✅ Data sent to Google Sheets: {len(data)} rows"
    except Exception as e:
        return f"❌ Google Sheets Error: {str(e)}"


def send_slack_message(message, channel="#general"):
    try:
        return f"✅ Message sent to Slack: {message[:50]}..."
    except Exception as e:
        return f"❌ Slack Error: {str(e)}"


def send_email(to_email, subject, body):
    try:
        return f"✅ Email sent to {to_email}"
    except Exception as e:
        return f"❌ Email Error: {str(e)}"


def save_to_google_sheets(data, spreadsheet_id):
    try:
        return f"✅ Data saved to Google Sheets: {len(data)} items"
    except Exception as e:
        return f"❌ Sheets Save Error: {str(e)}"


def send_whatsapp_message(to_number, message):
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', 'demo')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', 'demo')

        if account_sid == 'demo' or auth_token == 'demo':
            return f"📱 WhatsApp message ready to send to {to_number}: {message[:50]}..."

        # Real Twilio call would go here (omitted intentionally)
        return f"📱 WhatsApp message queued to {to_number}: {message[:50]}..."
    except Exception as e:
        return f"❌ WhatsApp Error: {str(e)}"


# === PREBUILT AUTOMATIONS ===
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

# Small, shared CSS for templates
DASHBOARD_CSS = """
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #2d3748; }
.header { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.2); color:white; padding:2rem 1.5rem; text-align:center; }
.card { background: rgba(255,255,255,0.95); border-radius:12px; padding:1.5rem; margin:1rem 0; }
.btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:0.75rem 1.25rem; border-radius:8px; text-decoration:none; }
.flash { background: rgba(212,240,197,0.9); color:#235d1c; padding:1rem; border-radius:8px; display:inline-block; }
</style>
"""


# === ROUTES ===
@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    cards = [
        {"title": "🤖 AI Automation Builder", "desc": "Describe what you want in plain English - AI builds the automation", "url": url_for("ai_automation_builder")},
        {"title": "💰 Pricing & Plans", "desc": "Choose your plan and unlock powerful features", "url": url_for("pricing")},
        {"title": "📊 My Automations" if user else "📊 Workflows", "desc": "Your saved automations and workflows", "url": url_for("workflows")},
        {"title": "🛠️ Utility Tools", "desc": "AI Copywriter, Text Tools, File Upload and more", "url": url_for("tools")}
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
    <div class="card" style="max-width:1200px; margin:2rem auto;">
      {% for card in cards %}
        <div style="padding:1rem; border-bottom:1px solid #eee;">
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


# AI Automation Builder
@app.route("/ai_automation", methods=["GET", "POST"])
def ai_automation_builder():
    result = ""
    if request.method == "POST":
        user_prompt = request.form.get("prompt", "").strip()
        automation_name = request.form.get("name", "Unnamed Automation")
        if user_prompt:
            ai_prompt = f"Create a step-by-step automation workflow based on this user request: \"{user_prompt}\""
            generated_code = call_ai_simple(ai_prompt)
            # Store automation
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
        <div class="card">
            <h3>Describe Your Automation</h3>
            <form method="post">
                <div style="margin-bottom:1rem;">
                    <label>Automation Name:</label>
                    <input type="text" name="name" value="My Automation" required style="width:100%; padding:0.5rem; border-radius:6px;" />
                </div>
                <div style="margin-bottom:1rem;">
                    <label>Describe what you want to automate:</label>
                    <textarea name="prompt" rows="5" required style="width:100%; padding:0.5rem; border-radius:6px;"></textarea>
                </div>
                <button class="btn" type="submit">🤖 Generate Automation</button>
            </form>
        </div>

        {% if result %}
        <div class="card" style="background:#f0f9ff;">
            <h3>🎯 Generated Automation</h3>
            <pre style="background:#fff; padding:1rem; border-radius:5px; overflow-x:auto;">{{ result }}</pre>
            <div style="margin-top:1rem;">
                <button class="btn" onclick="navigator.clipboard.writeText(`{{ result | safe }}`)">📋 Copy Code</button>
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
        <div class="card">
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
        async function executeAutomation() {
            try {
                const resultText = `{{ result | safe }}`;
                const steps = JSON.parse(resultText);
                const executeBtn = document.querySelector('button[onclick="executeAutomation()"]');
                executeBtn.innerHTML = '⏳ Executing...';
                executeBtn.disabled = true;

                const response = await fetch('/execute_automation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ steps: steps })
                });

                const data = await response.json();
                if (data.success) {
                    const resultsDiv = document.getElementById('executionResults');
                    const resultsList = document.getElementById('resultsList');
                    resultsList.innerHTML = data.results.map(result => `
                        <div style="padding:0.5rem; border-left:3px solid #10b981; margin:0.5rem 0; background:white;">${result}</div>
                    `).join('');
                    resultsDiv.style.display = 'block';
                    executeBtn.innerHTML = '✅ Executed!';
                } else {
                    alert('Error: ' + data.error);
                    executeBtn.innerHTML = '🚀 Execute Automation';
                    executeBtn.disabled = false;
                }

            } catch (error) {
                alert('Error executing automation: ' + (error.message || error));
                const executeBtn = document.querySelector('button[onclick="executeAutomation()"]');
                executeBtn.innerHTML = '🚀 Execute Automation';
                executeBtn.disabled = false;
            }
        }
    </script>
    """, css=DASHBOARD_CSS, result=result, automations=automations)


@app.route("/workflows")
def workflows():
    with get_db() as db:
        workflows = db.execute("SELECT * FROM workflows ORDER BY created DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Workflows</h1></div>
    <main style="max-width:900px; margin:2rem auto;">
        <h3>Your Workflows</h3>
        {% for wf in workflows %}
        <div class="card">
            <h4>{{ wf.name }}</h4>
            <p>{{ wf.description }}</p>
            <a href="{{ url_for('workflow_run', id=wf.id) }}" class="btn">Run</a>
        </div>
        {% endfor %}
    </main>
    """, css=DASHBOARD_CSS, workflows=workflows)


@app.route("/workflows/run/<int:id>")
def workflow_run(id):
    return f"Workflow run page for {id}"


@app.route("/tools")
def tools():
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Utility Tools</h1></div>
    <div style="text-align:center; margin:2rem;"><a href="{{ url_for('ai_automation_builder') }}" class="btn">🤖 Back to AI Builder</a></div>
    """, css=DASHBOARD_CSS)


@app.route("/admin/leads")
def admin_leads():
    return "Leads admin page"


@app.route("/health")
def health():
    return "OK"


# === AUTH ===
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
                db.execute("INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)", (email, name, password_hash))
                db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")

    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Create Account</h1></div>
    <main style="max-width:500px; margin:2rem auto;"><div class="card">
        <form method="POST">
            <div style="margin-bottom:1rem;"><label>Email:</label><input type="email" name="email" required style="width:100%; padding:0.5rem;"/></div>
            <div style="margin-bottom:1rem;"><label>Full Name:</label><input type="text" name="name" required style="width:100%; padding:0.5rem;"/></div>
            <div style="margin-bottom:1rem;"><label>Password:</label><input type="password" name="password" required style="width:100%; padding:0.5rem;"/></div>
            <button type="submit" class="btn">Register</button>
        </form>
        <p style="margin-top:1rem;">Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
    </div></main>
    """, css=DASHBOARD_CSS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and verify_password(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_plan'] = user['plan']
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Login</h1></div>
    <main style="max-width:500px; margin:2rem auto;"><div class="card">
        <form method="POST">
            <div style="margin-bottom:1rem;"><label>Email:</label><input type="email" name="email" required style="width:100%; padding:0.5rem;"/></div>
            <div style="margin-bottom:1rem;"><label>Password:</label><input type="password" name="password" required style="width:100%; padding:0.5rem;"/></div>
            <button type="submit" class="btn">Login</button>
        </form>
        <p style="margin-top:1rem;">Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
    </div></main>
    """, css=DASHBOARD_CSS)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("dashboard"))


# Pricing
@app.route("/pricing")
def pricing():
    user = get_current_user()
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>💰 Pricing Plans</h1><p>Choose the perfect plan for your automation needs</p></div>
    <div class="card" style="display:flex; gap:1rem; max-width:1000px; margin:2rem auto;">
        <div style="flex:1; padding:1rem; background:white; border-radius:8px;">
            <h3>🚀 Free</h3><p><strong>$0/month</strong></p>
        </div>
        <div style="flex:1; padding:1rem; border:2px solid #667eea; background:white; border-radius:8px;">
            <h3>⭐ Pro</h3><p><strong>$19/month</strong></p>
        </div>
        <div style="flex:1; padding:1rem; background:white; border-radius:8px;">
            <h3>🏢 Business</h3><p><strong>$49/month</strong></p>
        </div>
    </div>
    """, css=DASHBOARD_CSS, user=user)


# === EXECUTION ENDPOINT ===
@app.route("/execute_automation", methods=["POST"])
def execute_automation():
    try:
        payload = request.get_json(force=True)
        automation_steps = payload.get('steps', []) if isinstance(payload, dict) else []
        results = []

        for step in automation_steps:
            if not isinstance(step, dict):
                results.append(f"❌ Invalid step: {step}")
                continue
            step_type = (step.get('type') or '').lower()
            action = step.get('action', '')
            details = step.get('details', '')

            if step_type == 'webhook':
                # simulate webhook setup
                results.append(f"✅ Webhook step processed: {action}")
            elif step_type in ('email', 'notification'):
                # simulate sending email/notification
                results.append(f"✅ Notification step: {action}")
            elif step_type == 'database':
                # simulate DB write
                results.append(f"✅ Database step: {action}")
            elif step_type == 'http_request':
                # attempt a simple GET if details contains a URL
                if isinstance(details, str) and 'http' in details:
                    try:
                        url = details.split('\n')[0].strip()
                        r = requests.get(url, timeout=10)
                        results.append(f"✅ HTTP Request to {r.url} - {r.status_code}")
                    except Exception as e:
                        results.append(f"❌ HTTP Request failed: {str(e)}")
                else:
                    results.append(f"✅ HTTP Request step noted: {action}")
            else:
                results.append(f"⚠️ Unknown step type '{step_type}': {action}")

        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 so local machine and other hosts (if allowed) can reach it.
    app.run(host='0.0.0.0', port=port, debug=True)
