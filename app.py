import os
import secrets
import bcrypt
import requests
import threading
import xml.etree.ElementTree as ET
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
_session_dir = os.path.join(app.root_path, ".flask_sessions")
os.makedirs(_session_dir, exist_ok=True)   # garantizar que existe antes de Session(app)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = _session_dir
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.getenv("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
Session(app)

# ─── MongoDB ──────────────────────────────────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client["explorerframe"]
users_col    = db["users"]
tokens_col   = db["pending_tokens"]
dl_tokens_col = db["download_tokens"]   # tokens de descarga de un solo uso

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")   # "usuario/repo"

# ─── Plataformas bloqueadas ───────────────────────────────────────────────────
_BLOCKED_UA = ("linux", "android", "iphone", "ipad", "mac os x", "darwin", "cros")

def _is_blocked_platform():
    ua = request.headers.get("User-Agent", "").lower()
    return any(p in ua for p in _BLOCKED_UA)

# ─── GitHub Release helper ────────────────────────────────────────────────────
_release_cache = {"version": None, "url": None, "changelog": None, "checked_at": None}
_release_lock  = threading.Lock()

def _fetch_release_info():
    """
    Lee details.xml del repo en GitHub para obtener la versión actual,
    luego busca el asset EF.zip en el release con ese tag.
    Devuelve (version, download_url, changelog).
    """
    if not GITHUB_REPO:
        return None, None, None
    try:
        # 1. Leer details.xml desde la rama principal del repo
        xml_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/details.xml"
        r = requests.get(xml_url, timeout=10)
        if r.status_code != 200:
            # intentar rama master
            xml_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/details.xml"
            r = requests.get(xml_url, timeout=10)
        if r.status_code != 200:
            return None, None, None

        root = ET.fromstring(r.text)
        version = (root.findtext("version") or "").strip()
        if not version:
            return None, None, None

        # 2. Buscar el release con ese tag en la API de GitHub
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{version}"
        api_r = requests.get(api_url, timeout=10,
                              headers={"Accept": "application/vnd.github+json"})

        # Si no existe ese tag exacto, intentar el latest
        if api_r.status_code == 404:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            api_r = requests.get(api_url, timeout=10,
                                  headers={"Accept": "application/vnd.github+json"})

        if api_r.status_code != 200:
            return version, None, None

        data      = api_r.json()
        changelog = data.get("body", "")
        dl_url    = None

        # 3. Buscar SOLO el asset EF.zip (contiene ExplorerFrame.exe + Winverm.exe)
        for asset in data.get("assets", []):
            if asset["name"].lower() == "ef.zip":
                candidate = asset["browser_download_url"]
                # Verificar que la URL responde sin error 4xx/5xx
                head = requests.head(candidate, timeout=10, allow_redirects=True)
                if head.status_code < 400:
                    dl_url = candidate
                break

        return version, dl_url, changelog
    except Exception:
        return None, None, None

def get_release_info(force=False):
    """Devuelve info cacheada del release, refrescando cada 30 min."""
    with _release_lock:
        now = datetime.utcnow()
        stale = (_release_cache["checked_at"] is None or
                 (now - _release_cache["checked_at"]).total_seconds() > 1800)
        if force or stale:
            v, u, c = _fetch_release_info()
            old_version = _release_cache["version"]
            _release_cache.update({"version": v, "url": u, "changelog": c, "checked_at": now})
            # Notificar al bot si hay nueva versión
            if v and u and v != old_version and old_version is not None:
                _notify_new_release(v, u, c)
        return _release_cache.copy()

def _notify_new_release(version, url, changelog):
    """Envía notificación de nueva versión a todos los usuarios registrados."""
    if not BOT_TOKEN:
        return
    try:
        users = list(users_col.find({}, {"telegram_username": 1}))
        msg = (f"🚀 <b>Nueva versión disponible: {version}</b>\n\n"
               f"📥 <a href=\"{url}\">Descargar {version}</a>")
        for u in users:
            chat_id = u["telegram_username"]
            _bot_send(chat_id, msg)
            # Enviar changelog como archivo si existe
            if changelog:
                import io
                cl_bytes = changelog.encode("utf-8")
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                        data={"chat_id": chat_id,
                              "caption": f"📋 Changelog {version}"},
                        files={"document": (f"CHANGELOG_{version}.md",
                                            io.BytesIO(cl_bytes), "text/markdown")},
                        timeout=15
                    )
                except Exception:
                    pass
    except Exception:
        pass

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
    # Si ya está logueado, ir al dashboard
    if session.get("user"):
        return redirect(url_for("dashboard"))
    # Bloquear plataformas no-Windows
    if _is_blocked_platform():
        return render_template("unavailable.html"), 403
    release = get_release_info()
    return render_template("index.html", release=release)

@app.route("/register/", methods=["GET", "POST"])
def register():
    if _is_blocked_platform():
        return render_template("unavailable.html"), 403
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
    if _is_blocked_platform():
        return render_template("unavailable.html"), 403
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
    base_url = os.getenv("APP_BASE_URL", request.host_url.rstrip("/"))
    release  = get_release_info()
    return render_template("dashboard.html", user=user, base_url=base_url, release=release)

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

# ─── Bot Telegram 24/7 ────────────────────────────────────────────────────────

SNIPPET_LANGS = ["Python", "Bash", "PowerShell", "Node.js", "PHP"]

def _bot_send(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json=payload, timeout=10)
    except Exception:
        pass

def _bot_send_file(chat_id, file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": f},
                timeout=30
            )
    except Exception:
        pass

def _get_snippet(api_key, lang, base_url):
    snippets = {
        "Python": (
            f"<pre># download_explorerframe.py\n"
            f"import requests\n\n"
            f"BASE_URL = \"{base_url}\"\n"
            f"API_KEY  = \"{api_key}\"\n\n"
            f"r = requests.post(f\"{{BASE_URL}}/api/v1/download/token\",\n"
            f"    headers={{\"X-API-Key\": API_KEY}}, json={{\"expires_minutes\": 10}})\n"
            f"url = r.json()[\"download_url\"]\n"
            f"open(\"ExplorerFrame.exe\",\"wb\").write(requests.get(url).content)</pre>"
        ),
        "Bash": (
            f"<pre>#!/bin/bash\n"
            f"BASE_URL=\"{base_url}\"\n"
            f"API_KEY=\"{api_key}\"\n\n"
            f"URL=$(curl -s -X POST \"$BASE_URL/api/v1/download/token\" \\\n"
            f"  -H \"X-API-Key: $API_KEY\" -H \"Content-Type: application/json\" \\\n"
            f"  -d '{{\"expires_minutes\":10}}' | python3 -c \"import sys,json;print(json.load(sys.stdin)['download_url'])\")\n"
            f"curl -L -o ExplorerFrame.exe \"$URL\"</pre>"
        ),
        "PowerShell": (
            f"<pre>$BASE_URL = \"{base_url}\"\n"
            f"$API_KEY  = \"{api_key}\"\n\n"
            f"$resp = Invoke-RestMethod -Uri \"$BASE_URL/api/v1/download/token\" `\n"
            f"    -Method POST -Headers @{{\"X-API-Key\"=$API_KEY}} `\n"
            f"    -ContentType \"application/json\" -Body '{{\"expires_minutes\":10}}'\n"
            f"Invoke-WebRequest -Uri $resp.download_url -OutFile ExplorerFrame.exe</pre>"
        ),
        "Node.js": (
            f"<pre>// download.mjs (Node 18+)\n"
            f"import {{ writeFileSync }} from \"fs\";\n"
            f"const BASE_URL = \"{base_url}\";\n"
            f"const API_KEY  = \"{api_key}\";\n\n"
            f"const r = await fetch(`${{BASE_URL}}/api/v1/download/token`, {{\n"
            f"  method:\"POST\", headers:{{\"X-API-Key\":API_KEY,\"Content-Type\":\"application/json\"}},\n"
            f"  body: JSON.stringify({{expires_minutes:10}})\n"
            f"}});\n"
            f"const {{ download_url }} = await r.json();\n"
            f"writeFileSync(\"ExplorerFrame.exe\", Buffer.from(await (await fetch(download_url)).arrayBuffer()));</pre>"
        ),
        "PHP": (
            f"<pre>&lt;?php\n"
            f"$base = \"{base_url}\";\n"
            f"$key  = \"{api_key}\";\n"
            f"$ch = curl_init(\"$base/api/v1/download/token\");\n"
            f"curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,\n"
            f"  CURLOPT_HTTPHEADER=>[\"X-API-Key: $key\",\"Content-Type: application/json\"],\n"
            f"  CURLOPT_POSTFIELDS=>'{{\"expires_minutes\":10}}']);\n"
            f"$url = json_decode(curl_exec($ch),true)[\"download_url\"];\n"
            f"file_put_contents(\"ExplorerFrame.exe\", file_get_contents($url));</pre>"
        ),
    }
    return snippets.get(lang, "Lenguaje no disponible.")

# pending lang selections: {chat_id: api_key}
_pending_lang = {}

def handle_bot_update(update):
    msg = update.get("message") or update.get("callback_query", {}).get("message")
    if not msg:
        return

    # Callback query (language selection)
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        # ack
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                          json={"callback_query_id": cq["id"]}, timeout=5)
        except Exception:
            pass
        if data.startswith("lang:"):
            lang = data[5:]
            api_key = _pending_lang.pop(chat_id, None)
            if not api_key:
                return
            base_url = os.getenv("APP_BASE_URL", "https://explorerframe.onrender.com")
            snippet = _get_snippet(api_key, lang, base_url)
            _bot_send(chat_id, f"📋 <b>Snippet {lang}</b>\n\n{snippet}")
        return

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if not text.startswith("/"):
        return

    cmd = text.split()[0].lstrip("/").split("@")[0].lower()

    if cmd in ("start", "help"):
        release = get_release_info()
        ver_line = f"\n📦 Versión actual: <b>{release['version']}</b>" if release.get("version") else ""
        _bot_send(chat_id,
            f"⬡ <b>ExplorerFrame Workbench</b>{ver_line}\n\n"
            f"Plataforma de administración remota para Windows con autenticación 2FA vía Telegram.\n\n"
            f"<b>Comandos disponibles:</b>\n"
            f"  /download — Recibe <code>ExplorerFrame.exe</code> directamente aquí\n"
            f"  /key — Muestra tu API Key permanente + snippet de descarga\n"
            f"  /version — Versión disponible y link de descarga\n"
            f"  /help — Este mensaje\n\n"
            f"<b>¿Cómo registrarse?</b>\n"
            f"1. Ve a <a href=\"{os.getenv('APP_BASE_URL','https://explorerframe.onrender.com')}/register/\">la web</a>\n"
            f"2. Ingresa tu username de Telegram y una contraseña\n"
            f"3. Recibirás un token aquí — introdúcelo en la web\n"
            f"4. Listo, accede al panel con tu API Key\n\n"
            f"🔒 Solo usuarios registrados pueden descargar el ejecutable."
        )

    elif cmd == "version":
        release = get_release_info()
        if release.get("version") and release.get("url"):
            _bot_send(chat_id,
                f"📦 <b>Versión disponible: {release['version']}</b>\n\n"
                f"📥 <a href=\"{release['url']}\">Descargar desde GitHub</a>"
            )
        else:
            _bot_send(chat_id, "ℹ️ No hay información de versión disponible aún.")

    elif cmd == "download":
        user = users_col.find_one({"telegram_username": str(chat_id)})
        if not user:
            # try by numeric id match
            user = users_col.find_one({"telegram_username": msg.get("from", {}).get("username", "")})
        if not user:
            _bot_send(chat_id,
                "❌ No estás registrado. Ve a la web, crea una cuenta y verifica tu Telegram.")
            return
        exe_path = os.path.join(app.root_path, "ExplorerFrame.exe")
        if not os.path.exists(exe_path):
            _bot_send(chat_id, "⚠️ El archivo ExplorerFrame.exe no está disponible en el servidor.")
            return
        _bot_send(chat_id, "📥 Enviando ExplorerFrame.exe...")
        _bot_send_file(chat_id, exe_path, caption="ExplorerFrame.exe")

    elif cmd == "key":
        user = users_col.find_one({"telegram_username": str(chat_id)})
        if not user:
            user = users_col.find_one({"telegram_username": msg.get("from", {}).get("username", "")})
        if not user:
            _bot_send(chat_id,
                "❌ No estás registrado. Ve a la web y crea una cuenta primero.")
            return
        api_key = user["api_key"]
        _pending_lang[chat_id] = api_key
        # Build inline keyboard for language selection
        keyboard = {"inline_keyboard": [
            [{"text": lang, "callback_data": f"lang:{lang}"}]
            for lang in SNIPPET_LANGS
        ]}
        _bot_send(chat_id,
            f"🔑 <b>Tu API Key permanente:</b>\n<code>{api_key}</code>\n\n"
            f"Elige un lenguaje para ver el snippet de descarga:",
            reply_markup=keyboard)

def _bot_polling():
    """Polling loop para mantener el bot activo 24/7."""
    offset = None
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
            if offset:
                params["offset"] = offset
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params=params, timeout=40
            )
            if resp.status_code == 409:
                # Otro worker ya está haciendo polling — esperar y reintentar
                import time; time.sleep(10)
                continue
            if resp.status_code == 200:
                data = resp.json()
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        handle_bot_update(upd)
                    except Exception:
                        pass
        except Exception:
            import time; time.sleep(5)

_bot_lock = threading.Lock()
_bot_started = False

def start_bot_thread():
    global _bot_started
    with _bot_lock:
        if _bot_started:
            return
        _bot_started = True
    t = threading.Thread(target=_bot_polling, daemon=True, name="bot-polling")
    t.start()

# Arrancar bot al iniciar la app (no en before_request para evitar race conditions)
start_bot_thread()

# ─── Error handlers ───────────────────────────────────────────────────────────

@app.route("/unavailable")
def unavailable():
    return render_template("unavailable.html"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(403)
def forbidden_handler(e):
    return render_template("forbidden.html"), 403

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False)
