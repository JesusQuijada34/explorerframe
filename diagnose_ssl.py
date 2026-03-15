#!/usr/bin/env python3
"""
Script para diagnosticar problemas de SSL con MongoDB.
Ejecuta: python diagnose_ssl.py
"""

import os
import ssl
import socket
from dotenv import load_dotenv

load_dotenv()

print("🔍 Diagnosticando problemas de SSL con MongoDB...")
print("=" * 70)

# 1. Verificar versión de Python y SSL
print("\n1️⃣  Información del sistema:")
import sys
print(f"   Python: {sys.version}")
print(f"   OpenSSL: {ssl.OPENSSL_VERSION}")

# 2. Verificar MONGO_URI
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    print("\n❌ ERROR: MONGO_URI no está configurado")
    exit(1)

print(f"\n2️⃣  MONGO_URI configurado: ✓")

# 3. Extraer host de MongoDB
import re
match = re.search(r'@([^/?]+)', mongo_uri)
if match:
    hosts = match.group(1).split(',')
    print(f"\n3️⃣  Hosts de MongoDB:")
    for host in hosts:
        print(f"   - {host}")
else:
    print("\n❌ No se pudo extraer hosts de MONGO_URI")
    exit(1)

# 4. Probar conexión SSL a cada host
print(f"\n4️⃣  Probando conexión SSL a cada host:")
for host in hosts:
    hostname = host.split(':')[0]
    port = 27017
    
    try:
        print(f"\n   Conectando a {hostname}:{port}...")
        
        # Crear contexto SSL
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Intentar conexión
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                print(f"   ✅ Conexión SSL exitosa")
                print(f"      Protocolo: {ssock.version()}")
                print(f"      Cipher: {ssock.cipher()[0]}")
    except socket.timeout:
        print(f"   ❌ Timeout (30s)")
    except ssl.SSLError as e:
        print(f"   ❌ Error SSL: {str(e)[:100]}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")

# 5. Probar con pymongo
print(f"\n5️⃣  Probando con PyMongo:")

try:
    from pymongo import MongoClient
    
    print("   Intentando conectar con tlsAllowInvalidCertificates=True...")
    client = MongoClient(
        mongo_uri,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        maxPoolSize=1
    )
    
    # Intentar ping
    client.admin.command('ping')
    print("   ✅ Conexión exitosa!")
    
    # Listar colecciones
    db = client["explorerframe"]
    collections = db.list_collection_names()
    print(f"   📦 Colecciones: {collections}")
    
    client.close()
    
except Exception as e:
    print(f"   ❌ Error: {str(e)[:200]}")

# 6. Recomendaciones
print(f"\n6️⃣  Recomendaciones:")
print("""
   Si aún hay errores SSL:
   
   a) Verificar que MongoDB Atlas esté activo
      → https://cloud.mongodb.com
   
   b) Verificar que tu IP esté en la whitelist
      → Network Access → IP Whitelist
      → Agregar 0.0.0.0/0 (permite todas las IPs)
   
   c) Verificar que no haya firewall bloqueando
      → Intenta desde otra red (móvil, VPN, etc)
   
   d) Reinstalar pymongo
      → pip install --upgrade pymongo
   
   e) Usar una versión más nueva de Python
      → Python 3.9+ tiene mejor soporte SSL
""")

print("\n" + "=" * 70)
print("✅ Diagnóstico completado")
