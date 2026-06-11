import os
import time
import shutil
import platform
import zipfile
from datetime import datetime
import requests

def create_backup_archive(source_dir, destination_dir):
    """
    Crea un archivo ZIP de los archivos en source_dir y lo guarda en destination_dir.
    El nombre del ZIP será el nombre de la PC.
    """
    pc_name = platform.node()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{pc_name}_{timestamp}.zip"
    zip_filepath = os.path.join(destination_dir, zip_filename)

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, source_dir))
        print(f"Backup creado exitosamente: {zip_filepath}")
        return zip_filepath
    except Exception as e:
        print(f"Error al crear el backup: {e}")
        return None

def upload_file_gradually(filepath, server_url, api_key, chunk_size=1024*1024):
    """
    Sube un archivo al servidor de forma gradual (por chunks).
    """
    print(f"Iniciando subida gradual de {filepath} a {server_url}...")
    try:
        with open(filepath, 'rb') as f:
            offset = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                headers = {
                    'X-API-Key': api_key,
                    'X-File-Name': os.path.basename(filepath),
                    'X-Offset': str(offset),
                    'Content-Type': 'application/octet-stream'
                }
                response = requests.post(server_url, data=chunk, headers=headers, timeout=60)
                response.raise_for_status() # Lanza una excepción para códigos de estado HTTP erróneos
                
                print(f"Chunk de {len(chunk)} bytes subido. Offset: {offset}")
                offset += len(chunk)
                time.sleep(0.1) # Pequeña pausa para no saturar la red/servidor
        print(f"Archivo {filepath} subido completamente.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error de red o servidor al subir {filepath}: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al subir {filepath}: {e}")
        return False

def gradual_backup_task(source_dir, destination_dir, server_url, api_key, interval_seconds=3600):
    """
    Realiza backups graduales y los sube al servidor.
    """
    print(f"Iniciando tarea de backup gradual desde {source_dir} cada {interval_seconds} segundos.")
    while True:
        print(f"[{datetime.now()}] Realizando backup...")
        backup_file = create_backup_archive(source_dir, destination_dir)
        if backup_file:
            if upload_file_gradually(backup_file, server_url, api_key):
                os.remove(backup_file) # Eliminar el archivo local después de subirlo
                print(f"Archivo {backup_file} eliminado localmente después de la subida.")
            else:
                print(f"Fallo la subida de {backup_file}. Se mantendrá localmente para reintentar.")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    # Ejemplo de uso (estos valores deberían venir de variables de entorno o configuración)
    SOURCE_DIRECTORY = "./data_to_backup" # Directorio a respaldar
    BACKUP_DESTINATION = "./backups" # Donde se guardarán los ZIPs temporalmente
    SERVER_UPLOAD_URL = "http://your-server.com/upload" # URL de tu servidor de subida
    API_KEY = "your_api_key_here" # Tu API Key para autenticación

    os.makedirs(SOURCE_DIRECTORY, exist_ok=True)
    os.makedirs(BACKUP_DESTINATION, exist_ok=True)

    # Crear algunos archivos de prueba
    with open(os.path.join(SOURCE_DIRECTORY, "file1.txt"), "w") as f:
        f.write("Contenido del archivo 1")
    with open(os.path.join(SOURCE_DIRECTORY, "file2.log"), "w") as f:
        f.write("Contenido del archivo 2")

    print("Script de backup_task.py creado. Deberá ser integrado y ejecutado como un proceso en segundo plano o tarea programada.")
