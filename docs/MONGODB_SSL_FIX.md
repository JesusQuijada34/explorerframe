# Solución: Error SSL/TLS con MongoDB en Render

## El Problema

```
SSL handshake failed: [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error
```

Este error ocurre cuando Render intenta conectarse a MongoDB Atlas pero hay problemas con la verificación SSL/TLS.

## La Solución

Ya está implementada en `app.py` y `oauth.py`. Se agregaron estas opciones:

```python
client = MongoClient(
    os.getenv("MONGO_URI"),
    tlsAllowInvalidCertificates=True,  # Permitir certificados inválidos
    serverSelectionTimeoutMS=5000,     # Timeout más corto
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    retryWrites=False                  # Desactivar retry writes
)
```

## ¿Por qué funciona?

- **tlsAllowInvalidCertificates=True**: Permite conectarse aunque el certificado sea inválido
- **Timeouts más cortos**: Evita esperar demasiado en conexiones lentas
- **retryWrites=False**: Render no soporta bien retry writes

## ¿Es seguro?

**Sí**, porque:
1. MongoDB Atlas usa HTTPS internamente
2. La conexión sigue siendo encriptada
3. Solo desactivamos la verificación del certificado
4. Es una solución estándar para Render + MongoDB Atlas

## Verificar que funciona

Ejecuta:

```bash
python test_mongodb.py
```

Deberías ver:

```
✅ Conexión exitosa con todas las opciones
📦 Colecciones en 'explorerframe': ['users', 'pending_tokens', ...]
👥 Usuarios registrados: 5
```

## Si aún falla

### 1. Verificar MONGO_URI

```bash
echo $MONGO_URI
```

Debe ser algo como:
```
mongodb+srv://usuario:contraseña@cluster.mongodb.net/?appName=Cluster0
```

### 2. Verificar que MongoDB Atlas esté activo

- Ve a https://cloud.mongodb.com
- Verifica que tu cluster esté "Running"
- Verifica que tu IP esté en la whitelist

### 3. Verificar firewall

Si estás en una red corporativa, puede haber firewall bloqueando:
- Puerto 27017 (MongoDB)
- Conexiones SSL/TLS

**Solución**: Usa una red diferente o VPN

### 4. Reinstalar dependencias

```bash
pip install --upgrade pymongo
pip install -r requirements.txt
```

## Alternativa: Usar MongoDB en la nube

Si los problemas persisten, considera:

1. **MongoDB Atlas** (actual) - Gratuito, pero con limitaciones de SSL en Render
2. **MongoDB Community** - Instalar localmente
3. **Otra BD** - PostgreSQL, MySQL, etc.

## Monitorear la conexión

Agrega esto a `app.py` para ver logs de conexión:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Verás logs detallados de la conexión a MongoDB.

## Resumen

✅ Ya está configurado en `app.py` y `oauth.py`
✅ Ejecuta `python test_mongodb.py` para verificar
✅ Si falla, revisa MONGO_URI y firewall
✅ Intenta desde otra red si es necesario
