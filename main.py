# Amir Automator Dashboard - WITH AI AUTOMATION BUILDER
import os, uuid, json, sqlite3, requests
from flask import Flask, request, redirect, url_for, flash, render_template_string, session, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# === AI CONFIGURATION ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

def call_ai_simple(user_input):
    """Universal AI function that actually works"""
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
        else:
            return f"AI Error {response.status_code}: Check API key"
            
    except Exception as e:
        return f"AI Connection Error: {str(e)}"

# === DATABASE SETUP ===
DB_NAME = "amir_automator.db"
def get_db():
    conn = sqlite3.connect(DB_NAME)
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

# === SIMPLIFIED CSS ===
DASHBOARD_CSS = """
<style>
body { font-family: 'Segoe UI',Arial,sans-serif; background: #f8fafc; margin:0; }
.header { background:#2d3748; color:#fff; padding:1.5rem; text-align:center; }
.cards { display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:center; margin:2rem 0;}
.card { background:#fff; border-radius:10px; box-shadow:0 2px 8px #0001; width:320px; padding:2rem 1.5rem;
        display:flex; flex-direction:column; align-items:flex-start; min-height:220px}
.card h3 { margin-top:0; }
.card p { flex:1 0 auto; color:#444 }
.card .btn { background:#4299e1; color:#fff; padding:0.5em 1.2em; border:none; border-radius:4px; text-decoration:none;}
.card .btn:hover { background:#2b6cb0; }
.flash { background:#d4f0c5; color:#235d1c; padding:1em; margin:1em auto; border-radius:5px; width:fit-content;}
.form-group { margin-bottom:1rem;}
input,textarea,select { border:1px solid #bbb; border-radius:4px; padding:6px; margin:4px 0; width:100%;}
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
@app.route("/ai_automation", methods=["GET", "POST"])  # FIXED: changed to underscore
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
