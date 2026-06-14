"""
OAuth 2.0 implementation for ExplorerFrame.
Provides OAuth authorization code flow for third-party app integrations.
"""
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

# Lazy MongoDB connection
_mongo_client = None

def get_mongo_db():
    """Get MongoDB database connection (lazy initialization)"""
    global _mongo_client
    if _mongo_client is None:
        try:
            from pymongo import MongoClient
            _mongo_client = MongoClient(
                os.getenv("MONGO_URI"),
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                minPoolSize=1,
                retryWrites=False,
                maxIdleTimeMS=45000
            )
            _mongo_client.admin.command('ping')
        except Exception as e:
            print(f"[MONGO ERROR in oauth] {str(e)}")
            raise
    return _mongo_client["explorerframe"]


def _get_apps_col():
    """Get OAuth apps collection"""
    return get_mongo_db()["oauth_apps"]

def _get_codes_col():
    """Get authorization codes collection"""
    return get_mongo_db()["oauth_codes"]

def _get_tokens_col():
    """Get access tokens collection"""
    return get_mongo_db()["oauth_tokens"]


# ─── App Management ────────────────────────────────────────────────────────────

def get_app(client_id):
    """Get OAuth app by client_id"""
    try:
        return _get_apps_col().find_one({"client_id": client_id})
    except Exception as e:
        print(f"[OAUTH get_app ERROR] {str(e)}")
        return None


def create_app(user, name, redirect_uris):
    """Create a new OAuth application"""
    client_id = f"app_{secrets.token_hex(16)}"
    client_secret = secrets.token_hex(32)
    
    app_doc = {
        "client_id": client_id,
        "client_secret": client_secret,
        "name": name,
        "redirect_uris": redirect_uris,
        "owner": user,
        "created_at": datetime.now(timezone.utc)
    }
    
    _get_apps_col().insert_one(app_doc)
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "name": name,
        "redirect_uris": redirect_uris
    }


def update_app(client_id, user, **updates):
    """Update an OAuth application"""
    result = _get_apps_col().update_one(
        {"client_id": client_id, "owner": user},
        {"$set": updates}
    )
    return result.modified_count > 0


def delete_app(client_id, user):
    """Delete an OAuth application"""
    result = _get_apps_col().delete_one(
        {"client_id": client_id, "owner": user}
    )
    return result.deleted_count > 0


def get_user_apps(user):
    """Get all OAuth apps owned by a user"""
    return list(_get_apps_col().find({"owner": user}))


# ─── Authorization Code Flow ───────────────────────────────────────────────────

def create_auth_code(client_id, user, redirect_uri, scope):
    """
    Create an authorization code.
    The code expires in 10 minutes.
    """
    code = secrets.token_urlsafe(32)
    
    code_doc = {
        "code": code,
        "client_id": client_id,
        "user": user,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    
    _get_codes_col().insert_one(code_doc)
    
    return code


def exchange_code_for_token(client_id, client_secret, code, redirect_uri):
    """
    Exchange an authorization code for an access token.
    Returns access token data or None if invalid.
    """
    # Find and validate the code
    code_doc = _get_codes_col().find_one({
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri
    })
    
    if not code_doc:
        return None
    
    # Check expiration
    if datetime.now(timezone.utc) > code_doc["expires_at"]:
        _get_codes_col().delete_one({"_id": code_doc["_id"]})
        return None
    
    # Validate client secret
    app = get_app(client_id)
    if not app or app["client_secret"] != client_secret:
        return None
    
    # Delete the used code
    _get_codes_col().delete_one({"_id": code_doc["_id"]})
    
    # Generate access token
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    
    # Store token
    token_doc = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "user": code_doc["user"],
        "scope": code_doc["scope"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    _get_tokens_col().insert_one(token_doc)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": code_doc["scope"]
    }


# ─── Token Verification ────────────────────────────────────────────────────────

def verify_access_token(access_token):
    """
    Verify an access token and return the token data.
    Returns None if invalid or expired.
    """
    token_doc = _get_tokens_col().find_one({
        "access_token": access_token
    })
    
    if not token_doc:
        return None
    
    # Check expiration
    if datetime.now(timezone.utc) > token_doc["expires_at"]:
        _get_tokens_col().delete_one({"_id": token_doc["_id"]})
        return None
    
    return {
        "user_id": token_doc["user"],
        "client_id": token_doc["client_id"],
        "scope": token_doc["scope"]
    }


def revoke_token(access_token):
    """Revoke an access token"""
    _get_tokens_col().delete_one({"access_token": access_token})
    return True


# ─── Token Refresh (optional extension) ──────────────────────────────────────

def refresh_access_token(refresh_token):
    """
    Refresh an access token using a refresh token.
    Returns new access token data or None if invalid.
    """
    # Find the old token by refresh token
    old_token = _get_tokens_col().find_one({"refresh_token": refresh_token})
    
    if not old_token:
        return None
    
    # Delete old token
    _get_tokens_col().delete_one({"_id": old_token["_id"]})
    
    # Generate new tokens
    access_token = secrets.token_urlsafe(32)
    new_refresh_token = secrets.token_urlsafe(32)
    
    # Store new token
    token_doc = {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "client_id": old_token["client_id"],
        "user": old_token["user"],
        "scope": old_token["scope"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    _get_tokens_col().insert_one(token_doc)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": old_token["scope"]
    }
