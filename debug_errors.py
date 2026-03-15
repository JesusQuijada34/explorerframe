"""
Script para monitorear errores en tiempo real.
Ejecuta esto en una terminal separada mientras pruebas.
"""

import subprocess
import sys
import time

def tail_logs():
    """Muestra los últimos errores del servidor."""
    print("🔍 Monitoreando errores del servidor...")
    print("=" * 60)
    
    try:
        # Ejecutar Flask con output en tiempo real
        process = subprocess.Popen(
            [sys.executable, "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in process.stdout:
            print(line.rstrip())
            
            # Resaltar errores
            if "[ERROR" in line or "Traceback" in line or "Exception" in line:
                print("⚠️  ERROR DETECTADO ⚠️")
                
    except KeyboardInterrupt:
        print("\n\n✓ Monitoreo detenido")
        process.terminate()

if __name__ == "__main__":
    tail_logs()
