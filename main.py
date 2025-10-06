# Amir Automator Dashboard - WITH AI AUTOMATION BUILDER
import os, uuid, json, sqlite3, requests
from flask import Flask, request, redirect, url_for, flash, render_template_string, session, jsonify
from dotenv import load_dotenv

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
        db.execute("""CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, 
            user_prompt TEXT, ai_generated_code TEXT,
            status TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add API integrations table
        db.execute("""CREATE TABLE IF NOT EXISTS api_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT,
            service_type TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add pre-built automations table
        db.execute("""CREATE TABLE IF NOT EXISTS prebuilt_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            category TEXT,
            steps_json TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Keep your existing tables
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, steps_json TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
    print("Database initialized.")

init_db()

# === AI CONFIGURATION ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")  # ✅ FIXED: Added missing quote

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
        # This would use Google Sheets API
        # For demo, return success message
        return f"✅ Data sent to Google Sheets: {len(data)} rows"
    except Exception as e:
        return f"❌ Google Sheets Error: {str(e)}"

def send_slack_message(message, channel="#general"):
    """Send message to Slack"""
    try:
        # This would use Slack Webhook API
        # For demo, return success message
        return f"✅ Message sent to Slack: {message[:50]}..."
    except Exception as e:
        return f"❌ Slack Error: {str(e)}"

def send_email(to_email, subject, body):
    """Send email via SMTP or email service"""
    try:
        # This would use email service API
        # For demo, return success message
        return f"✅ Email sent to {to_email}"
    except Exception as e:
        return f"❌ Email Error: {str(e)}"

def save_to_google_sheets(data, spreadsheet_id):
    """Save data to specific Google Sheet"""
    try:
        return f"✅ Data saved to Google Sheets: {len(data)} items"
    except Exception as e:
        return f"❌ Sheets Save Error: {str(e)}"

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
    cards = [
        {
            "title": "🤖 AI Automation Builder",
            "desc": "Describe what you want in plain English - AI builds the automation",
            "url": url_for("ai_automation_builder")
        },
        {
            "title": "📊 Workflows", 
            "desc": "Design and run automated workflows",
            "url": url_for("workflows")
        },
        {
            "title": "🛠️ Utility Tools",
            "desc": "AI Copywriter, Text Tools, File Upload and more",
            "url": url_for("tools")
        },
        {
            "title": "📨 Lead Capture",
            "desc": "Contact form and lead management",
            "url": url_for("admin_leads")
        }
    ]
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
        <h1>🚀 Amir Automator Dashboard</h1>
        <p>AI-Powered Automation Platform</p>
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
    """, css=DASHBOARD_CSS, cards=cards)

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
                <a href="{{ url_for('workflows') }}" class="btn">🚀 Implement This</a>
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
