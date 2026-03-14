import os
import secrets
import bcrypt
import requests
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import (Flask, request, jsonify, render_template,
                   redirect, url_for, session, send_file, send_from_directory)
from flask_session import Session
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# ─── Sesión persistente server-side ──────────────────────────────────────────
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, ".flask_sessions")
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
Session(app)

# ─── MongoDB ──────────────────────────────────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client["explorerframe"]
users_col    = db["users"]
tokens_col   = db["pending_tokens"]
dl_tokens_col = db["download_tokens"]   # tokens de descarga de un solo uso

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass

def generate_token():
    return secrets.token_urlsafe(32)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not key:
            return jsonify({"error": "Forbidden"}), 403
        user = users_col.find_one({"api_key": key})
        if not user:
            return jsonify({"error": "Forbidden"}), 403
        request.api_user = user
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("register.html", error="Completa todos los campos.")

    if users_col.find_one({"telegram_username": username}):
        return render_template("register.html", error="Este usuario ya está registrado.")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    token   = generate_token()
    expires = utcnow() + timedelta(minutes=20)

    tokens_col.delete_many({"telegram_username": username})
    tokens_col.insert_one({
        "telegram_username": username,
        "token": token,
        "password_hash": hashed,
        "expires": expires,
        "type": "register"
    })

    chat_id = username if username.lstrip("-").isdigit() else username
    send_telegram_message(chat_id,
        f"🔐 <b>ExplorerFrame Auth</b>\n\n"
        f"Tu token de verificación:\n\n<code>{token}</code>\n\n"
        f"⏳ Expira en <b>20 minutos</b>."
    )

    session["pending_register"] = username
    return redirect(url_for("register_verify"))

@app.route("/register/verify/", methods=["GET", "POST"])
def register_verify():
    username = session.get("pending_register")
    if not username:
        return redirect(url_for("register"))

    if request.method == "GET":
        return render_template("register_verify.html", username=username)

    token_input = request.form.get("token", "").strip()
    record = tokens_col.find_one({"telegram_username": username, "type": "register"})

    if not record:
        return render_template("register_verify.html", username=username, error="No hay token pendiente.")
    if utcnow() > record["expires"]:
        tokens_col.delete_one({"_id": record["_id"]})
        return render_template("register_verify.html", username=username, error="Token expirado. Vuelve a registrarte.")
    if token_input != record["token"]:
        return render_template("register_verify.html", username=username, error="Token incorrecto.")

    api_key = secrets.token_hex(32)
    users_col.insert_one({
        "telegram_username": username,
        "password_hash": record["password_hash"],
        "api_key": api_key,
        "created_at": utcnow()
    })
    tokens_col.delete_one({"_id": record["_id"]})
    session.pop("pending_register", None)
    session.permanent = True
    session["user"] = username
    return redirect(url_for("dashboard"))

@app.route("/login/", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    user = users_col.find_one({"telegram_username": username})
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return render_template("login.html", error="Credenciales incorrectas.")

    token   = generate_token()
    expires = utcnow() + timedelta(minutes=20)
    tokens_col.delete_many({"telegram_username": username, "type": "login"})
    tokens_col.insert_one({"telegram_username": username, "token": token, "expires": expires, "type": "login"})

    chat_id = username if username.lstrip("-").isdigit() else username
    send_telegram_message(chat_id,
        f"🔐 <b>ExplorerFrame Login</b>\n\n"
        f"Token de inicio de sesión:\n\n<code>{token}</code>\n\n"
        f"⏳ Expira en <b>20 minutos</b>."
    )

    session["pending_login"] = username
    return redirect(url_for("login_verify"))

@app.route("/login/verify/", methods=["GET", "POST"])
def login_verify():
    username = session.get("pending_login")
    if not username:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("register_verify.html", username=username, mode="login")

    token_input = request.form.get("token", "").strip()
    record = tokens_col.find_one({"telegram_username": username, "type": "login"})

    if not record or utcnow() > record["expires"]:
        return render_template("register_verify.html", username=username, mode="login", error="Token expirado o inválido.")
    if token_input != record["token"]:
        return render_template("register_verify.html", username=username, mode="login", error="Token incorrecto.")

    tokens_col.delete_one({"_id": record["_id"]})
    session.pop("pending_login", None)
    session.permanent = True
    session["user"] = username
    return redirect(url_for("dashboard"))

@app.route("/dashboard/")
@login_required
def dashboard():
    user = users_col.find_one({"telegram_username": session["user"]})
    return render_template("dashboard.html", user=user)

@app.route("/logout/")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─── Static app folder ────────────────────────────────────────────────────────

@app.route("/app/<path:filename>")
def app_static(filename):
    return send_from_directory(os.path.join(app.root_path, "app"), filename)

# ─── Download (vía token de un solo uso generado por API) ─────────────────────

@app.route("/download/")
def download_exe():
    dl_token = request.args.get("token", "").strip()
    if not dl_token:
        return render_template("forbidden.html"), 403

    record = dl_tokens_col.find_one({"token": dl_token})
    if not record:
        return render_template("forbidden.html"), 403
    if utcnow() > record["expires"]:
        dl_tokens_col.delete_one({"_id": record["_id"]})
        return render_template("forbidden.html"), 403

    dl_tokens_col.delete_one({"_id": record["_id"]})   # un solo uso

    path = os.path.join(app.root_path, "ExplorerFrame.exe")
    if not os.path.exists(path):
        return "Archivo no disponible.", 404
    return send_file(path, as_attachment=True, download_name="ExplorerFrame.exe")

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/v1/telegram/id")
@require_api_key
def api_telegram_ids():
    """Devuelve los usernames/IDs de todos los usuarios registrados separados por comas."""
    users = users_col.find({}, {"telegram_username": 1})
    ids = ",".join(u["telegram_username"] for u in users)
    return ids, 200, {"Content-Type": "text/plain"}

@app.route("/api/v1/download/token", methods=["POST"])
@require_api_key
def api_generate_download_token():
    """
    Genera un token de descarga de un solo uso (válido 10 min).
    Devuelve la URL completa lista para usar.
    Body JSON opcional: { "expires_minutes": 10 }
    """
    body    = request.get_json(silent=True) or {}
    minutes = min(int(body.get("expires_minutes", 10)), 60)
    token   = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(minutes=minutes)

    dl_tokens_col.insert_one({
        "token": token,
        "issued_to": request.api_user["telegram_username"],
        "expires": expires,
        "created_at": utcnow()
    })

    base_url = request.host_url.rstrip("/")
    return jsonify({
        "token": token,
        "download_url": f"{base_url}/download/?token={token}",
        "expires_in_minutes": minutes,
        "expires_at": expires.isoformat() + "Z"
    })

@app.route("/api/v1/download/status")
@require_api_key
def api_download_status():
    """Informa si el archivo ExplorerFrame.exe está disponible en el servidor."""
    available = os.path.exists(os.path.join(app.root_path, "ExplorerFrame.exe"))
    return jsonify({"available": available, "filename": "ExplorerFrame.exe"})

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False)
