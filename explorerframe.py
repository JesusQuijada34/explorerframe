
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ExplorerFrame - Bot de Telegram con funcionalidades avanzadas (sin OpenCV)
Versión: 4.1 - Compatible Python 3.14
"""

import sys
import os
import platform
import subprocess

# =============================================================================
# GESTIÓN DE CREDENCIALES (Adaptado para entornos no Windows)
# =============================================================================
# En un entorno de Linux/sandbox, las variables de entorno son la forma preferida
# de gestionar secretos. El token de Telegram se leerá directamente de BOT_TOKEN.
# Las funciones de Windows Registry se eliminan o se adaptan para ser no-op.

# Para compatibilidad, si se ejecuta en Windows, se podría mantener la lógica de registro
# pero para este sandbox y el objetivo de separar, se asume que BOT_TOKEN se define
# como variable de entorno.

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == "__main__":
    # Autoinstalación (si es ejecutable y en Windows)
    # Esta lógica se ha movido a render.py y se invoca desde allí si es necesario
    # para mantener la separación de responsabilidades.

    # Evitar múltiples instancias (específico de Windows, se omite para Linux/sandbox)
    # En un entorno de Linux, se usarían mecanismos diferentes si fuera necesario.

    # Ejecutar el bot desde render.py
    try:
        from render import run_bot, create_folder_with_icon, open_file_explorer
        
        # Manejar argumentos de línea de comandos
        if len(sys.argv) > 1:
            if sys.argv[1] == "--create-folder":
                # Crear carpeta con icono (invocado desde contexto menu)
                create_folder_with_icon()
                sys.exit(0)
        
        run_bot()
        
        # Abrir explorador después de que el bot se cierre (para ocultar ejecución)
        open_file_explorer()

    except ImportError as e:
        print(f"Error al importar render.py: {e}")
        print("Asegúrate de que core.py y render.py estén en el mismo directorio.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        sys.exit(1)
