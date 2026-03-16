"""
OAuth 2.0 implementation for ExplorerFrame.
Allows third-party apps to authenticate users via ExplorerFrame.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient

# Conexión lazy: se conecta solo cuando se necesita
_mongo_client = None

def get_mongo_db():
    """Obtiene la conexión a MongoDB (lazy initialization)"""
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                os.getenv("MONGO_URI"),
                tlsAllowInvalidCertificates=True,
                # Timeouts recomendados para Render + Atlas
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=15000,
                # Pool de conexiones
                maxPoolSize=5,
                minPoolSize=0,
                # Render no soporta bien retry writes
                retryWrites=False,
                # Heartbeat para mantener conexión viva
                heartbeatFrequencyMS=10000,
                directConnection=False
            )
            # Verificar que funciona
            _mongo_client.admin.command('ping')
        except Exception as e:
            print(f"[MONGO ERROR] {str(e)}")
            _mongo_client = None
            raise
    return _mongo_client["explorerframe"]

# Lazy collection wrapper
class LazyCollection:
    def __init__(self, collection_name):
        self.collection_name = collection_name
    
    def __getattr__(self, name):
        return getattr(get_mongo_db()[self.collection_name], name)

oauth_apps = LazyCollection("oauth_apps")
oauth_codes = LazyCollection("oauth_codes")
oauth_tokens = LazyCollection("oauth_tokens")

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def generate_client_id():
    """Genera un Client ID único."""
    return f"app_{secrets.token_hex(16)}"

def generate_client_secret():
    """Genera un Client Secret seguro."""
    return secrets.token_urlsafe(48)

def generate_auth_code():
    """Genera un código de autorización (válido 10 minutos)."""
    return secrets.token_urlsafe(32)

def generate_access_token():
    """Genera un access token (válido 30 días)."""
    return secrets.token_urlsafe(48)

def create_app(user_id, app_name, redirect_uris):
    """
    Crea una nueva aplicación OAuth.
    
    Args:
        user_id: ID del usuario propietario
        app_name: Nombre de la aplicación
        redirect_uris: Lista de URIs permitidas para redirección
    
    Returns:
        dict con client_id y client_secret
    """
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    
    app_doc = {
        "client_id": client_id,
        "client_secret": hashlib.sha256(client_secret.encode()).hexdigest(),  # Hash del secret
        "owner": user_id,
        "name": app_name,
        "redirect_uris": redirect_uris,
        "created_at": utcnow(),
        "active": True
    }
    
    oauth_apps.insert_one(app_doc)
    return {"client_id": client_id, "client_secret": client_secret}

def get_app(client_id):
    """Obtiene una app por client_id."""
    return oauth_apps.find_one({"client_id": client_id, "active": True})

def verify_client_secret(client_id, client_secret):
    """Verifica que el client_secret sea correcto."""
    app = get_app(client_id)
    if not app:
        return False
    secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
    return app["client_secret"] == secret_hash

def create_auth_code(client_id, user_id, redirect_uri, scope="profile"):
    """
    Crea un código de autorización.
    
    Args:
        client_id: ID de la aplicación
        user_id: ID del usuario autenticado
        redirect_uri: URI a la que redirigir
        scope: Permisos solicitados
    
    Returns:
        Código de autorización
    """
    code = generate_auth_code()
    expires = utcnow() + timedelta(minutes=10)
    
    oauth_codes.insert_one({
        "code": code,
        "client_id": client_id,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "expires": expires,
        "used": False
    })
    
    return code

def exchange_code_for_token(client_id, client_secret, code, redirect_uri):
    """
    Intercambia un código de autorización por un access token.
    
    Returns:
        dict con access_token y user_id, o None si falla
    """
    # Verificar credenciales
    if not verify_client_secret(client_id, client_secret):
        return None
    
    # Buscar el código
    code_doc = oauth_codes.find_one({
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "used": False
    })
    
    if not code_doc or utcnow() > code_doc["expires"]:
        return None
    
    # Marcar código como usado
    oauth_codes.update_one({"_id": code_doc["_id"]}, {"$set": {"used": True}})
    
    # Crear access token
    access_token = generate_access_token()
    expires = utcnow() + timedelta(days=30)
    
    oauth_tokens.insert_one({
        "token": hashlib.sha256(access_token.encode()).hexdigest(),
        "client_id": client_id,
        "user_id": code_doc["user_id"],
        "scope": code_doc["scope"],
        "expires": expires,
        "created_at": utcnow()
    })
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 30 * 24 * 60 * 60,
        "user_id": code_doc["user_id"]
    }

def verify_access_token(access_token):
    """
    Verifica un access token y devuelve los datos del usuario.
    
    Returns:
        dict con user_id y scope, o None si inválido
    """
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    token_doc = oauth_tokens.find_one({"token": token_hash})
    
    if not token_doc or utcnow() > token_doc["expires"]:
        return None
    
    return {
        "user_id": token_doc["user_id"],
        "scope": token_doc["scope"],
        "client_id": token_doc["client_id"]
    }

def revoke_token(access_token):
    """Revoca un access token."""
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    oauth_tokens.delete_one({"token": token_hash})

def get_user_apps(user_id):
    """Obtiene todas las apps de un usuario."""
    return list(oauth_apps.find({"owner": user_id}, {"client_secret": 0}))

def update_app(client_id, user_id, **updates):
    """Actualiza una app (solo el propietario puede)."""
    app = oauth_apps.find_one({"client_id": client_id, "owner": user_id})
    if not app:
        return False
    oauth_apps.update_one({"_id": app["_id"]}, {"$set": updates})
    return True

def delete_app(client_id, user_id):
    """Elimina una app (solo el propietario puede)."""
    app = oauth_apps.find_one({"client_id": client_id, "owner": user_id})
    if not app:
        return False
    oauth_apps.update_one({"_id": app["_id"]}, {"$set": {"active": False}})
    return True
