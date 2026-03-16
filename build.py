#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script para compilar todos los ejecutables con PyInstaller
Uso: python build.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Ejecuta un comando y reporta el resultado."""
    print(f"\n{'='*70}")
    print(f"🔨 {description}")
    print(f"{'='*70}")
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        return False

def clean_build_artifacts():
    """Limpia artefactos de compilaciones anteriores."""
    print("\n🧹 Limpiando artefactos anteriores...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removido: {dir_name}")

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    BUILD SCRIPT - ExplorerFrame                    ║
║                                                                    ║
║  Este script compila los tres ejecutables:                        ║
║  1. protection.exe   - Sistema de protección mutua                ║
║  2. ExplorerFrame.exe - Bot de Telegram                           ║
║  3. Winverm.exe      - Verificador de ExplorerFrame               ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
        print(f"✅ PyInstaller encontrado: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller no está instalado")
        print("   Instálalo con: pip install pyinstaller")
        sys.exit(1)
    
    # Verificar que los archivos .spec existan
    spec_files = ['protection.spec', 'explorerframe.spec', 'winverm.spec']
    for spec_file in spec_files:
        if not os.path.exists(spec_file):
            print(f"❌ Archivo no encontrado: {spec_file}")
            sys.exit(1)
    
    print("✅ Todos los archivos .spec encontrados")
    
    # Limpiar artefactos anteriores
    clean_build_artifacts()
    
    # Compilar cada ejecutable
    builds = [
        ("pyinstaller protection.spec", "Compilando protection.exe"),
        ("pyinstaller explorerframe.spec", "Compilando ExplorerFrame.exe"),
        ("pyinstaller winverm.spec", "Compilando Winverm.exe"),
    ]
    
    results = []
    for cmd, description in builds:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Resumen
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE COMPILACIÓN")
    print(f"{'='*70}")
    
    all_success = True
    for description, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {description}")
        if not success:
            all_success = False
    
    if all_success:
        print(f"\n{'='*70}")
        print("🎉 ¡COMPILACIÓN EXITOSA!")
        print(f"{'='*70}")
        print("\n📁 Los ejecutables están en: ./dist/")
        print("\n📋 Próximos pasos:")
        print("  1. Copiar los .exe a una carpeta segura")
        print("  2. Ejecutar protection.exe para iniciar el sistema")
        print("  3. Los archivos se copiarán a System32 automáticamente")
        print("  4. Se registrarán en el inicio de Windows")
        print("  5. Se crearán entradas en el contexto menu")
        return 0
    else:
        print(f"\n{'='*70}")
        print("❌ COMPILACIÓN FALLIDA")
        print(f"{'='*70}")
        print("\nRevisa los errores arriba para más detalles.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
