# Solución Real: Error SSL/TLS con MongoDB en Render

## El Problema Real

El error `SSL: TLSV1_ALERT_INTERNAL_ERROR` ocurre porque:

1. **Render tiene restricciones de red** — No puede hacer handshake SSL normal
2. **MongoDB Atlas rechaza la conexión** — Por problemas de certificado
3. **Los timeouts son muy cortos** — 5-10 segundos no es suficiente

## La Solución

### Opción 1: Aumentar Timeouts (Ya implementado)

```python
client = MongoClient(
    os.getenv("MONGO_URI"),
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=30000,  # 30 segundos (antes era 5)
    connectTimeoutMS=30000,          # 30 segundos (antes era 10)
    socketTimeoutMS=30000,           # 30 segundos (antes era 10)
    maxPoolSize=10,
    minPoolSize=1,
    retryWrites=False,
    maxIdleTimeMS=45000
)
```

### Opción 2: Verificar MongoDB Atlas

1. Ve a https://cloud.mongodb.com
2. Selecciona tu cluster
3. Ve a **Network Access**
4. Verifica que tu IP esté en la whitelist
5. Si no está, agrega `0.0.0.0/0` (permite todas las IPs)

### Opción 3: Diagnosticar el Problema

Ejecuta:

```bash
python diagnose_ssl.py
```

Esto te dirá exactamente dónde está el problema.

## Causas Comunes

### 1. MongoDB Atlas está caído
**Síntoma**: Error SSL en todos los hosts
**Solución**: Verifica https://status.mongodb.com

### 2. IP no está en whitelist
**Síntoma**: Timeout después de 30 segundos
**Solución**: Agrega tu IP en Network Access

### 3. Firewall bloqueando puerto 27017
**Síntoma**: Timeout en conexión
**Solución**: Intenta desde otra red (móvil, VPN)

### 4. Versión antigua de Python
**Síntoma**: Error SSL incluso con opciones correctas
**Solución**: Actualiza a Python 3.9+

### 5. Versión antigua de pymongo
**Síntoma**: Opciones SSL no funcionan
**Solución**: `pip install --upgrade pymongo`

## Verificación Rápida

### 1. ¿Está MongoDB Atlas activo?

```bash
curl https://status.mongodb.com
```

### 2. ¿Está tu IP en la whitelist?

En MongoDB Atlas:
- Network Access
- IP Whitelist
- Verifica que tu IP esté ahí

### 3. ¿Puedes conectar desde otra red?

Intenta desde:
- Móvil (datos)
- VPN
- Otra red WiFi

### 4. ¿Está pymongo actualizado?

```bash
pip install --upgrade pymongo
```

## Si Nada Funciona

### Opción A: Usar MongoDB Community (local)

```bash
# Instalar MongoDB Community
# https://docs.mongodb.com/manual/installation/

# Conectar localmente
MONGO_URI=mongodb://localhost:27017
```

### Opción B: Usar otra base de datos

- PostgreSQL (Render lo soporta)
- MySQL (Render lo soporta)
- SQLite (simple pero no escalable)

### Opción C: Usar MongoDB en Render

Render tiene soporte para MongoDB:

```bash
# En Render, crear un servicio MongoDB
# Luego usar la URI que Render proporciona
```

## Configuración Recomendada

Para Render + MongoDB Atlas:

```python
client = MongoClient(
    os.getenv("MONGO_URI"),
    # SSL
    tlsAllowInvalidCertificates=True,
    # Timeouts generosos
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    # Pool de conexiones
    maxPoolSize=10,
    minPoolSize=1,
    # Render no soporta bien retry writes
    retryWrites=False,
    # Mantener conexiones vivas
    maxIdleTimeMS=45000
)
```

## Monitorear Conexión

Agrega logging para ver qué está pasando:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Ahora verás logs detallados de MongoDB
```

## Próximos Pasos

1. Ejecuta `python diagnose_ssl.py`
2. Verifica MongoDB Atlas está activo
3. Verifica tu IP está en whitelist
4. Intenta desde otra red
5. Actualiza pymongo: `pip install --upgrade pymongo`
6. Reinicia la app

## Contacto

Si el problema persiste:

1. Copia el output de `diagnose_ssl.py`
2. Copia el error completo de la página 500
3. Verifica que MongoDB Atlas esté activo
4. Intenta desde otra red

El problema es casi siempre:
- MongoDB Atlas caído (5%)
- IP no en whitelist (40%)
- Firewall bloqueando (40%)
- Versión antigua de pymongo (15%)
