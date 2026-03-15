# ExplorerFrame OAuth 2.0 API

ExplorerFrame ahora funciona como proveedor OAuth 2.0, permitiendo que aplicaciones de terceros autentiquen usuarios usando sus cuentas de ExplorerFrame.

## Flujo OAuth 2.0

### 1. Registrar tu aplicación

Ve a `/dev/` en tu cuenta de ExplorerFrame y crea una nueva aplicación. Recibirás:
- **Client ID**: Identificador público de tu app
- **Client Secret**: Contraseña secreta (guárdala segura)

### 2. Redirigir al usuario a autorizar

```
GET /oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=profile&state=RANDOM_STATE
```

**Parámetros:**
- `client_id` (requerido): Tu Client ID
- `redirect_uri` (requerido): Una de las URIs registradas en tu app
- `scope` (opcional): Permisos solicitados (actualmente solo `profile`)
- `state` (recomendado): Token aleatorio para prevenir CSRF

El usuario verá una pantalla de login de ExplorerFrame. Si autoriza, será redirigido a:

```
YOUR_REDIRECT_URI?code=AUTHORIZATION_CODE&state=RANDOM_STATE
```

### 3. Intercambiar código por token

```bash
curl -X POST https://explorerframe.onrender.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "code": "AUTHORIZATION_CODE",
    "redirect_uri": "YOUR_REDIRECT_URI"
  }'
```

**Respuesta:**
```json
{
  "access_token": "TOKEN_HERE",
  "token_type": "Bearer",
  "expires_in": 2592000,
  "user_id": "telegram_username"
}
```

### 4. Obtener información del usuario

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  https://explorerframe.onrender.com/oauth/userinfo
```

**Respuesta:**
```json
{
  "user_id": "telegram_username",
  "api_key": "user_api_key",
  "created_at": "2024-03-14T10:30:00"
}
```

## Endpoints

### GET /oauth/authorize
Inicia el flujo de autorización. Requiere que el usuario esté logueado en ExplorerFrame.

### POST /oauth/token
Intercambia un código de autorización por un access token.

### GET /oauth/userinfo
Devuelve información del usuario autenticado. Requiere header `Authorization: Bearer <token>`.

### POST /oauth/revoke
Revoca un access token.

```bash
curl -X POST https://explorerframe.onrender.com/oauth/revoke \
  -H "Content-Type: application/json" \
  -d '{"token": "ACCESS_TOKEN"}'
```

## Ejemplo: Integración en Node.js

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

const CLIENT_ID = 'your_client_id';
const CLIENT_SECRET = 'your_client_secret';
const REDIRECT_URI = 'http://localhost:3000/callback';
const BASE_URL = 'https://explorerframe.onrender.com';

// 1. Redirigir a ExplorerFrame
app.get('/login', (req, res) => {
  const state = Math.random().toString(36).substring(7);
  res.redirect(`${BASE_URL}/oauth/authorize?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&state=${state}`);
});

// 2. Callback después de autorizar
app.get('/callback', async (req, res) => {
  const { code, state } = req.query;
  
  try {
    // Intercambiar código por token
    const tokenRes = await axios.post(`${BASE_URL}/oauth/token`, {
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      code,
      redirect_uri: REDIRECT_URI
    });
    
    const { access_token } = tokenRes.data;
    
    // Obtener información del usuario
    const userRes = await axios.get(`${BASE_URL}/oauth/userinfo`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });
    
    const user = userRes.data;
    
    // Guardar token en sesión y redirigir
    req.session.user = user;
    req.session.access_token = access_token;
    res.redirect('/dashboard');
  } catch (error) {
    res.status(400).send('Error en autenticación');
  }
});

app.listen(3000);
```

## Seguridad

- Nunca expongas tu `client_secret` en el cliente (frontend)
- Siempre valida el parámetro `state` para prevenir CSRF
- Los access tokens expiran en 30 días
- Los códigos de autorización expiran en 10 minutos
- Usa HTTPS en producción
