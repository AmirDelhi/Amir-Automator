import os, io, time, json, zipfile, sqlite3, uuid, secrets, random
from urllib.parse import quote_plus
from flask import Flask, request, redirect, render_template_string, session, url_for, send_file, flash

# App setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "amir-dev-secret-keep-it-safe")

# Directories
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
ARTIFACTS_DIR = "artifacts"
DB = "state.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Database connection
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# Create tables once at startup
with db() as conn:
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        goal TEXT,
        status TEXT,
        created_at INTEGER
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS steps (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        agent TEXT,
        action TEXT,
        input TEXT,
        output TEXT,
        status TEXT,
        created_at INTEGER
    )""")

# Homepage route with lead form
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        with db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (id, goal, status, created_at) VALUES (?, ?, ?, ?)",
                [str(uuid.uuid4()), f"{name} | {email} | {message}", "new", int(time.time())]
            )
        flash("Thanks! Your message has been received.")
        return redirect("/")
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Amir Automator</title>
        <style>
            body { font-family: Arial; padding: 40px; background: #f4f4f4; }
            h1 { color: #333; }
            form { background: white; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; }
            input, textarea { width: 100%; margin-bottom: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            .flash { color: green; text-align: center; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>Welcome to Amir Automator</h1>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="name" placeholder="Your Name" required>
            <input type="email" name="email" placeholder="Your Email" required>
            <textarea name="message" placeholder="Your Message" required></textarea>
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """)

# Health check route
@app.route("/health")
def health():
    return "ok", 200

# Lead viewer route
@app.route("/admin/leads")
def admin_leads():
    try:
        with db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, goal, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 50")
            rows = cursor.fetchall()
    except Exception as e:
        return f"<h2>Error loading leads</h2><pre>{str(e)}</pre>", 500

    html = ["<h2>Latest Leads</h2><ul>"]
    for r in rows:
        lead_text = r[1]
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[3]))
        html.append(f"<li><code>{lead_text}</code> — <small>{timestamp}</small></li>")
    html.append("</ul><p><a href='/'>← Back to Home</a></p>")
    return "\n".join(html)

# Styled dashboard route
@app.route("/dashboard")
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Amir Automator — Dashboard</title>
      <style>
        body { font-family: Arial; padding: 40px; background: #fafafa; }
        h1 { margin-bottom: 10px; }
        .nav { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 20px; }
        .card { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 16px; }
        .card h3 { margin: 0 0 8px 0; }
        a.btn { display: inline-block; background: #007bff; color: #fff; padding: 8px 12px; border-radius: 6px; text-decoration: none; }
        .top { display: flex; justify-content: space-between; align-items: center; }
        .muted { color: #777; font-size: 14px; }
      </style>
    </head>
    <body>
      <div class="top">
        <h1>Amir Automator</h1>
        <div class="muted">v0.1 • {{ brand }}</div>
      </div>
      <p>Quick tools to collect leads and deliver value fast.</p>
      <div class="nav">
        <div class="card">
          <h3>Leads</h3>
          <p>View submissions from your homepage form.</p>
          <a class="btn" href="/admin/leads">Open</a>
        </div>
        <div class="card">
          <h3>GenAI copywriter</h3>
          <p>Draft headlines, ads, and outreach copy.</p>
          <a class="btn" href="/tools/copywriter">Open</a>
        </div>
        <div class="card">
          <h3>Resume builder</h3>
          <p>Generate a clean resume from your inputs.</p>
          <a class="btn" href="/tools/resume">Open</a>
        </div>
        <div class="card">
          <h3>File uploader</h3>
          <p>Upload and parse files for quick insights.</p>
          <a class="btn" href="/tools/upload">Open</a>
        </div>
      </div>
      <p style="margin-top:30px"><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """, brand=os.environ.get("BRAND_NAME", "Amir Automator"))

# GenAI Copywriter route
@app.route("/tools/copywriter", methods=["GET", "POST"])
def tool_copywriter():
    output = ""
    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if prompt:
            output = f"Headline: {prompt}\n\nAd Copy: {prompt} — fast, clear, and benefit-driven."
    return render_template_string("""
    <h2>GenAI Copywriter</h2>
    <form method="POST">
      <textarea name="prompt" rows="4" cols="60" placeholder="Write a headline..."></textarea><br>
      <button type="submit">Draft</button>
    </form>
    {% if output %}<pre>{{ output }}</pre>{% endif %}
    <p><a href="/dashboard">← Back</a></p>
    """, output=output)

# Resume Builder route
@app.route("/tools/resume", methods=["GET", "POST"])
def tool_resume():
    resume = ""
    if request.method == "POST":
        name = request.form.get("name","").strip()
        role = request.form.get("role","").strip()
        skills = request.form.get("skills","").strip()
        bullets = request.form.get("bullets","").strip()
        resume = f"""{name} — {role}

Skills
- {skills}

Experience
- {bullets}

Links
- WhatsApp: https://wa.me/{os.environ.get("WHATSAPP_NUMBER","
