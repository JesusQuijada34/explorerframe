# Novedades — ExplorerFrame v1.2

**Publicado:** 14 de marzo de 2026

---

## 🎉 Principales Mejoras en v1.2

### 🔧 Correcciones Críticas

#### Servidor Web (app.py)
- **HTTP 500 Fix**: El directorio de sesiones ahora se crea antes de que `Session(app)` se inicialice, previniendo crashes en la primera solicitud en Render
- **Timeout de Gunicorn**: `render.yaml` ahora inicia gunicorn con `--workers 1 --timeout 120` para prevenir que los workers se maten durante long-poll de 30s
- **Bot 24/7**: El polling del bot de Telegram ahora corre en un thread daemon iniciado al cargar el módulo; `threading.Lock` previene threads duplicados en reinicios de gunicorn; conflictos 409 se manejan con backoff

#### Agente Cliente (explorer.py)
- **Soporte dotenv**: Carga `.env` al iniciar; `BOT_TOKEN`, `API_URL`, `OWNER_ID` se leen del entorno
- **Fix de header de autenticación**: Cambio de `Authorization: Bearer` → `X-API-Key` en solicitudes de token de actualización
- **Fix de limpieza de keylog**: `keylog.txt` ahora se vacía solo después de un envío exitoso, no incondicionalmente
- **Advertencia de inicio**: Registra una advertencia si `authorized_users` está vacío al arrancar

#### Winverm (winverm.py)
- **Fix de header de autenticación**: Cambio de `Authorization: Bearer` → `X-API-Key`

---

### ✨ Nuevas Características

#### Dashboard Web
- **Redirección inteligente**: `/`, `/login/`, `/register/` ahora redirigen a `/dashboard/` cuando hay una sesión activa
- **Bloqueo de plataformas**: Linux, macOS, Android, iOS se bloquean en páginas públicas y se redirigen a `/unavailable` (HTTP 403)
- **Guía de onboarding**: Instrucciones paso a paso para registro, comandos del bot y duración de sesión
- **Meta tags mejorados**: `og:image` y Twitter Card para vista previa en redes sociales
- **Páginas de error**: `404.html` (no encontrado) y `unavailable.html` (bloqueo de plataforma) añadidas

#### Gestor de Actualizaciones
- **Seguimiento de versiones en GitHub**: Lee `details.xml` de la rama `main` del repositorio para obtener la versión actual
- **Descarga automática de parches**: Obtiene el release de GitHub correspondiente y localiza `EF.zip` (bundle de parches con `ExplorerFrame.exe` + `Winverm.exe`)
- **Validación de URLs**: Valida la URL de descarga con una solicitud HEAD antes de cachear
- **Notificaciones de actualización**: Cuando la versión en `details.xml` cambia, todos los usuarios registrados reciben un mensaje de Telegram con el enlace de descarga y el changelog del release como archivo `.md`

#### Nuevos Comandos del Bot
- **`/help`**: Rediseñado con instrucciones completas de onboarding, lista de comandos disponibles e información de versión actual
- **`/version`**: Nuevo comando — muestra la versión actual y enlace directo de descarga de `EF.zip`
- **`/key`**: Muestra la API Key permanente + menú inline de idiomas (Python, Bash, PowerShell, Node.js, PHP) con snippets listos para usar
- **`/download`**: Envía `ExplorerFrame.exe` directamente al chat para usuarios registrados

#### API REST Mejorada
- **Snippets de código**: Dashboard ahora muestra la URL real del servidor en lugar de un placeholder
- **Múltiples lenguajes**: Generador de snippets para Python, Bash, PowerShell, Node.js y PHP

---

### 🔐 Mejoras de Seguridad

- **SESSION_COOKIE_SECURE**: Habilitado solo cuando `FLASK_ENV=production`
- **OWNER_ID**: Siempre se añade a `authorized_users` independientemente del valor de `AUTHORIZED_IDS`
- **Validación mejorada**: Mejor manejo de errores de autenticación y autorización

---

### 📦 Cambios de Configuración

#### `.env`
- Todas las variables ahora están documentadas
- Nuevas variables: `APP_BASE_URL`, `FLASK_ENV`, `GITHUB_REPO`

#### `render.yaml`
- Añadidas variables: `APP_BASE_URL`, `FLASK_ENV=production`
- Flags de gunicorn: `--workers 1 --timeout 120 --keep-alive 5`

#### `details.xml`
- Declaración `encoding="UTF-8"` añadida
- Formato consistente

---

### 🔄 Cambios Técnicos

#### explorer.py
- **`check_for_updates` → `check_for_updates_job`**: Convertido a `async def` con firma `context: ContextTypes.DEFAULT_TYPE`, registrado directamente en `job_queue` (sin más wrapper `asyncio.create_task`)

---

## 📊 Estadísticas de la Versión

- **Commits desde v1.0.0**: 50+
- **Archivos modificados**: 12
- **Nuevas características**: 8
- **Bugs corregidos**: 6
- **Mejoras de seguridad**: 4

---

## 🚀 Próximas Mejoras Planeadas

- [ ] Soporte para múltiples idiomas en la interfaz web
- [ ] Dashboard con gráficos de uso del sistema
- [ ] Historial de acciones y auditoría
- [ ] Soporte para múltiples agentes por usuario
- [ ] Integración con webhooks personalizados
- [ ] Modo de demostración para pruebas

---

## 📝 Notas de Compatibilidad

- **Python**: 3.8 o superior
- **Windows**: 7 o superior
- **MongoDB**: 4.0 o superior
- **Telegram Bot API**: Versión 6.0+

---

## 🙏 Agradecimientos

Gracias a todos los usuarios que reportaron bugs y sugirieron mejoras en esta versión.

**Última actualización:** 16 de marzo de 2026
