"""
Sistema de notificaciones para ExplorerFrame.
Maneja notificaciones del bot de Telegram y Web Push.
"""

import os
import requests
from pymongo import MongoClient

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")

def get_mongo_db():
    """Obtiene conexión a MongoDB."""
    try:
        client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
        client.admin.command('ping')
        return client["explorerframe"]
    except Exception as e:
        print(f"[MONGO ERROR] {str(e)}")
        return None

def send_telegram_notification(chat_id, message, parse_mode="HTML"):
    """Envía notificación por Telegram."""
    if not BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": parse_mode}, timeout=10)
        return True
    except Exception as e:
        print(f"[TELEGRAM NOTIFICATION ERROR] {str(e)}")
        return False

def notify_news_update(summary):
    """Notifica a todos los usuarios sobre actualización de noticias."""
    db = get_mongo_db()
    if not db:
        return False
    try:
        users = list(db["users"].find({}, {"telegram_username": 1}))
        message = f"📰 <b>Noticias Actualizadas</b>\n\n{summary}\n\nVisita el sitio para ver todas las novedades."
        for user in users:
            chat_id = user.get("telegram_username")
            if chat_id:
                send_telegram_notification(chat_id, message)
        return True
    except Exception as e:
        print(f"[NOTIFY NEWS ERROR] {str(e)}")
        return False

def notify_user_registered(chat_id, username):
    """Notifica cuando un usuario se registra."""
    message = f"✅ <b>Bienvenido a ExplorerFrame</b>\n\nTu cuenta <code>{username}</code> ha sido creada exitosamente.\n\nUsa /help para ver los comandos disponibles."
    return send_telegram_notification(chat_id, message)

def notify_user_login(chat_id, username):
    """Notifica cuando un usuario inicia sesión."""
    message = f"🔓 <b>Sesión iniciada</b>\n\nHas iniciado sesión como <code>{username}</code>."
    return send_telegram_notification(chat_id, message)

def notify_waiting_bot_start(chat_id, username):
    """Notifica que se está esperando que el usuario inicie el bot."""
    message = f"⏳ <b>Esperando confirmación</b>\n\nPara completar tu registro, inicia el bot escribiendo /start en @explorerframebot.\n\nEste mensaje expirará en 20 minutos."
    return send_telegram_notification(chat_id, message)
