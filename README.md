# ExplorerFrame v1.2

**Herramienta de administración remota personal para equipos Windows** — Monitorea y controla máquinas de forma remota a través de un bot de Telegram con autenticación segura, backups automáticos y control total del sistema.

**Versión actual:** `v1.2-26.03-18.22` | **Última actualización:** 14 de marzo de 2026

---

## 🎯 Descripción General

ExplorerFrame es una solución completa de administración remota diseñada para usuarios que necesitan monitoreo y control seguro de equipos Windows. Combina un agente cliente ligero con un servidor web robusto y un bot de Telegram inteligente.

### Componentes Principales

| Componente | Descripción |
|---|---|
| **`explorer.py`** | Agente cliente que se ejecuta en el equipo administrado. Gestiona el bot de Telegram, capturas de pantalla, keylogger, backup incremental y control del sistema. |
| **`app.py`** | Servidor web Flask desplegado en la nube. Gestiona autenticación de usuarios, distribución del ejecutable, tokens de descarga y notificaciones de actualizaciones. |
| **`winverm.py`** | Script auxiliar que verifica la existencia del ejecutable y aplica actualizaciones automáticas. |

---

## ✨ Características Principales

### Seguridad y Autenticación
- ✅ Autenticación de dos factores vía Telegram (registro e inicio de sesión)
- ✅ Autorización estricta por ID de usuario o grupo de Telegram
- ✅ API REST con autenticación por API Key
- ✅ Tokens de descarga de un solo uso
- ✅ Encriptación de contraseñas con bcrypt

### Monitoreo y Captura
- ✅ Backup incremental automático (solo archivos nuevos/modificados, cada 10 min)
- ✅ Capturas de pantalla automáticas por detección de cambios (umbral 5%)
- ✅ Keylogger local con envío periódico cada 10 min
- ✅ Métricas del sistema en tiempo real (CPU, RAM, discos, batería)

### Control Remoto
- ✅ Control de energía remoto: bloquear, apagar, reiniciar, suspender, hibernar
- ✅ Control de conectividad WiFi con monitoreo de reconexión
- ✅ Explorador de archivos interactivo con botones inline de Telegram
- ✅ Descarga de archivos directa desde Telegram
- ✅ Aplicación de parches y ejecución de scripts remotos

### Instalación y Actualización
- ✅ Autoinstalación en `System32` con persistencia en inicio de Windows
- ✅ Actualización automática del agente cada 30 min
- ✅ Notificaciones de nuevas versiones en Telegram
- ✅ Descarga automática de parches desde GitHub

### Interfaz Web
- ✅ Dashboard inteligente con guía de onboarding
- ✅ Generador de snippets de código (Python, Bash, PowerShell, Node.js, PHP)
- ✅ Visualización de versión actual y enlaces de descarga
- ✅ Bloqueo de plataformas no Windows (Linux, macOS, Android, iOS)

---

## 📋 Requisitos del Sistema

### Servidor
- Python 3.8+
- MongoDB Atlas (o MongoDB local)
- Gunicorn (para producción)
- Render.com (recomendado para despliegue)

### Agente Cliente
- Windows 7 o superior
- Python 3.8+ (o ejecutable compilado)
- Conexión a Internet

### Dependencias Python

```
flask==2.3.0
flask-session==0.5.0
gunicorn==21.0.0
pymongo[srv]==4.4.0
python-dotenv==1.0.0
requests==2.31.0
bcrypt==4.0.1
python-telegram-bot[job-queue]==20.0
apscheduler>=3.10.0
pytz
tzlocal
pillow
keyboard
pywin32
psutil
numpy
```

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/JesusQuijada34/ExplorerFrame.git
cd ExplorerFrame
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y rellena las variables:

```env
# Flask
SECRET_KEY=tu_clave_secreta_aqui
FLASK_ENV=production

# MongoDB
MONGO_URI=mongodb+srv://usuario:contraseña@cluster.mongodb.net/explorerframe

# Telegram
TELEGRAM_BOT_TOKEN=tu_token_del_bot_aqui
BOT_TOKEN=tu_token_del_bot_aqui

# Autorización
AUTHORIZED_IDS=123456789,grupo:-100987654321
OWNER_ID=tu_id_de_telegram

# Actualización
UPDATE_TOKEN=tu_token_de_actualizacion
GITHUB_REPO=JesusQuijada34/ExplorerFrame

# URLs
APP_BASE_URL=https://tu-dominio.com
API_URL=https://tu-dominio.com/api
```

### 4. Desplegar el servidor

#### Opción A: Render.com (Recomendado)

```bash
git push origin main
```

El servidor se despliega automáticamente usando `render.yaml`.

#### Opción B: Local

```bash
python app.py
```

### 5. Ejecutar el agente cliente

En el equipo a administrar:

```bash
python explorer.py
```

O descarga el ejecutable compilado desde el dashboard web.

---

## 🤖 Comandos del Bot de Telegram

| Comando | Descripción |
|---|---|
| `/start` | Información del sistema (IP, CPU, RAM, discos, batería) |
| `/help` | Guía completa de comandos disponibles |
| `/info` | Métricas actuales del sistema |
| `/screenshot` | Captura de pantalla inmediata |
| `/cd` | Explorador de archivos interactivo |
| `/download` | Descarga el archivo seleccionado |
| `/version` | Muestra la versión actual y enlace de descarga |
| `/key` | Muestra la API Key permanente con snippets de código |
| `/workstation mode:<acción>` | Control de energía (lockscreen/shutdown/restart/logout/suspend/hibernate) |
| `/wifi off` | Apaga el WiFi y notifica al reconectar |

---

## 📊 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot                              │
│              (python-telegram-bot + APScheduler)             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼──────────┐
│  Agent Client    │    │  Web Server       │
│  (explorer.py)   │    │  (app.py + Flask) │
│                  │    │                   │
│ • Keylogger      │    │ • Auth (2FA)      │
│ • Screenshots    │    │ • Dashboard       │
│ • Backup         │    │ • API REST        │
│ • Power Control  │    │ • File Download   │
│ • WiFi Control   │    │ • Update Manager  │
└────────┬─────────┘    └────────┬──────────┘
         │                       │
         └───────────┬───────────┘
                     │
            ┌────────▼────────┐
            │   MongoDB       │
            │   (Atlas)       │
            └─────────────────┘
```

---

## 🔐 Seguridad

- **Autenticación 2FA**: Todos los usuarios deben verificarse a través de Telegram
- **API Key**: Tokens únicos y permanentes para acceso programático
- **Tokens de descarga**: Válidos solo una vez y con expiración
- **Encriptación**: Contraseñas hasheadas con bcrypt
- **Bloqueo de plataformas**: Solo Windows puede acceder al agente
- **Autorización granular**: Control por ID de usuario o grupo de Telegram

---

## 📝 Documentación Adicional

- [CHANGELOG.md](CHANGELOG.md) — Historial completo de cambios
- [NEWS.md](NEWS.md) — Novedades y mejoras recientes
- [RELEASE_NOTES.md](RELEASE_NOTES.md) — Notas de la versión actual
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Detalles técnicos de la arquitectura
- [docs/QUICK_START.md](docs/QUICK_START.md) — Guía rápida de inicio
- [docs/OAUTH_SETUP.md](docs/OAUTH_SETUP.md) — Configuración de OAuth (opcional)

---

## 📄 Licencia

Este proyecto está bajo la licencia especificada en [LICENSE](LICENSE).

**Autor:** JesusQuijada34  
**Empresa:** Influent  
**Plataforma:** Knosthalij

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📞 Soporte

Para reportar bugs o solicitar features, abre un issue en el repositorio.

**Última actualización:** 16 de marzo de 2026
