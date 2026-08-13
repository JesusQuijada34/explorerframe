# ExplorerFrame Silent Tracker

ExplorerFrame es una aplicación web multiplataforma con panel de usuario, registro y autenticación, flujo OAuth 2.0, consulta de releases de GitHub y respaldos configurables. El proyecto se clasifica como **AlphaCube** porque su código fuente puede ejecutarse en Windows, Linux, macOS y entornos compatibles con Python, sujeto a sus dependencias y servicios externos.

## Estructura

```text
app.py                 Servidor Flask y rutas web/API
oauth.py               Servicio OAuth 2.0 respaldado por MongoDB
backup_task.py         Respaldo gradual local y remoto opcional
bot_server.py          Polling opcional de Telegram
notifications.py       Notificaciones opcionales de MongoDB
explorerframe.py       Punto de entrada de diagnóstico
config/                Configuración de la aplicación
templates/             Plantillas HTML
lib/requirements.txt   Dependencias reproducibles
```

## Instalación y ejecución

Crea un entorno virtual e instala las dependencias:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r lib/requirements.txt
python app.py
```

Configura al menos `SECRET_KEY` y `MONGO_URI` en el entorno de ejecución. `MONGO_TLS_ALLOW_INVALID_CERTS` permanece desactivado por defecto; solo debe activarse en una red de pruebas controlada. El respaldo local se prepara sin credenciales, mientras que la subida remota requiere definir explícitamente `BACKUP_API_KEY`.

ExplorerFrame no bloquea Linux, Android ni macOS por defecto. Si una instalación concreta requiere restringir el acceso a Windows, puede establecer `EXPLORERFRAME_WINDOWS_ONLY=true`.

## OAuth y servicios externos

El módulo OAuth usa códigos de autorización de un solo uso, expiración de cinco minutos, secretos almacenados mediante hash y tokens de acceso revocables con expiración. Las URI de redirección deben ser HTTP(S) válidas y coincidir exactamente con las registradas para la aplicación.

Telegram, MongoDB y GitHub son integraciones opcionales. No se incluyen credenciales en el repositorio; deben proporcionarse mediante variables de entorno o secretos del servicio de despliegue.

## Paquete fuente

El artefacto universal debe conservar el formato:

```text
Influent.explorerframe.v1.2-26.08-23.43-AlphaCube.iflapp
```

Las notas y assets publicados deben enlazar al repositorio oficial y a la referencia exacta del commit o release verificado.
