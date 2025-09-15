import os, io, time, json, zipfile, sqlite3, uuid, secrets, random
from urllib.parse import quote_plus
from flask import Flask, request, redirect, render_template_string, session, url_for, send_file, flash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "amir-dev-secret-keep-it-safe")

UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
ARTIFACTS_DIR = "artifacts"
DB = "state.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
