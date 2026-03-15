#!/usr/bin/env python3
"""
Script para probar la conexión a MongoDB.
Ejecuta: python test_mongodb.py
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

print("🔍 Probando conexión a MongoDB...")
print("=" * 60)

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    print("❌ ERROR: MONGO_URI no está configurado en .env")
    exit(1)

print(f"📍 URI: {mongo_uri[:50]}...")

try:
    print("\n1️⃣  Intentando conectar sin opciones SSL...")
    client1 = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client1.admin.command('ping')
    print("✅ Conexión exitosa sin opciones SSL")
    client1.close()
except Exception as e:
    print(f"❌ Falló: {str(e)[:100]}")

try:
    print("\n2️⃣  Intentando conectar con tlsAllowInvalidCertificates=True...")
    client2 = MongoClient(
        mongo_uri,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000
    )
    client2.admin.command('ping')
    print("✅ Conexión exitosa con tlsAllowInvalidCertificates=True")
    client2.close()
except Exception as e:
    print(f"❌ Falló: {str(e)[:100]}")

try:
    print("\n3️⃣  Intentando conectar con tlsInsecure=True...")
    client3 = MongoClient(
        mongo_uri,
        tlsInsecure=True,
        serverSelectionTimeoutMS=5000
    )
    client3.admin.command('ping')
    print("✅ Conexión exitosa con tlsInsecure=True")
    client3.close()
except Exception as e:
    print(f"❌ Falló: {str(e)[:100]}")

try:
    print("\n4️⃣  Intentando conectar con tlsAllowInvalidCertificates + timeouts...")
    client4 = MongoClient(
        mongo_uri,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        retryWrites=False
    )
    client4.admin.command('ping')
    print("✅ Conexión exitosa con todas las opciones")
    
    # Probar acceso a la BD
    db = client4["explorerframe"]
    collections = db.list_collection_names()
    print(f"\n📦 Colecciones en 'explorerframe': {collections}")
    
    # Contar documentos
    users_count = db["users"].count_documents({})
    print(f"👥 Usuarios registrados: {users_count}")
    
    client4.close()
except Exception as e:
    print(f"❌ Falló: {str(e)[:100]}")

print("\n" + "=" * 60)
print("✅ Prueba completada")
