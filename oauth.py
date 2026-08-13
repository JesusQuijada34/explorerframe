"""MongoDB-backed OAuth 2.0 authorization-code helpers for ExplorerFrame."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlparse


def _db():
    # Import lazily to avoid app.py <-> oauth.py circular imports during startup.
    from app import get_mongo_db
    return get_mongo_db()


def _now():
    return datetime.utcnow()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_redirect(uri: str) -> bool:
    parsed = urlparse(uri)
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc)


def get_app(client_id: str):
    return _db()["oauth_apps"].find_one({"client_id": client_id})


def create_app(owner: str, name: str, redirect_uris: list[str]):
    redirect_uris = [str(uri).strip() for uri in redirect_uris if str(uri).strip()]
    if not redirect_uris or any(not _valid_redirect(uri) for uri in redirect_uris):
        raise ValueError("redirect_uris must contain valid HTTP(S) URLs")
    client_id = "app_" + secrets.token_urlsafe(18)
    client_secret = "secret_" + secrets.token_urlsafe(32)
    document = {
        "client_id": client_id,
        "client_secret_hash": _digest(client_secret),
        "owner": owner,
        "name": name.strip(),
        "redirect_uris": redirect_uris,
        "created_at": _now(),
    }
    _db()["oauth_apps"].insert_one(document)
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "name": document["name"],
        "redirect_uris": redirect_uris,
    }


def update_app(client_id: str, owner: str, **updates):
    allowed = {}
    if "name" in updates:
        name = str(updates["name"]).strip()
        if not name:
            raise ValueError("name cannot be empty")
        allowed["name"] = name
    if "redirect_uris" in updates:
        uris = [str(uri).strip() for uri in updates["redirect_uris"] if str(uri).strip()]
        if not uris or any(not _valid_redirect(uri) for uri in uris):
            raise ValueError("redirect_uris must contain valid HTTP(S) URLs")
        allowed["redirect_uris"] = uris
    if allowed:
        result = _db()["oauth_apps"].update_one({"client_id": client_id, "owner": owner}, {"$set": allowed})
        return result.modified_count == 1
    return False


def delete_app(client_id: str, owner: str):
    result = _db()["oauth_apps"].delete_one({"client_id": client_id, "owner": owner})
    _db()["oauth_codes"].delete_many({"client_id": client_id})
    _db()["oauth_tokens"].delete_many({"client_id": client_id})
    return result.deleted_count == 1


def get_user_apps(owner: str):
    return list(_db()["oauth_apps"].find({"owner": owner}).sort("created_at", -1))


def create_auth_code(client_id: str, user_id: str, redirect_uri: str, scope: str):
    app_info = get_app(client_id)
    if not app_info or redirect_uri not in app_info.get("redirect_uris", []):
        raise ValueError("invalid client or redirect URI")
    raw_code = "code_" + secrets.token_urlsafe(32)
    _db()["oauth_codes"].insert_one({
        "code_hash": _digest(raw_code),
        "client_id": client_id,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "expires_at": _now() + timedelta(minutes=5),
        "used": False,
    })
    return raw_code


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str):
    app_info = get_app(client_id)
    if not app_info or not secrets.compare_digest(app_info.get("client_secret_hash", ""), _digest(client_secret)):
        return None
    record = _db()["oauth_codes"].find_one_and_update(
        {"code_hash": _digest(code), "client_id": client_id, "redirect_uri": redirect_uri, "used": False, "expires_at": {"$gt": _now()}},
        {"$set": {"used": True, "used_at": _now()}},
    )
    if not record:
        return None
    access_token = "atk_" + secrets.token_urlsafe(32)
    _db()["oauth_tokens"].insert_one({
        "token_hash": _digest(access_token),
        "client_id": client_id,
        "user_id": record["user_id"],
        "scope": record.get("scope", "profile"),
        "created_at": _now(),
        "expires_at": _now() + timedelta(days=30),
        "revoked": False,
    })
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": 30 * 24 * 60 * 60, "scope": record.get("scope", "profile")}


def verify_access_token(access_token: str):
    record = _db()["oauth_tokens"].find_one({"token_hash": _digest(access_token), "revoked": False, "expires_at": {"$gt": _now()}})
    if not record:
        return None
    return {"user_id": record["user_id"], "client_id": record["client_id"], "scope": record.get("scope", "profile")}


def revoke_token(access_token: str):
    result = _db()["oauth_tokens"].update_one({"token_hash": _digest(access_token)}, {"$set": {"revoked": True, "revoked_at": _now()}})
    return result.modified_count == 1
