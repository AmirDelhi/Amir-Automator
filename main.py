# Amir Automator Dashboard - All-in-One Modular Flask App
# ------------------------------------------------------
# This is a monolithic Flask app inspired by Emergent.sh, Zapier, n8n, Make.com, Replit, Bubble, Render, etc.
# Features: Dashboard, Lead Capture, Admin, Page Builder, Workflows, Inbound Webhooks, Utility Tools, App Hosting, AI Integration.
#
# Deployment: See instructions at the end of this file for GitHub + Render deployment.
#
# ------------------------------------------------------

import os
import io
import csv
import uuid
import json
import shutil
import zipfile
import sqlite3
import datetime
import traceback
import requests
from flask import (
    Flask, request, redirect, url_for, flash, send_file,
    render_template_string, session, jsonify, abort
)
# Temporary GPT helper until we connect the real API
def call_gpt(user_input):
    # This just echoes back the input in JSON format
    return '{"action": "echo", "content": "' + user_input + '"}'

# --- ENVIRONMENT VARIABLES & CONFIG ---
SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
BRAND_NAME = os.environ.get("BRAND_NAME", "Amir Automator Dashboard")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "")
AI_API_KEY  = os.environ.get("AI_API_KEY", "")
AI_MODEL    = os.environ.get("AI_MODEL", "gpt-3.5-turbo")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")

UPLOAD_FOLDER = os.path.abspath("uploads")
APPS_FOLDER   = os.path.abspath("apps")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(APPS_FOLDER, exist_ok=True)

# --- FLASK APP SETUP ---
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# --- DATABASE SETUP ---
DB_NAME = "amir_automator.db"
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, body TEXT, slug TEXT UNIQUE, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, steps_json TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS workflow_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id INTEGER, run_ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            result_json TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, method TEXT, headers TEXT, payload TEXT, received DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, filename TEXT, upload_ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
    print("Database initialized.")

def safe_extract(zip_ref, path):
    for member in zip_ref.namelist():
        member_path = os.path.abspath(os.path.join(path, member))
        if not member_path.startswith(os.path.abspath(path)):
            raise Exception("Unsafe zip file detected!")
        zip_ref.extract(member, path)

init_db()

def ai_generate(system_prompt, user_prompt):
    """
    Calls an OpenAI-compatible API if env vars are set, else returns demo output.
    """
    if AI_BASE_URL and AI_API_KEY:
        url = f"{AI_BASE_URL.strip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[AI Error: {e}]"
    return f"[AI DEMO] {system_prompt} | {user_prompt[:80]}..."

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
a { color: #3182ce; text-decoration: none; }
a:hover { text-decoration: underline; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 1px solid #ddd; padding: 8px; }
tr:nth-child(even){ background-color:#f2f2f2; }
th { background-color: #4299e1; color: white;}
input,textarea,select { border:1px solid #bbb; border-radius:4px; padding:6px; margin:4px 0;}
form label { font-weight:bold;}
.form-group { margin-bottom:1rem;}
</style>
"""

# HOMEPAGE: Lead Capture
@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if name and email:
            with get_db() as db:
                db.execute("INSERT INTO leads (name, email, message) VALUES (?, ?, ?)",
                           (name, email, message))
                db.commit()
            flash("Thank you! We received your message.", "success")
            return redirect(url_for("home"))
        else:
            flash("Name and Email are required.", "danger")
    leads_ct = get_db().execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
        <h1>{{ brand }}</h1>
        <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard</a> &nbsp;
        <a href="{{ url_for('admin_leads') }}" class="btn">Admin</a>
    </div>
    <div style="max-width:440px;margin:2.5rem auto;background:#fff;padding:2rem 2rem 1rem 2rem;border-radius:10px;box-shadow:0 2px 8px #0001;">
        <h2>Contact Us</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for cat,msg in messages %}
              <div class="flash">{{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="post">
            <div class="form-group"><label>Name</label><br>
                <input type="text" name="name" required></div>
            <div class="form-group"><label>Email</label><br>
                <input type="email" name="email" required></div>
            <div class="form-group"><label>Message</label><br>
                <textarea name="message" rows=3></textarea></div>
            <button class="btn" type="submit">Submit</button>
        </form>
        <div style="margin-top:1.6rem;color:#888;">Total leads: {{ leads_ct }}</div>
    </div>
    """, css=DASHBOARD_CSS, brand=BRAND_NAME, leads_ct=leads_ct)

# DASHBOARD: Central Hub
@app.route("/dashboard")
def dashboard():
    cards = [
        {
            "title": "Page Builder",
            "desc": "Create simple web pages and publish them instantly.",
            "url": url_for("builder_pages")
        },
        {
            "title": "Workflows",
            "desc": "Design and run JSON-based workflows (HTTP, AI, DB, webhooks).",
            "url": url_for("workflows")
        },
        {
            "title": "Inbound Webhooks",
            "desc": "Receive and log incoming webhook requests. Docs & test included.",
            "url": url_for("webhook_test")
        },
        {
            "title": "Utility Tools",
            "desc": "AI Copywriter, Resume Builder, File Upload, Calculator, Text Utils, Summarizer, Code Runner.",
            "url": url_for("tools")
        },
        {
            "title": "App Hosting",
            "desc": "Upload a Flask mini-app (zip), simulate deployment, view apps.",
            "url": url_for("apps")
        },
        {
            "title": "Lead Admin",
            "desc": "View & export lead capture form submissions.",
            "url": url_for("admin_leads")
        }
    ]
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
        <h1>{{ brand }} Dashboard</h1>
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
    """, css=DASHBOARD_CSS, brand=BRAND_NAME, cards=cards)

# --- ADMIN: Leads & Export ---
@app.route("/admin/leads")
def admin_leads():
    db = get_db()
    leads = db.execute("SELECT * FROM leads ORDER BY ts DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
      <h1>Admin: Leads</h1>
      <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
      <a href="{{ url_for('admin_leads_csv') }}" class="btn">Export CSV</a>
    </div>
    <main style="max-width:900px;margin:2rem auto;">
    <table>
      <tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th><th>Timestamp</th></tr>
      {% for row in leads %}
        <tr>
            <td>{{ row.id }}</td>
            <td>{{ row.name }}</td>
            <td>{{ row.email }}</td>
            <td>{{ row.message }}</td>
            <td>{{ row.ts }}</td>
        </tr>
      {% endfor %}
    </table>
    <div style="margin:1rem 0;"><a href="{{ url_for('home') }}">Back to Home</a></div>
    </main>
    """, css=DASHBOARD_CSS, leads=leads)

@app.route("/admin/leads.csv")
def admin_leads_csv():
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["ID", "Name", "Email", "Message", "Timestamp"])
    db = get_db()
    for row in db.execute("SELECT * FROM leads ORDER BY ts DESC"):
        cw.writerow([row["id"], row["name"], row["email"], row["message"], row["ts"]])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="leads.csv")

# --- PAGE BUILDER ---
@app.route("/builder/pages")
def builder_pages():
    db = get_db()
    pages = db.execute("SELECT * FROM pages ORDER BY created DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
      <h1>Page Builder</h1>
      <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
      <a href="{{ url_for('builder_new') }}" class="btn">Create New Page</a>
    </div>
    <main style="max-width:900px;margin:2rem auto;">
      <table>
        <tr><th>Title</th><th>Slug</th><th>Created</th><th>Preview</th></tr>
        {% for p in pages %}
          <tr>
            <td>{{ p.title }}</td>
            <td>{{ p.slug }}</td>
            <td>{{ p.created }}</td>
            <td><a href="{{ url_for('builder_page', slug=p.slug) }}" target="_blank">Open</a></td>
          </tr>
        {% endfor %}
      </table>
    </main>
    """, css=DASHBOARD_CSS, pages=pages)

@app.route("/builder/new", methods=["GET", "POST"])
def builder_new():
    msg = ""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        slug = request.form.get("slug", "").strip().replace(" ", "-").lower()
        if not slug:
            slug = str(uuid.uuid4())[:8]
        with get_db() as db:
            try:
                db.execute("INSERT INTO pages (title, body, slug) VALUES (?, ?, ?)", (title, body, slug))
                db.commit()
                return redirect(url_for("builder_pages"))
            except sqlite3.IntegrityError:
                msg = "Slug already exists. Try another."
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>New Page</h1>
    <a href="{{ url_for('builder_pages') }}" class="btn">Pages</a></div>
    <main style="max-width:700px;margin:2rem auto;">
      {% if msg %}<div class="flash">{{ msg }}</div>{% endif %}
      <form method="post">
        <div class="form-group"><label>Title</label><br>
            <input type="text" name="title" required></div>
        <div class="form-group"><label>Body (HTML allowed)</label><br>
            <textarea name="body" rows=8 required></textarea></div>
        <div class="form-group"><label>Slug (optional)</label><br>
            <input type="text" name="slug" placeholder="my-page"></div>
        <button class="btn" type="submit">Publish</button>
      </form>
    </main>
    """, css=DASHBOARD_CSS, msg=msg)

@app.route("/p/<slug>")
def builder_page(slug):
    db = get_db()
    page = db.execute("SELECT * FROM pages WHERE slug=?", (slug,)).fetchone()
    if not page:
        return "404 Page not found", 404
    return render_template_string("""
    {{ css|safe }}
    <div style="max-width:800px;margin:2rem auto 1rem auto;background:#fff;padding:2rem;border-radius:10px;box-shadow:0 2px 8px #0001;">
      <h1>{{ page.title }}</h1>
      <div>{{ page.body | safe }}</div>
      <div style="margin-top:2em;font-size:90%;color:#888;">Published at {{ page.created }}</div>
    </div>
    """, css=DASHBOARD_CSS, page=page)

# --- WORKFLOWS ---
@app.route("/workflows", methods=["GET", "POST"])
def workflows():
    db = get_db()
    msg = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("desc", "").strip()
        steps_json = request.form.get("steps_json", "").strip()
        try:
            steps = json.loads(steps_json)
            db.execute("INSERT INTO workflows (name, description, steps_json) VALUES (?, ?, ?)",
                       (name, desc, steps_json))
            db.commit()
            flash("Workflow created!", "success")
            return redirect(url_for("workflows"))
        except Exception as e:
            msg = f"Error: {e}"
    workflows = db.execute("SELECT * FROM workflows ORDER BY created DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header">
      <h1>Workflows</h1>
      <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
    </div>
    <main style="max-width:950px;margin:2rem auto;">
      <h3>Create New Workflow</h3>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for cat,msg in messages %}
            <div class="flash">{{ msg }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {% if msg %}<div class="flash">{{ msg }}</div>{% endif %}
      <form method="post">
        <div class="form-group"><label>Name</label><br>
          <input name="name" required></div>
        <div class="form-group"><label>Description</label><br>
          <input name="desc"></div>
        <div class="form-group"><label>Steps (JSON array)</label><br>
          <textarea name="steps_json" rows=6 required>[{{'{"type":"http_post","url":"https://example.com","payload":{"foo":"bar"}}'}}]</textarea>
        </div>
        <button class="btn" type="submit">Create Workflow</button>
      </form>
      <h3 style="margin-top:2.5em;">Workflows</h3>
      <table>
        <tr><th>Name</th><th>Description</th><th>Created</th><th>Run</th></tr>
        {% for wf in workflows %}
          <tr>
            <td>{{ wf.name }}</td>
            <td>{{ wf.description }}</td>
            <td>{{ wf.created }}</td>
            <td><a href="{{ url_for('workflow_run', id=wf.id) }}" class="btn">Run</a></td>
          </tr>
        {% endfor %}
      </table>
    </main>
    """, css=DASHBOARD_CSS, workflows=workflows, msg=msg)

@app.route("/workflows/run/<int:id>", methods=["GET", "POST"])
def workflow_run(id):
    db = get_db()
    wf = db.execute("SELECT * FROM workflows WHERE id=?", (id,)).fetchone()
    if not wf:
        return "Workflow not found", 404
    steps = json.loads(wf["steps_json"])
    results = []
    if request.method == "POST":
        for i, step in enumerate(steps):
            r = {"step": i+1, "type": step.get("type"), "result": None, "error": None}
            try:
                if step["type"] == "http_post":
                    url = step["url"]
                    payload = step.get("payload", {})
                    resp = requests.post(url, json=payload, timeout=10)
                    r["result"] = {"status": resp.status_code, "text": resp.text[:300]}
                elif step["type"] == "ai_generate":
                    prompt = step.get("prompt", "")
                    r["result"] = ai_generate("You are a helpful assistant", prompt)
                elif step["type"] == "save_to_db":
                    table = step.get("table", "steps")
                    data = step.get("data", {})
                    db.execute(f"INSERT INTO {table} (data, ts) VALUES (?, ?)", (json.dumps(data), datetime.datetime.utcnow()))
                    db.commit()
                    r["result"] = f"Saved to {table}."
                elif step["type"] == "webhook_trigger":
                    url = step["url"]
                    payload = step.get("payload", {})
                    resp = requests.post(url, json=payload, timeout=10)
                    r["result"] = f"Webhook status {resp.status_code}"
                else:
                    r["error"] = "Unknown step type"
            except Exception as e:
                r["error"] = str(e)
            results.append(r)
        db.execute("INSERT INTO workflow_logs (workflow_id, result_json) VALUES (?, ?)", (wf["id"], json.dumps(results)))
        db.commit()
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Run Workflow: {{ wf.name }}</h1>
    <a href="{{ url_for('workflows') }}" class="btn">Back</a></div>
    <main style="max-width:900px;margin:2rem auto;">
      <div><b>Description:</b> {{ wf.description }}</div>
      <div><b>Steps:</b>
        <pre>{{ wf.steps_json }}</pre>
      </div>
      <form method="post">
        <button class="btn" type="submit">Run Workflow</button>
      </form>
      {% if results %}
      <h3>Results</h3>
      <pre>{{ results|tojson(indent=2) }}</pre>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, wf=wf, results=results)

# --- INBOUND WEBHOOKS ---
@app.route("/integrations/webhook/<name>", methods=["GET", "POST"])
def integrations_webhook(name):
    db = get_db()
    headers = dict(request.headers)
    payload = ""
    try:
        payload = request.get_json(force=False, silent=True)
        if payload is None:
            payload = request.form or request.data.decode("utf-8")
        else:
            payload = json.dumps(payload)
    except Exception:
        payload = request.data.decode("utf-8")
    db.execute("INSERT INTO webhooks (name, method, headers, payload) VALUES (?, ?, ?, ?)",
               (name, request.method, json.dumps(headers), str(payload)))
    db.commit()
    return jsonify({"status": "ok", "name": name})

@app.route("/integrations/webhook-test")
def webhook_test():
    db = get_db()
    recent = db.execute("SELECT * FROM webhooks ORDER BY received DESC LIMIT 10").fetchall()
    example_curl = f"""curl -X POST https://{{{{ request.host }}}}/integrations/webhook/testhook -H "X-Test: 123" -d '{{"foo":"bar"}}'"""
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Inbound Webhooks</h1>
      <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
    </div>
    <main style="max-width:900px;margin:2rem auto;">
      <h3>Send a POST or GET to:</h3>
      <pre>POST/GET https://{{ request.host }}/integrations/webhook/&lt;name&gt;</pre>
      <div>Example:</div>
      <pre>curl -X POST https://{{ request.host }}/integrations/webhook/testhook -H "X-Test: 123" -d '{"foo":"bar"}'</pre>
      <h3>Recent Webhooks</h3>
      <table>
        <tr><th>Name</th><th>Method</th><th>Received</th><th>Headers</th><th>Payload</th></tr>
        {% for wh in recent %}
          <tr>
            <td>{{ wh.name }}</td>
            <td>{{ wh.method }}</td>
            <td>{{ wh.received }}</td>
            <td><pre style="max-width:220px;overflow-x:auto;">{{ wh.headers|truncate(160) }}</pre></td>
            <td><pre style="max-width:320px;overflow-x:auto;">{{ wh.payload|truncate(320) }}</pre></td>
          </tr>
        {% endfor %}
      </table>
    </main>
    """, css=DASHBOARD_CSS, recent=recent)

# --- UTILITY TOOLS DASHBOARD ---
@app.route("/tools")
def tools():
    tool_cards = [
        {"title":"Copywriter (AI)", "desc":"Generate ad copy from a prompt.", "url":url_for("tools_copywriter")},
        {"title":"Resume Builder", "desc":"Build a resume from your info. AI polish optional.", "url":url_for("tools_resume")},
        {"title":"File Upload", "desc":"Upload files to /uploads.", "url":url_for("tools_upload")},
        {"title":"Calculator", "desc":"Simple calculator (add, subtract, multiply, divide).", "url":url_for("tools_calculator")},
        {"title":"Text Utils", "desc":"Format text: uppercase, lowercase, slugify.", "url":url_for("tools_textutils")},
        {"title":"Summarizer (AI)", "desc":"Paste text, get a summary.", "url":url_for("tools_summarizer")},
        {"title":"Code Runner", "desc":"Python code runner (Replit-lite).", "url":url_for("tools_code")},
    ]
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Utility Tools</h1>
      <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a>
    </div>
    <div class="cards">
      {% for t in tool_cards %}
        <div class="card">
          <h3>{{ t.title }}</h3>
          <p>{{ t.desc }}</p>
          <a href="{{ t.url }}" class="btn">Open</a>
        </div>
      {% endfor %}
    </div>
    """, css=DASHBOARD_CSS, tool_cards=tool_cards)

# --- TOOL: Copywriter (AI) ---
@app.route("/tools/copywriter", methods=["GET", "POST"])
def tools_copywriter():
    result = ""
    if request.method == "POST":
        prompt = request.form.get("prompt", "")
        result = ai_generate("You are an expert ad copywriter.", prompt)
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>AI Copywriter</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:700px;margin:2rem auto;">
      <form method="post">
        <div class="form-group"><label>Describe your product or service:</label><br>
        <textarea name="prompt" rows=4 required></textarea></div>
        <button class="btn" type="submit">Generate Copy</button>
      </form>
      {% if result %}
      <h3>Generated Copy</h3>
      <div style="background:#eee;padding:1em;border-radius:5px;">{{ result }}</div>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, result=result)

# --- TOOL: Resume Builder (w/AI polish option) ---
@app.route("/tools/resume", methods=["GET", "POST"])
def tools_resume():
    result = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        role = request.form.get("role", "")
        skills = request.form.get("skills", "")
        bullets = request.form.get("bullets", "")
        polish = request.form.get("polish")
        resume = f"Resume for {name}\nRole: {role}\nSkills: {skills}\nAchievements:\n- " + "\n- ".join(bullets.split("\n"))
        if polish:
            result = ai_generate("You are a resume writing and editing assistant.", resume)
        else:
            result = resume
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Resume Builder</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:700px;margin:2rem auto;">
      <form method="post">
        <div class="form-group"><label>Name</label><br>
        <input name="name" required></div>
        <div class="form-group"><label>Role</label><br>
        <input name="role" required></div>
        <div class="form-group"><label>Skills (comma separated)</label><br>
        <input name="skills" required></div>
        <div class="form-group"><label>Achievements (one per line)</label><br>
        <textarea name="bullets" rows=4></textarea></div>
        <div class="form-group"><input type="checkbox" name="polish" value="1"> Polish with AI</div>
        <button class="btn" type="submit">Generate Resume</button>
      </form>
      {% if result %}
      <h3>Generated Resume</h3>
      <pre style="background:#eee;padding:1em;border-radius:5px;">{{ result }}</pre>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, result=result)

# --- TOOL: File Upload ---
@app.route("/tools/upload", methods=["GET", "POST"])
def tools_upload():
    msg = ""
    files = []
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            fname = f"{uuid.uuid4().hex}_{f.filename}"
            path = os.path.join(UPLOAD_FOLDER, fname)
            f.save(path)
            msg = f"File uploaded as {fname}"
        else:
            msg = "No file selected."
    files = os.listdir(UPLOAD_FOLDER)
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>File Upload</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:700px;margin:2rem auto;">
      {% if msg %}<div class="flash">{{ msg }}</div>{% endif %}
      <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <button class="btn" type="submit">Upload</button>
      </form>
      <h3>Uploaded Files</h3>
      <ul>
      {% for fname in files %}
        <li><a href="/uploads/{{ fname }}" target="_blank">{{ fname }}</a></li>
      {% endfor %}
      </ul>
    </main>
    """, css=DASHBOARD_CSS, msg=msg, files=files)

@app.route("/uploads/<fname>")
def uploaded_file(fname):
    return send_file(os.path.join(UPLOAD_FOLDER, fname))

# --- TOOL: Calculator ---
@app.route("/tools/calculator", methods=["GET", "POST"])
def tools_calculator():
    result = None
    if request.method == "POST":
        try:
            a = float(request.form.get("a", "0"))
            b = float(request.form.get("b", "0"))
            op = request.form.get("op")
            if op == "add":
                result = a + b
            elif op == "sub":
                result = a - b
            elif op == "mul":
                result = a * b
            elif op == "div":
                result = a / b if b != 0 else "Infinity"
        except Exception:
            result = "Invalid input."
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Calculator</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:500px;margin:2rem auto;">
      <form method="post">
        <input type="number" name="a" step="any" required>
        <select name="op">
          <option value="add">+</option>
          <option value="sub">-</option>
          <option value="mul">*</option>
          <option value="div">/</option>
        </select>
        <input type="number" name="b" step="any" required>
        <button class="btn" type="submit">=</button>
      </form>
      {% if result is not none %}
        <h3>Result: {{ result }}</h3>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, result=result)

# --- TOOL: Text Utils ---
def slugify(s):
    import re
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')

@app.route("/tools/textutils", methods=["GET", "POST"])
def tools_textutils():
    result = ""
    out = ""
    if request.method == "POST":
        txt = request.form.get("text", "")
        fmt = request.form.get("fmt")
        if fmt == "upper":
            out = txt.upper()
        elif fmt == "lower":
            out = txt.lower()
        elif fmt == "slug":
            out = slugify(txt)
        result = out
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Text Utils</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:600px;margin:2rem auto;">
      <form method="post">
        <div class="form-group"><label>Text</label><br>
          <textarea name="text" rows=3 required></textarea></div>
        <div class="form-group">
          <select name="fmt">
            <option value="upper">UPPERCASE</option>
            <option value="lower">lowercase</option>
            <option value="slug">slugify</option>
          </select>
        </div>
        <button class="btn" type="submit">Format</button>
      </form>
      {% if result %}
      <h3>Output</h3>
      <pre style="background:#eee;padding:1em;border-radius:5px;">{{ result }}</pre>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, result=result)

# --- TOOL: Summarizer (AI) ---
@app.route("/tools/summarizer", methods=["GET", "POST"])
def tools_summarizer():
    result = ""
    if request.method == "POST":
        txt = request.form.get("text", "")
        result = ai_generate("Summarize the following text in a concise way.", txt)
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Summarizer (AI)</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:700px;margin:2rem auto;">
      <form method="post">
        <div class="form-group"><label>Paste text to summarize</label><br>
        <textarea name="text" rows=7 required></textarea></div>
        <button class="btn" type="submit">Summarize</button>
      </form>
      {% if result %}
      <h3>Summary</h3>
      <div style="background:#eee;padding:1em;border-radius:5px;">{{ result }}</div>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, result=result)

# --- TOOL: Replit-lite Code Runner ---
@app.route("/tools/code", methods=["GET", "POST"])
def tools_code():
    out = err = ""
    code = ""
    if request.method == "POST":
        code = request.form.get("code", "")
        try:
            import sys
            import contextlib
            stdout = io.StringIO()
            stderr = io.StringIO()
            local_vars = {}
            with contextlib.redirect_stdout(stdout):
                with contextlib.redirect_stderr(stderr):
                    exec(code, {"__builtins__":__builtins__,"__name__":"__main__"}, local_vars)
            out = stdout.getvalue()
            err = stderr.getvalue()
        except Exception as e:
            err = str(e) + "\n" + traceback.format_exc()
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>Python Code Runner</h1>
    <a href="{{ url_for('tools') }}" class="btn">Tools</a></div>
    <main style="max-width:900px;margin:2rem auto;">
      <form method="post">
        <div class="form-group"><label>Python Code</label><br>
        <textarea name="code" rows=10 style="width:100%" required>{{ code }}</textarea></div>
        <button class="btn" type="submit">Run</button>
      </form>
      {% if out or err %}
      <div style="margin-top:1.5em;">
        <h3>Output</h3>
        <pre style="background:#e2f7e1;padding:1em;border-radius:5px;">{{ out }}</pre>
        {% if err %}
        <h3>Errors</h3>
        <pre style="background:#ffeaea;padding:1em;border-radius:5px;">{{ err }}</pre>
        {% endif %}
      </div>
      {% endif %}
    </main>
    """, css=DASHBOARD_CSS, out=out, err=err, code=code)

# --- APP HOSTING (Upload Flask mini-app as ZIP) ---
@app.route("/apps", methods=["GET", "POST"])
def apps():
    msg = ""
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "MiniApp")
        desc = request.form.get("desc", "")
        f = request.files.get("file")
        if f and f.filename.endswith(".zip"):
            app_id = str(uuid.uuid4())[:8]
            save_folder = os.path.join(APPS_FOLDER, app_id)
            os.makedirs(save_folder, exist_ok=True)
            zip_path = os.path.join(save_folder, f.filename)
            f.save(zip_path)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    safe_extract(zip_ref, save_folder)
                db.execute("INSERT INTO apps (name, description, filename) VALUES (?, ?, ?)", (name, desc, f.filename))
                db.commit()
                msg = f"App '{name}' deployed! (Simulated)"
            except Exception as e:
                msg = f"Error extracting zip: {e}"
        else:
            msg = "Please upload a .zip file."
    apps = db.execute("SELECT * FROM apps ORDER BY upload_ts DESC").fetchall()
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>App Hosting</h1>
    <a href="{{ url_for('dashboard') }}" class="btn">Dashboard</a></div>
    <main style="max-width:900px;margin:2rem auto;">
      {% if msg %}<div class="flash">{{ msg }}</div>{% endif %}
      <h3>Upload Flask App (zip)</h3>
      <form method="post" enctype="multipart/form-data">
        <div class="form-group"><label>App Name</label><br>
            <input name="name" required></div>
        <div class="form-group"><label>Description</label><br>
            <input name="desc"></div>
        <div class="form-group"><label>Zip File</label><br>
            <input type="file" name="file" required></div>
        <button class="btn" type="submit">Deploy</button>
      </form>
      <h3>Deployed Apps</h3>
      <table>
        <tr><th>Name</th><th>Description</th><th>File</th><th>Deployed At</th></tr>
        {% for a in apps %}
        <tr>
          <td>{{ a.name }}</td>
          <td>{{ a.description }}</td>
          <td>{{ a.filename }}</td>
          <td>{{ a.upload_ts }}</td>
        </tr>
        {% endfor %}
      </table>
      <div style="margin-top:1em;font-size:90%;color:#888;">Note: Uploaded apps are extracted but not auto-executed for safety.</div>
    </main>
    """, css=DASHBOARD_CSS, msg=msg, apps=apps)

# --- HEALTH CHECK ---
@app.route("/health")
def health():
    return "ok"

# --- ERROR HANDLER (Optional, for a friendlier 404) ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template_string("""
    {{ css|safe }}
    <div class="header"><h1>404 Not Found</h1></div>
    <div style="max-width:600px;margin:3rem auto;text-align:center;">
      <p>The page you are looking for does not exist.</p>
      <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard</a>
    </div>
    """, css=DASHBOARD_CSS), 404

# --- DEPLOYMENT INSTRUCTIONS ---
"""
# Deployment (GitHub + Render):
#
# 1. Push this repo to GitHub (e.g., https://github.com/AmirDelhi/Amir-Automator).
# 2. On Render.com, select "New Web Service", connect your repo.
# 3. For build & start:
#      - Build Command: pip install -r requirements.txt
#      - Start Command: gunicorn main:app
# 4. Add environment variables as needed (SECRET_KEY, AI_BASE_URL, AI_API_KEY, etc).
#
# The app will auto-create a SQLite DB file on first run.
#
# For local dev:
#   $ pip install -r requirements.txt
#   $ flask run

@app.route("/chat", methods=["GET","POST"])
def chat():
    response, raw_cmd, error = None, None, None
    if request.method == "POST":
        user_input = request.form.get("message","").strip()
        if not user_input:
            error = "Please type a command."
        else:
            raw_cmd = call_gpt(user_input)
            try:
                cmd = json.loads(raw_cmd)
                response = {"ok": True, "message": f"Executed {cmd['action']}"}
            except Exception as e:
                error = f"Parse error: {e}"
    return render_template_string("""
        <h2>Personal AI Assistant</h2>
        <form method="POST">
          <textarea name="message" rows="4" style="width:100%" placeholder="Type a command..."></textarea><br>
          <button type="submit">Run</button>
        </form>
        {% if error %}<div style="color:red">{{ error }}</div>{% endif %}
        {% if raw_cmd %}
          <h4>Parsed JSON</h4><pre>{{ raw_cmd }}</pre>
        {% endif %}
        {% if response %}
          <h4>Result</h4><pre>{{ response }}</pre>
        {% endif %}
        <p><a href="/dashboard">← Back</a></p>
    """, response=response, raw_cmd=raw_cmd, error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

