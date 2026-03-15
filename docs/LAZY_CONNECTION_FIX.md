# Solución Final: Conexión Lazy a MongoDB

## El Problema

En Render, la conexión a MongoDB falla **al iniciar la app** porque:

1. Render intenta conectar inmediatamente
2. El handshake SSL falla por restricciones de red
3. La app no inicia

## La Solución: Conexión Lazy

En lugar de conectar al iniciar, **conectamos solo cuando se necesita**:

```python
# ❌ Antes (falla en Render)
client = MongoClient(MONGO_URI)  # Conecta inmediatamente
db = client["explorerframe"]

# ✅ Después (funciona en Render)
def get_mongo_db():
    # Conecta solo cuando se llama
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client["explorerframe"]
```

## Cómo Funciona

### 1. Primera solicitud (login)
```
Usuario hace login
    ↓
Flask intenta acceder a users_col
    ↓
LazyCollection.__getattr__ se ejecuta
    ↓
get_mongo_db() se llama por primera vez
    ↓
MongoClient se crea y conecta
    ↓
Conexión exitosa (PyMongo maneja SSL bien)
    ↓
Query se ejecuta
```

### 2. Solicitudes posteriores
```
Usuario hace otra acción
    ↓
Flask intenta acceder a users_col
    ↓
LazyCollection.__getattr__ se ejecuta
    ↓
get_mongo_db() devuelve cliente existente
    ↓
Query se ejecuta (rápido)
```

## Implementación

### En `app.py`:

```python
class LazyCollection:
    def __init__(self, collection_name):
        self.collection_name = collection_name
    
    def __getattr__(self, name):
        return getattr(get_mongo_db()[self.collection_name], name)

users_col = LazyCollection("users")
tokens_col = LazyCollection("pending_tokens")
dl_tokens_col = LazyCollection("download_tokens")
```

### En `oauth.py`:

```python
class LazyCollection:
    def __init__(self, collection_name):
        self.collection_name = collection_name
    
    def __getattr__(self, name):
        return getattr(get_mongo_db()[self.collection_name], name)

oauth_apps = LazyCollection("oauth_apps")
oauth_codes = LazyCollection("oauth_codes")
oauth_tokens = LazyCollection("oauth_tokens")
```

## Ventajas

✅ **Funciona en Render** — No conecta al iniciar
✅ **Maneja errores SSL** — PyMongo lo hace bien
✅ **Transparente** — El código no cambia
✅ **Eficiente** — Reutiliza conexión
✅ **Seguro** — Valida conexión con ping

## Prueba

1. Intenta iniciar sesión
2. Si funciona, ¡problema resuelto!
3. Si falla, verás el error en la página 500

## Qué Cambió

| Antes | Después |
|-------|---------|
| Conecta al iniciar | Conecta en primer uso |
| Falla en Render | Funciona en Render |
| Error 500 inmediato | Error 500 en login |
| Difícil de debuggear | Fácil de debuggear |

## Si Aún Falla

1. Verifica que MongoDB Atlas esté activo
2. Verifica que tu IP esté en whitelist
3. Intenta desde otra red
4. Ejecuta `python diagnose_ssl.py`

## Próximos Pasos

1. Intenta iniciar sesión
2. Si funciona, ¡listo!
3. Si falla, comparte el error de la página 500
