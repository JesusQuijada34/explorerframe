# Debugging de Errores 500

Si ves un error 500 al iniciar sesión, ahora puedes ver exactamente qué pasó.

## 1. Ver el error en la página

Cuando ocurra un error 500, la página mostrará:
- **Detalles del error**: Mensaje específico de qué falló
- **Stack trace**: Línea por línea dónde ocurrió el error

Esto te ayuda a identificar si es:
- Problema de conexión a MongoDB
- Error en JWT/sesiones
- Error en Telegram
- Problema de datos

## 2. Ver logs en la consola

Si ejecutas Flask localmente, verás los errores en la terminal:

```bash
python app.py
```

Busca líneas como:
```
[ERROR 500] ...
[LOGIN ERROR] ...
[REGISTER ERROR] ...
[SESSION LOAD ERROR] ...
[SESSION SAVE ERROR] ...
```

## 3. Errores Comunes

### Error: "SSL handshake failed" / "tlsv1 alert internal error"
**Causa**: Problema de SSL/TLS con MongoDB Atlas en Render
**Solución**: Ya está configurado en `app.py` y `oauth.py` con:
```python
tlsAllowInvalidCertificates=True
tlsInsecure=True
```

**Si aún falla:**
1. Ejecuta: `python test_mongodb.py`
2. Verifica que MongoDB Atlas esté activo
3. Intenta desde otra red (puede ser firewall)

### Error: "name 'datetime' is not defined"
**Causa**: Falta importar `datetime` en `oauth.py`
**Solución**: Verificar que los imports estén correctos

### Error: "MongoClient is not defined"
**Causa**: Falta importar `MongoClient` en `oauth.py`
**Solución**: Verificar que los imports estén correctos

### Error: "MONGO_URI not found"
**Causa**: Variable de entorno no configurada
**Solución**: Verificar `.env` tiene `MONGO_URI`

### Error: "connection refused"
**Causa**: MongoDB no está disponible
**Solución**: Verificar que MongoDB Atlas esté activo

### Error: "invalid_grant" en OAuth
**Causa**: Código expirado o ya usado
**Solución**: Generar un nuevo código

## 4. Checklist de Debugging

- [ ] ¿Está configurado `.env` correctamente?
- [ ] ¿Está MongoDB Atlas activo?
- [ ] ¿Está el bot de Telegram activo?
- [ ] ¿Están todas las dependencias instaladas? (`pip install -r requirements.txt`)
- [ ] ¿Hay errores en la consola?
- [ ] ¿El error aparece en la página 500?

## 5. Logs Detallados

Cada endpoint ahora registra errores con:
- Nombre del endpoint
- Mensaje de error
- Stack trace completo

Busca en los logs:
```
[REGISTER ERROR]
[LOGIN ERROR]
[LOGIN_VERIFY ERROR]
[REGISTER_VERIFY ERROR]
[SESSION LOAD ERROR]
[SESSION SAVE ERROR]
[ERROR 500]
```

## 6. Monitorear en Tiempo Real

Ejecuta en una terminal separada:

```bash
python debug_errors.py
```

Esto mostrará todos los errores mientras pruebas.

## 7. Verificar Conexión a MongoDB

Ejecuta este script para probar la conexión:

```bash
python test_mongodb.py
```

Esto probará diferentes configuraciones de SSL y te dirá cuál funciona.

Si todo falla, verifica:
1. `MONGO_URI` en `.env` es correcto
2. MongoDB Atlas está activo
3. Tu IP está en la whitelist de MongoDB Atlas
4. No hay firewall bloqueando la conexión

## 8. Verificar JWT

```python
import jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
secret = os.getenv("SECRET_KEY")

# Crear token
payload = {"user": "test", "exp": datetime.now(timezone.utc) + timedelta(days=30)}
token = jwt.encode(payload, secret, algorithm="HS256")
print("Token:", token)

# Decodificar
decoded = jwt.decode(token, secret, algorithms=["HS256"])
print("Decodificado:", decoded)
```

## 9. Verificar Telegram

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Verificar que el token es válido
url = f"https://api.telegram.org/bot{bot_token}/getMe"
response = requests.get(url)
print(response.json())
```

## 10. Reportar Errores

Si encuentras un error que no puedes resolver:

1. Copia el **stack trace completo** de la página 500
2. Copia los **logs de la consola**
3. Verifica tu **`.env`** (sin exponer datos sensibles)
4. Describe **qué estabas haciendo** cuando ocurrió el error
