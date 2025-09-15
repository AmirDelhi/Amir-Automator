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
with db() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        goal TEXT,
        status TEXT,
        created_at INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS steps (
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
        with db() as c:
            c.execute(
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
    rows = []
    with db() as c:
        c.execute("SELECT id, goal, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 50")
        rows = c.fetchall()
    html = ["<h2>Latest Leads</h2><ul>"]
    for r in rows:
        html.append(f"<li><code>{r[1]}</code> — <small>{r[3]}</small></li>")
    html.append("</ul><p><a href='/'>← Back to Home</a></p>")
    return "\n".join(html)

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
