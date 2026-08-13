# ExplorerFrame Silent Tracker

**Identidad del paquete:** `influent.explorerframe.v1.2-26.08-21.56`
**Autor:** `JesusQuijada34`
**Plataforma:** `AlphaCube`
**Descripción:** Estructura reparada por MoonFix

## Estructura PackageMaker 3.2.7

Este repositorio fue normalizado mediante **MoonFix**, usando la estructura de PackageMaker 3.2.7. El paquete público debe conservar `details.xml`, `version.res`, `autorun`, `autorun.bat`, `.storedetail`, `updater.py`, `config/settings.json`, los marcadores `.container` y los archivos de documentación correspondientes. El publisher oficial es `influent` y la versión pública no contiene sufijo de plataforma.

## Instalación y ejecución

Instala las dependencias declaradas en `lib/requirements.txt` cuando exista y ejecuta el entrypoint real del proyecto. En Linux, los comandos privilegiados son específicos de Danenone y no deben trasladarse a Windows. En proyectos AlphaCube, la validación Windows debe realizarse con el `buildthis` oficial de PackageMaker.

## Validación

La fuente debe pasar compilación sintáctica, pruebas funcionales disponibles, comprobación de identidad XML, protección contra traversal en ZIP y llamadas seguras a subprocess. Los artefactos `.iflapp` deben ser generados por PackageMaker; los paquetes Debian deben usar el nombre canónico `influent.explorerframe.v1.2-26.08-21.56_ARCH.deb`.

## Release

El tag y el título del release deben ser exactamente `v1.2-26.08-21.56`. Los assets deben usar el nombre canónico del paquete y una extensión objetiva. No se permite publicar un release AlphaCube que contenga únicamente el build Linux.

## Referencia original

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
