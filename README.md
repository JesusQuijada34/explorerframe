# ExplorerFrame

Herramienta de administración remota personal para equipos Windows. Permite monitorear y controlar máquinas de forma remota a través de un bot de Telegram.

## Componentes

- **`explorer.py`** — Agente cliente que corre en el equipo administrado. Gestiona el bot de Telegram, capturas de pantalla, keylogger, backup incremental y control del sistema.
- **`app.py`** — Servidor web Flask desplegado en la nube. Gestiona autenticación de usuarios, distribución del ejecutable y tokens de descarga.
- **`winverm.py`** — Script auxiliar que verifica la existencia del ejecutable y aplica actualizaciones automáticas.

## Características

- Autenticación de dos factores vía Telegram (registro e inicio de sesión)
- Autorización estricta por ID de usuario o grupo de Telegram
- Backup incremental automático (solo archivos nuevos/modificados, cada 10 min)
- Capturas de pantalla automáticas por detección de cambios (umbral 5%)
- Keylogger local con envío periódico cada 10 min
- Control de energía remoto: bloquear, apagar, reiniciar, suspender, hibernar
- Control de conectividad WiFi con monitoreo de reconexión
- Explorador de archivos interactivo con botones inline de Telegram
- Aplicación de parches y ejecución de scripts remotos
- Autoinstalación en `System32` con persistencia en inicio de Windows
- Actualización automática del agente cada 30 min
- API REST con autenticación por API Key

## Requisitos

```
flask
flask-session
gunicorn
pymongo[srv]
python-dotenv
requests
bcrypt
python-telegram-bot[job-queue]
apscheduler>=3.10.0
pytz tzlocal pillow keyboard pywin32 psutil numpy
```

## Configuración

Copia `.env.example` y rellena las variables:

```env
SECRET_KEY=...
MONGO_URI=mongodb+srv://...
TELEGRAM_BOT_TOKEN=...
BOT_TOKEN=...
AUTHORIZED_IDS=123456789,grupo:-100987654321
UPDATE_TOKEN=...
```

## Despliegue (Render)

El servidor se despliega automáticamente con `render.yaml`. El agente cliente se compila con PyInstaller y se distribuye desde el panel web.

## Uso del agente

1. Ejecuta `explorer.py` (o el `.exe` compilado) en el equipo a administrar.
2. El agente se autoinstala en `System32` y se registra en el inicio de Windows.
3. Controla el equipo desde Telegram con los comandos disponibles.

### Comandos del bot

| Comando | Descripción |
|---|---|
| `/start` | Info del sistema (IP, CPU, RAM, discos, batería) |
| `/info` | Métricas actuales del sistema |
| `/screenshot` | Captura de pantalla inmediata |
| `/cd` | Explorador de archivos interactivo |
| `/download` | Descarga el archivo seleccionado |
| `/workstation mode:<acción>` | Control de energía (lockscreen/shutdown/restart/logout/suspend/hibernate) |
| `/wifi off` | Apaga el WiFi y notifica al reconectar |

## Licencia

Ver [LICENSE](LICENSE).
