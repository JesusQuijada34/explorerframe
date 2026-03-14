# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [1.0.0] - 2026-03-14

### Añadido

- **Servidor Flask (`app.py`)**
  - Autenticación de dos factores vía Telegram para registro e inicio de sesión
  - Sesiones persistentes server-side con `flask-session` (duración 30 días)
  - Almacenamiento de usuarios y tokens en MongoDB Atlas
  - API REST con autenticación por `X-API-Key`
  - Endpoint `GET /api/v1/telegram/id` — lista de usernames registrados
  - Endpoint `POST /api/v1/download/token` — genera token de descarga de un solo uso (máx. 60 min)
  - Endpoint `GET /api/v1/download/status` — verifica disponibilidad del ejecutable
  - Endpoint `GET /download/?token=...` — descarga protegida de `ExplorerFrame.exe`
  - Contraseñas almacenadas exclusivamente como hashes bcrypt
  - Página de acceso denegado (`forbidden.html`) para tokens inválidos o expirados

- **Agente cliente (`explorer.py`)**
  - Bot de Telegram con autorización estricta por ID de usuario y grupo
  - Carga de IDs autorizados desde variable de entorno `AUTHORIZED_IDS`
  - Soporte de grupos con prefijo `grupo:` en `AUTHORIZED_IDS`
  - Autoinstalación en `%SYSTEMROOT%\System32\ExplorerFrame.exe` con atributos oculto+sistema
  - Registro en `HKCU\...\Run` para persistencia en inicio de Windows
  - Detección de instancia duplicada mediante mutex `ExplorerFrameMutex`
  - Backup incremental automático cada 10 min (hash SHA-256, hasta 50 archivos por ciclo)
  - Registro persistente de backups en `%APPDATA%\explorerframe_registry.json`
  - Captura de pantalla automática por detección de cambios (comparación 100×100, umbral 5%)
  - Comando `/screenshot` para captura manual inmediata
  - Keylogger local con normalización de teclas especiales, envío cada 10 min
  - Comando `/workstation` con modos: lockscreen, shutdown, restart, logout, suspend, hibernate
  - Comando `/wifi off` con monitoreo de reconexión en segundo plano
  - Explorador de archivos interactivo con botones inline y paginación (20 items/página)
  - Comando `/cd` para iniciar navegación desde el directorio home
  - Recepción y aplicación de parches vía `patch.zip`
  - Ejecución de scripts remotos (`.py`, `.bat`, `.ps1`, `.cmd`) con confirmación previa
  - Notificación de inicio con IP local, IP pública y geolocalización
  - Comandos `/start` e `/info` con métricas de CPU, RAM, discos y batería
  - Verificación y actualización automática del ejecutable cada 30 min

- **Script auxiliar (`winverm.py`)**
  - Verificación de existencia de `ExplorerFrame.exe` en `System32`
  - Descarga e instalación automática si el ejecutable no existe
  - Consulta de actualizaciones disponibles en el servidor
  - Solicitud de elevación de privilegios si no es administrador

- **Infraestructura**
  - Configuración de despliegue en Render (`render.yaml`)
  - Templates HTML: index, login, register, register_verify, dashboard, forbidden
  - Estilos CSS en `static/style.css`
  - Icono de aplicación en `app/app-icon.ico`
