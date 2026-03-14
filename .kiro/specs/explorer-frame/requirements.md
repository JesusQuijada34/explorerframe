# Documento de Requisitos

## Introducción

ExplorerFrame es una herramienta de administración remota personal para equipos Windows. Permite al propietario del equipo monitorear y controlar sus máquinas de forma remota a través de un bot de Telegram, realizando respaldos incrementales automáticos, capturas de pantalla, registro de actividad local, control de energía y aplicación de parches/actualizaciones. El sistema se compone de dos partes: un agente cliente que corre en el equipo administrado (`explorer.py`) y un servidor web Flask (`app.py`) que gestiona autenticación, distribución del ejecutable y tokens de descarga.

## Glosario

- **Agent**: El proceso cliente (`ExplorerFrame.exe`) que corre en el equipo administrado y ejecuta todas las funciones de monitoreo y control.
- **Server**: La aplicación Flask (`app.py`) desplegada en la nube que gestiona usuarios, autenticación y distribución del ejecutable.
- **Bot**: El bot de Telegram integrado en el Agent que recibe comandos y envía notificaciones.
- **Authorized_User**: Usuario de Telegram cuyo ID numérico está registrado en la configuración del Agent y tiene permiso para enviar comandos.
- **Token de descarga**: Cadena aleatoria de un solo uso generada por el Server para autorizar la descarga del ejecutable del Agent.
- **Respaldo incremental**: Copia de seguridad que solo incluye los archivos modificados desde el último respaldo completo o incremental.
- **Keylogger**: Módulo del Agent que registra las pulsaciones de teclado de forma local para auditoría del propietario.
- **Snapshot**: Captura de pantalla tomada por el Agent bajo demanda o de forma periódica.
- **Patch**: Actualización del ejecutable del Agent distribuida desde el Server.
- **Authorized_Group**: Grupo de Telegram cuyo ID está en la lista de grupos autorizados del Agent.
- **Backup_Registry**: Archivo JSON persistente en disco que almacena el hash SHA-256 de cada archivo ya respaldado.
- **Patch**: Archivo ZIP enviado por Telegram con nombre `patch.zip` que contiene un ejecutable de actualización.
- **Download_Token**: Token de un solo uso generado por el Server para autorizar la descarga del ejecutable.
- **API_Key**: Clave secreta de 64 caracteres hexadecimales asignada a cada usuario registrado para autenticar llamadas a la API REST.
- **Keylog_File**: Archivo de texto local donde el Agent registra las pulsaciones de teclado del equipo administrado.
- **Screenshot**: Imagen PNG de la pantalla completa capturada por el Agent.
- **Winverm**: Script auxiliar (`winverm.py`) que verifica la existencia del ejecutable y aplica actualizaciones.

---

## Requisitos

### Requisito 1: Autorización estricta de comandos

**User Story:** Como propietario del equipo, quiero que solo mis usuarios y grupos de Telegram predefinidos puedan enviar comandos al Agent, para que ningún tercero pueda controlar mis máquinas.

#### Criterios de Aceptación

1. WHEN el Bot recibe cualquier comando o mensaje, THE Bot SHALL verificar si el ID del remitente está en la lista de Authorized_Users o si el ID del chat está en la lista de Authorized_Groups antes de ejecutar ninguna acción.
2. IF el remitente no está en la lista de Authorized_Users ni en la lista de Authorized_Groups, THEN THE Bot SHALL responder con el mensaje "No autorizado" y no ejecutar ninguna acción adicional.
3. WHEN el Agent inicia, THE Agent SHALL obtener la lista de IDs autorizados desde la variable de entorno `AUTHORIZED_IDS` antes de aceptar cualquier comando.
4. THE Agent SHALL soportar IDs de grupos con el prefijo `grupo:` en la variable `AUTHORIZED_IDS` para distinguirlos de IDs de usuarios individuales.
5. IF la variable de entorno `AUTHORIZED_IDS` está vacía al iniciar, THEN THE Agent SHALL iniciar con listas de autorización vacías y rechazar todos los comandos entrantes.

---

### Requisito 2: Autenticación de usuarios en el Server

**User Story:** Como propietario, quiero registrarme e iniciar sesión en el Server usando verificación de dos factores vía Telegram, para que el acceso al panel web esté protegido.

#### Criterios de Aceptación

1. WHEN un usuario envía el formulario de registro con nombre de usuario y contraseña, THE Server SHALL generar un token aleatorio de 32 bytes, almacenarlo con expiración de 20 minutos y enviarlo al chat de Telegram del usuario.
2. WHEN el usuario ingresa el token de verificación correcto antes de su expiración, THE Server SHALL crear la cuenta con la con.
8. THE Server SHALL almacenar las contraseñas exclusivamente como hashes bcrypt y nunca en texto plano.

---

### Requisito 3: Gestión de API Keys y tokens de descarga

**User Story:** Como propietario, quiero que el Agent pueda descargar actualizaciones del Server usando tokens de un solo uso, para que las descargas no sean accesibles públicamente.

#### Criterios de Aceptación

1. WHEN el Server recibe una solicitud POST a `/api/v1/download/token` con una API_Key válida, THE Server SHALL generar un Download_Token de un solo uso con expiración configurable de hasta 60 minutos.
2. WHEN el Server recibe una solicitud GET a `/download/` con un Download_Token válido y no expirado, THE Server SHALL servir el archivo `ExplorerFrame.exe` y eliminar el token inmediatamente después de la descarga.
3. IF el Download_Token ha expirado o no existe, THEN THE Server SHALL responder con HTTP 403 y renderizar la plantilla `forbidden.html`.
4. THE Server SHALL exponer el endpoint `/api/v1/telegram/id` que devuelve los usernames de todos los usuarios registrados separados por comas, accesible solo con API_Key válida.
5. THE Server SHALL exponer el endpoint `/api/v1/download/status` que indica si el archivo `ExplorerFrame.exe` está disponible en el servidor, accesible solo con API_Key válida.
6. IF una solicitud a cualquier endpoint de la API no incluye una API_Key válida en el header `X-API-Key` o en el parámetro `api_key`, THEN THE Server SHALL responder con HTTP 403 y el cuerpo `{"error": "Forbidden"}`.

---

### Requisito 4: Autoinstalación y persistencia del Agent

**User Story:** Como propietario, quiero que el Agent se instale automáticamente en `System32` y se registre en el inicio de Windows, para que persista entre reinicios sin intervención manual.

#### Criterios de Aceptación

1. WHEN el Agent se ejecuta como archivo compilado (`frozen`) y no está instalado en `System32`, THE Agent SHALL copiarse a `%SYSTEMROOT%\System32\ExplorerFrame.exe` con atributos de sistema y oculto.
2. WHEN el Agent realiza la autoinstalación, THE Agent SHALL registrar la ruta del ejecutable en `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` para ejecutarse al inicio de sesión.
3. IF el Agent no tiene privilegios de administrador al intentar autoinstalarse, THEN THE Agent SHALL relanzarse solicitando elevación de privilegios mediante `ShellExecuteW` con el verbo `runas`.
4. WHEN el Agent detecta que ya existe una instancia en ejecución mediante el mutex `ExplorerFrameMutex`, THE Agent SHALL lanzar `explorer.exe` y terminar sin iniciar una segunda instancia.
5. WHEN el Agent completa la autoinstalación, THE Agent SHALL lanzar la nueva copia desde `System32` y terminar el proceso original.

---

### Requisito 5: Respaldo incremental automático de archivos

**User Story:** Como propietario, quiero que el Agent respalde automáticamente solo los archivos nuevos o modificados del directorio home, para mantener copias actualizadas sin transferir archivos duplicados.

#### Criterios de Aceptación

1. THE Agent SHALL ejecutar el proceso de respaldo automático cada 600 segundos de forma continua mientras esté activo.
2. WHEN el Agent ejecuta un respaldo, THE Agent SHALL calcular el hash SHA-256 de cada archivo encontrado y compararlo con el hash almacenado en el Backup_Registry para determinar si es nuevo o modificado.
3. WHEN el Agent detecta archivos nuevos o modificados, THE Agent SHALL empaquetar hasta 50 archivos en un archivo ZIP con estructura de rutas relativas al directorio home y enviarlo al primer Authorized_User disponible.
4. WHEN el Agent envía exitosamente un archivo en el respaldo, THE Agent SHALL actualizar el Backup_Registry con el nuevo hash SHA-256 del archivo.
5. THE Agent SHALL persistir el Backup_Registry en disco en `%APPDATA%\explorerframe_registry.json` para sobrevivir reinicios.
6. THE Agent SHALL excluir los subdirectorios `AppData\Local` y `AppData\Roaming` del escaneo de respaldo para evitar archivos de sistema y temporales.
7. IF no hay archivos nuevos o modificados en el ciclo de respaldo, THEN THE Agent SHALL omitir el envío sin generar ningún mensaje.

---

### Requisito 6: Captura de pantalla manual y automática por detección de cambios

**User Story:** Como propietario, quiero recibir capturas de pantalla automáticamente cuando detecte cambios significativos en la pantalla, y también poder solicitarlas manualmente, para monitorear la actividad visual del equipo.

#### Criterios de Aceptación

1. THE Agent SHALL verificar cambios en la pantalla cada 5 segundos comparando la captura actual con la anterior.
2. WHEN el Agent detecta que más del 5% de los píxeles de una versión reducida a 100×100 de la pantalla difieren en más de 30 unidades de intensidad respecto a la captura anterior, THE Agent SHALL enviar la captura actual como imagen PNG al primer Authorized_User disponible.
3. WHEN un Authorized_User envía el comando `/screenshot`, THE Bot SHALL capturar la pantalla completa inmediatamente y enviarla como imagen PNG al solicitante.
4. THE Agent SHALL almacenar las capturas temporalmente en `%APPDATA%\explorerframe_temp\` y eliminarlas después de enviarlas.
5. IF la captura anterior no existe al iniciar la comparación, THEN THE Agent SHALL almacenar la captura actual como referencia sin enviarla.

---

### Requisito 7: Registro de actividad de teclado (Keylogger local)

**User Story:** Como propietario, quiero que el Agent registre las pulsaciones de teclado del equipo y me las envíe periódicamente, para auditar la actividad local de mis propias máquinas.

#### Criterios de Aceptación

1. THE Agent SHALL registrar cada pulsación de teclado en `%APPDATA%\keylog.txt` con marca de tiempo en formato `YYYY-MM-DD HH:MM:SS` mientras esté activo.
2. THE Agent SHALL normalizar las teclas especiales en el registro: la tecla `space` como espacio, `enter` como salto de línea, `backspace` como `[BORRAR]`, y cualquier tecla de nombre mayor a un carácter como `[NOMBRE_EN_MAYÚSCULAS]`.
3. THE Agent SHALL enviar el archivo `keylog.txt` al primer Authorized_User disponible cada 600 segundos.
4. WHEN el Agent envía el archivo de keylog exitosamente, THE Agent SHALL vaciar el contenido del archivo `keylog.txt` sin eliminarlo.
5. IF el archivo `keylog.txt` no existe en el momento del envío programado, THEN THE Agent SHALL omitir el envío sin generar error.

---

### Requisito 8: Control de energía y estado de la estación de trabajo

**User Story:** Como propietario, quiero poder bloquear, apagar, reiniciar, suspender o hibernar mis equipos remotamente desde Telegram, para gestionar el estado de energía sin acceso físico.

#### Criterios de Aceptación

1. WHEN un Authorized_User envía `/workstation mode: lockscreen`, THE Bot SHALL bloquear la sesión de Windows inmediatamente usando `LockWorkStation`.
2. WHEN un Authorized_User envía `/workstation mode: shutdown`, THE Bot SHALL iniciar el apagado del equipo con un retardo de 5 segundos.
3. WHEN un Authorized_User envía `/workstation mode: restart`, THE Bot SHALL iniciar el reinicio del equipo con un retardo de 5 segundos.
4. WHEN un Authorized_User envía `/workstation mode: logout`, THE Bot SHALL cerrar la sesión del usuario actual.
5. WHEN un Authorized_User envía `/workstation mode: suspend`, THE Bot SHALL suspender el equipo usando `SetSuspendState`.
6. WHEN un Authorized_User envía `/workstation mode: hibernate`, THE Bot SHALL hibernar el equipo.
7. IF el modo especificado en el comando `/workstation` no es uno de los valores reconocidos, THEN THE Bot SHALL responder con el mensaje de uso correcto del comando.
8. IF ocurre un error al ejecutar cualquier operación de control de energía, THEN THE Bot SHALL responder con el mensaje de error específico recibido del sistema operativo.

---

### Requisito 9: Control de conectividad WiFi

**User Story:** Como propietario, quiero poder apagar el WiFi remotamente y recibir una notificación cuando el equipo recupere conectividad a internet, para gestionar el acceso a red de mis equipos.

#### Criterios de Aceptación

1. WHEN un Authorized_User envía `/wifi off`, THE Bot SHALL deshabilitar el adaptador de red "Wi-Fi" usando `netsh` y confirmar la acción al usuario.
2. WHEN el Agent deshabilita el WiFi, THE Agent SHALL iniciar un proceso de monitoreo en segundo plano que verifique la conectividad a internet cada 10 segundos.
3. WHEN el proceso de monitoreo detecta conectividad a internet exitosa, THE Agent SHALL habilitar el adaptador "Wi-Fi" y notificar al chat que inició el comando con el mensaje "Conexión a internet restablecida".

---

### Requisito 10: Explorador de archivos interactivo

**User Story:** Como propietario, quiero navegar por el sistema de archivos del equipo remoto usando botones inline de Telegram y descargar archivos individuales, para acceder a cualquier archivo sin conocer su ruta exacta.

#### Criterios de Aceptación

1. WHEN un Authorized_User envía el comando `/cd`, THE Bot SHALL mostrar el contenido del directorio home del usuario con un teclado inline de botones navegables.
2. THE Bot SHALL mostrar hasta 20 elementos por página en el explorador, con botones de paginación para avanzar y retroceder.
3. WHEN el usuario selecciona una carpeta en el explorador, THE Bot SHALL actualizar el mensaje mostrando el contenido de esa carpeta.
4. WHEN el usuario selecciona un archivo en el explorador, THE Bot SHALL almacenar la ruta del archivo en el estado del usuario para su posterior descarga.
5. WHEN un Authorized_User envía el comando `/download` con una ruta de archivo válida o con un archivo previamente seleccionado en el explorador, THE Bot SHALL enviar el archivo como documento de Telegram.
6. IF la ruta especificada en `/download` no corresponde a un archivo existente, THEN THE Bot SHALL responder con el mensaje "Archivo no encontrado".
7. THE Bot SHALL incluir un botón "Subir" en el explorador para navegar al directorio padre, excepto cuando ya se esté en el directorio raíz.

---

### Requisito 11: Aplicación de parches y ejecución de scripts remotos

**User Story:** Como propietario, quiero poder enviar un archivo ZIP de parche o un script por Telegram para actualizar el Agent o ejecutar comandos en el equipo, para mantener el software actualizado y automatizar tareas remotamente.

#### Criterios de Aceptación

1. WHEN un Authorized_User envía un archivo con nombre `patch.zip` al Bot, THE Agent SHALL extraer el primer archivo `.exe` encontrado dentro del ZIP, reemplazar el ejecutable en `System32` y reiniciar el proceso.
2. WHEN un Authorized_User envía un archivo con extensión `.py`, `.bat`, `.ps1` o `.cmd`, THE Bot SHALL preguntar al usuario si desea ejecutarlo antes de proceder.
3. WHEN el usuario confirma la ejecución de un script con "sí", "si" o "yes", THE Agent SHALL ejecutar el script con el intérprete correspondiente, capturar la salida estándar y de error, y responder con los primeros 3000 caracteres del resultado.
4. WHEN el usuario responde negativamente a la ejecución de un script, THE Bot SHALL responder "Ejecución cancelada" y descartar el script pendiente.
5. IF ocurre un error al aplicar el parche `patch.zip`, THEN THE Bot SHALL responder con el mensaje de error específico y no reiniciar el proceso.
6. IF el archivo `patch.zip` no contiene ningún archivo `.exe`, THEN THE Bot SHALL responder con el mensaje "No se encontró un ejecutable en el zip".
7. WHEN el Agent recibe cualquier documento, THE Agent SHALL guardarlo en `%APPDATA%\` y confirmar la ruta de guardado al usuario.

---

### Requisito 12: Verificación y actualización automática del ejecutable (Winverm)

**User Story:** Como propietario, quiero que el script auxiliar `winverm.py` verifique si el ejecutable está instalado y lo descargue o actualice automáticamente desde el Server, para garantizar que el Agent siempre esté presente y actualizado.

#### Criterios de Aceptación

1. WHEN el Winverm se ejecuta y el archivo `ExplorerFrame.exe` no existe en `System32`, THE Winverm SHALL solicitar un Download_Token al Server usando el `UPDATE_TOKEN` de entorno y descargar el ejecutable.
2. WHEN el Winverm se ejecuta y el archivo `ExplorerFrame.exe` ya existe en `System32`, THE Winverm SHALL consultar el endpoint `/api/v1/download/status` para verificar si hay una versión disponible en el Server.
3. WHEN el Server indica que hay una versión disponible, THE Winverm SHALL descargar y reemplazar el ejecutable existente usando un Download_Token de un solo uso.
4. IF el Winverm no tiene privilegios de administrador al intentar instalar o actualizar el ejecutable, THEN THE Winverm SHALL relanzarse solicitando elevación de privilegios mediante `ShellExecuteW` con el verbo `runas`.
5. IF la variable de entorno `UPDATE_TOKEN` está vacía, THEN THE Winverm SHALL mostrar el mensaje "No hay token de actualización. Define UPDATE_TOKEN en entorno" y terminar sin intentar la descarga.
6. WHEN el Winverm instala exitosamente el ejecutable, THE Winverm SHALL aplicar los atributos de sistema y oculto al archivo y lanzar el proceso.

---

### Requisito 13: Notificaciones de inicio y métricas del sistema

**User Story:** Como propietario, quiero recibir una notificación con información del sistema cuando el Agent inicia por primera vez, para conocer el estado del equipo al conectarme.

#### Criterios de Aceptación

1. WHEN el Agent inicia, THE Agent SHALL enviar el mensaje "ExplorerFrame iniciado" a todos los Authorized_Users.
2. WHEN un Authorized_User envía el comando `/start` por primera vez en la sesión, THE Bot SHALL responder con la IP local, IP pública, ubicación geográfica aproximada, información de CPU, RAM, discos y batería del equipo.
3. WHEN un Authorized_User envía el comando `/info`, THE Bot SHALL responder con las métricas actuales de CPU, RAM, discos y batería del equipo.
4. THE Bot SHALL obtener la IP pública consultando `https://api.ipify.org` y la geolocalización aproximada consultando `http://ip-api.com/json/{ip}`.
5. IF ocurre un error al obtener la información de red o geolocalización, THEN THE Bot SHALL mostrar "Desconocida" o "No disponible" en los campos correspondientes sin interrumpir el resto de la respuesta.

---

### Requisito 14: Actualización automática periódica del Agent

**User Story:** Como propietario, quiero que el Agent verifique automáticamente si hay una nueva versión disponible en el Server y se actualice sin intervención manual, para mantener el software siempre actualizado.

#### Criterios de Aceptación

1. THE Agent SHALL verificar la disponibilidad de una nueva versión en el Server cada 1800 segundos de forma continua mientras esté activo.
2. WHEN el Server indica que hay una versión disponible y el Agent tiene un `UPDATE_TOKEN` configurado, THE Agent SHALL solicitar un Download_Token de un solo uso, descargar el nuevo ejecutable y reemplazar el archivo en `System32`.
3. WHEN el Agent descarga y reemplaza el ejecutable exitosamente, THE Agent SHALL lanzar el nuevo proceso y terminar el proceso actual.
4. IF el Agent no tiene configurado el `UPDATE_TOKEN` en el entorno, THEN THE Agent SHALL registrar el mensaje "No hay token de actualización" y omitir la actualización sin interrumpir el funcionamiento normal.
5. IF ocurre cualquier error durante el proceso de actualización automática, THEN THE Agent SHALL registrar el error y continuar operando con la versión actual.
traseña hasheada usando bcrypt y asignar una API_Key única de 64 caracteres hexadecimales.
3. IF el token de verificación ha expirado, THEN THE Server SHALL eliminar el token pendiente y mostrar el mensaje "Token expirado. Vuelve a registrarte."
4. IF el token de verificación es incorrecto, THEN THE Server SHALL mostrar el mensaje "Token incorrecto. Inténtalo de nuevo." sin eliminar el token pendiente.
5. WHEN el usuario completa el registro exitosamente, THE Server SHALL redirigir al usuario a la página de inicio de sesión.
6. WHEN un usuario registrado envía el formulario de inicio de sesión con credenciales válidas, THE Server SHALL generar un token de sesión, almacenarlo en una cookie segura y redirigir al panel principal.
7. IF las credenciales de inicio de sesión son incorrectas, THEN THE Server SHALL mostrar el mensaje "Credenciales inválidas" sin revelar si el usuario existe o no.
