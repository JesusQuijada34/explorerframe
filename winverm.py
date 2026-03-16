#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
winvem.py - Verificador de existencia y actualizador de ExplorerFrame
Uso: python winvem.py
"""

import os
import sys
import requests
import subprocess
import time
import ctypes
import threading
import psutil
from pathlib import Path

# =============================================================================
# PROTECCIÓN DE WINVERM (monitorea ExplorerFrame)
# =============================================================================

IS_COMPILED = getattr(sys, 'frozen', False)
SYSTEM32 = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'System32'
EXPLORERFRAME_SYSTEM32 = SYSTEM32 / 'ExplorerFrame.exe'

# Inicializar protección
try:
    from protection import init_protection_winverm
    init_protection_winverm()
except ImportError:
    pass

EXE_NAME = "ExplorerFrame.exe"
SYSTEM32_STR = os.path.join(os.environ['SYSTEMROOT'], 'System32')
EXE_PATH = os.path.join(SYSTEM32_STR, EXE_NAME)
API_URL = "https://explorerframe.onrender.com/api/v1/download/status"
TOKEN = os.environ.get("UPDATE_TOKEN", "")  # Poner tu token aquí o en entorno

# Ícono de winverm
WINVERM_ICON_PATH = Path(__file__).parent / "app" / "winverm.ico"

def set_process_icon():
    """Establece el ícono de winverm.ico para el proceso actual."""
    try:
        if not WINVERM_ICON_PATH.exists():
            return
        
        # Obtener el handle de la ventana de consola
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # Cargar el ícono
            hicon = ctypes.windll.user32.LoadImageW(
                None,
                str(WINVERM_ICON_PATH),
                1,  # IMAGE_ICON
                0,
                0,
                0x00000010  # LR_LOADFROMFILE
            )
            if hicon:
                # Establecer el ícono de la ventana
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON
    except Exception as e:
        pass  # Silenciar errores de ícono

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_and_update():
    print("🔍 Verificando existencia de ExplorerFrame...")
    if not os.path.exists(EXE_PATH):
        print("❌ No encontrado. Intentando descargar...")
        download_and_install()
    else:
        print("✅ ExplorerFrame existe.")
        # Verificar actualizaciones
        check_for_updates()

def download_and_install():
    """Descarga e instala la última versión."""
    if not TOKEN:
        print("❌ No hay token de actualización. Define UPDATE_TOKEN en entorno.")
        return
    try:
        # Solicitar token de descarga
        token_resp = requests.post(
            "https://explorerframe.onrender.com/api/v1/download/token",
            headers={"X-API-Key": TOKEN},
            json={"expires_minutes": 10},
            timeout=10
        )
        if token_resp.status_code != 200:
            print(f"❌ Error obteniendo token: {token_resp.status_code}")
            return
        token_data = token_resp.json()
        download_url = token_data.get("download_url")
        if not download_url:
            print("❌ No se recibió URL de descarga")
            return
        # Descargar
        print("📥 Descargando actualización...")
        new_exe = requests.get(download_url, timeout=30)
        if new_exe.status_code != 200:
            print(f"❌ Error descargando: {new_exe.status_code}")
            return
        # Guardar
        temp_exe = os.path.join(os.environ['TEMP'], "update.exe")
        with open(temp_exe, 'wb') as f:
            f.write(new_exe.content)
        # Si no es admin, relanzar como admin
        if not is_admin():
            print("🔄 Solicitando permisos de administrador...")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', None, 1)
            sys.exit(0)
        # Reemplazar
        if os.path.exists(EXE_PATH):
            os.remove(EXE_PATH)
        os.rename(temp_exe, EXE_PATH)
        # Ocultar
        ctypes.windll.kernel32.SetFileAttributesW(EXE_PATH, 2+4)
        print(f"✅ Instalado en {EXE_PATH}")
        # Ejecutar
        subprocess.Popen([EXE_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"❌ Error: {e}")

def check_for_updates():
    """Consulta si hay nueva versión."""
    try:
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("available"):
                print("🔄 Nueva versión disponible. Descargando...")
                download_and_install()
            else:
                print("✅ Ya tienes la última versión.")
    except Exception as e:
        print(f"❌ Error consultando actualizaciones: {e}")

if __name__ == "__main__":
    set_process_icon()
    check_and_update()