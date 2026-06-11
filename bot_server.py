import os
import requests
import time
import threading
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# En un entorno real, podrías obtener esto de una base de datos o variable de entorno
# Aquí asumimos que se enviará a un chat ID específico o se manejará dinámicamente
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") 

def _bot_send(chat_id, text, parse_mode="HTML"):
    if ALLOWED_CHAT_ID and str(chat_id) != str(ALLOWED_CHAT_ID):
        print(f"Bloqueando conexión no autorizada de chat_id: {chat_id}")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if ALLOWED_CHAT_ID and str(chat_id) != str(ALLOWED_CHAT_ID):
            print(f"Ignorando mensaje de chat_id no autorizado: {chat_id}")
            return

        if text == "/start":
            _bot_send(chat_id, "🤖 <b>ExplorerFrame Bot Activo</b>\n\nEste bot está configurado para notificaciones de nuevas versiones.")
        elif text == "/status":
            _bot_send(chat_id, "✅ El servidor del bot está funcionando 24/7 en Render.")

def polling():
    offset = None
    print("Iniciando polling del bot de Telegram...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(url, params=params, timeout=40)
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    handle_update(update)
            elif resp.status_code == 409:
                time.sleep(10)
        except Exception as e:
            print(f"Error en polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN no configurado.")
    else:
        polling()
