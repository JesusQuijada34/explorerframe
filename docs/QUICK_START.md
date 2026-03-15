# OAuth Quick Start

## 1. Registrar tu app

1. Inicia sesión en ExplorerFrame
2. Ve a `/dev/` (Developer Console)
3. Click "+ Nueva Aplicación"
4. Ingresa:
   - **Nombre**: "Mi App"
   - **URIs de redirección**: `https://myapp.com/callback`
5. Guarda el **Client ID** y **Client Secret**

## 2. Implementar el flujo

### Paso 1: Redirigir a ExplorerFrame

```javascript
const clientId = 'app_xxx';
const redirectUri = 'https://myapp.com/callback';
const state = Math.random().toString(36).substring(7);

localStorage.setItem('oauth_state', state);

const authUrl = new URL('https://explorerframe.onrender.com/oauth/authorize');
authUrl.searchParams.set('client_id', clientId);
authUrl.searchParams.set('redirect_uri', redirectUri);
authUrl.searchParams.set('state', state);

window.location.href = authUrl.toString();
```

### Paso 2: Manejar el callback

El usuario será redirigido a:
```
https://myapp.com/callback?code=AUTH_CODE&state=RANDOM_STATE
```

### Paso 3: Intercambiar código por token (en tu backend)

```python
import requests

code = request.args.get('code')
state = request.args.get('state')

# Validar state
if state != session.get('oauth_state'):
    return 'Invalid state', 400

# Intercambiar código por token
response = requests.post('https://explorerframe.onrender.com/oauth/token', json={
    'grant_type': 'authorization_code',
    'client_id': 'app_xxx',
    'client_secret': 'secret_yyy',
    'code': code,
    'redirect_uri': 'https://myapp.com/callback'
})

token_data = response.json()
access_token = token_data['access_token']
user_id = token_data['user_id']

# Guardar en sesión
session['access_token'] = access_token
session['user_id'] = user_id
```

### Paso 4: Obtener datos del usuario

```python
import requests

access_token = session['access_token']

response = requests.get(
    'https://explorerframe.onrender.com/oauth/userinfo',
    headers={'Authorization': f'Bearer {access_token}'}
)

user = response.json()
# {
#   "user_id": "telegram_username",
#   "api_key": "user_api_key",
#   "created_at": "2024-03-14T10:30:00"
# }
```

## 3. Respuestas de API

### POST /oauth/token - Success
```json
{
  "access_token": "token_here",
  "token_type": "Bearer",
  "expires_in": 2592000,
  "user_id": "telegram_username"
}
```

### GET /oauth/userinfo - Success
```json
{
  "user_id": "telegram_username",
  "api_key": "user_api_key",
  "created_at": "2024-03-14T10:30:00"
}
```

### Error Response
```json
{
  "error": "invalid_grant"
}
```

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `invalid_client` | Client ID incorrecto o no existe | Verifica el Client ID en `/dev/` |
| `invalid_grant` | Código expirado o ya usado | Genera un nuevo código |
| `invalid_token` | Token expirado o revocado | Pide un nuevo token |
| `missing_parameters` | Faltan parámetros requeridos | Verifica la documentación |

## Seguridad

- ✅ Nunca expongas `client_secret` en el frontend
- ✅ Siempre valida el parámetro `state`
- ✅ Usa HTTPS en producción
- ✅ Guarda `access_token` de forma segura (sesión del servidor)
- ✅ Revoca tokens cuando el usuario cierre sesión

## Documentación Completa

- [OAuth API Reference](oauth-api.md)
- [Ejemplos de Código](oauth-examples.md)
- [Setup Guide](OAUTH_SETUP.md)
