# ExplorerFrame OAuth Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ExplorerFrame Platform                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  User Dashboard  │         │ Developer Console│              │
│  │  - Login/Logout  │         │ - Create Apps    │              │
│  │  - API Key       │         │ - View Creds     │              │
│  │  - Download      │         │ - Manage URIs    │              │
│  └──────────────────┘         └──────────────────┘              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              OAuth 2.0 Endpoints                         │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ GET  /oauth/authorize      - Start auth flow      │  │   │
│  │  │ POST /oauth/token          - Exchange code→token  │  │   │
│  │  │ GET  /oauth/userinfo       - Get user data        │  │   │
│  │  │ POST /oauth/revoke         - Revoke token         │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MongoDB Collections                        │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ oauth_apps        - Registered applications       │  │   │
│  │  │ oauth_codes       - Authorization codes (10 min)  │  │   │
│  │  │ oauth_tokens      - Access tokens (30 days)       │  │   │
│  │  │ users             - User accounts                 │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## OAuth 2.0 Authorization Code Flow

```
┌──────────────┐                                    ┌──────────────┐
│  User's App  │                                    │ ExplorerFrame│
│  (Frontend)  │                                    │  (Backend)   │
└──────────────┘                                    └──────────────┘
       │                                                    │
       │ 1. Click "Login with ExplorerFrame"               │
       │                                                    │
       │ 2. Redirect to /oauth/authorize                   │
       ├───────────────────────────────────────────────────>│
       │    ?client_id=app_xxx                             │
       │    &redirect_uri=https://myapp.com/callback       │
       │    &state=random123                               │
       │                                                    │
       │ 3. User logs in (if not already)                  │
       │                                                    │
       │ 4. User authorizes app                            │
       │                                                    │
       │ 5. Redirect to callback with code                 │
       │<───────────────────────────────────────────────────┤
       │    ?code=auth_code_xxx                            │
       │    &state=random123                               │
       │                                                    │
       │ 6. Backend: POST /oauth/token                     │
       │    (client_id, client_secret, code, redirect_uri) │
       ├───────────────────────────────────────────────────>│
       │                                                    │
       │ 7. Return access_token                            │
       │<───────────────────────────────────────────────────┤
       │    {                                              │
       │      "access_token": "token_xxx",                 │
       │      "token_type": "Bearer",                      │
       │      "expires_in": 2592000,                       │
       │      "user_id": "telegram_username"               │
       │    }                                              │
       │                                                    │
       │ 8. GET /oauth/userinfo                            │
       │    Authorization: Bearer token_xxx                │
       ├───────────────────────────────────────────────────>│
       │                                                    │
       │ 9. Return user data                               │
       │<───────────────────────────────────────────────────┤
       │    {                                              │
       │      "user_id": "telegram_username",              │
       │      "api_key": "user_api_key",                   │
       │      "created_at": "2024-03-14T10:30:00"          │
       │    }                                              │
       │                                                    │
       │ 10. User logged in!                               │
       │                                                    │
```

## Data Models

### oauth_apps
```
{
  _id: ObjectId,
  client_id: "app_xxx",                    // Público
  client_secret: "hash_sha256",            // Privado (hasheado)
  owner: "telegram_username",              // Propietario
  name: "Mi App",                          // Nombre legible
  redirect_uris: [                         // URIs permitidas
    "https://myapp.com/callback",
    "https://myapp.com/oauth/callback"
  ],
  created_at: ISODate,
  active: true
}
```

### oauth_codes
```
{
  _id: ObjectId,
  code: "auth_code_xxx",                   // Código único
  client_id: "app_xxx",                    // App que lo solicitó
  user_id: "telegram_username",            // Usuario que autorizó
  redirect_uri: "https://myapp.com/callback",
  scope: "profile",                        // Permisos
  expires: ISODate,                        // Expira en 10 min
  used: false                              // Usado una sola vez
}
```

### oauth_tokens
```
{
  _id: ObjectId,
  token: "hash_sha256",                    // Token hasheado
  client_id: "app_xxx",                    // App que lo emitió
  user_id: "telegram_username",            // Usuario propietario
  scope: "profile",                        // Permisos
  expires: ISODate,                        // Expira en 30 días
  created_at: ISODate
}
```

## Security Measures

### Token Generation
- Client ID: `secrets.token_hex(16)` → 32 caracteres
- Client Secret: `secrets.token_urlsafe(48)` → 64 caracteres
- Auth Code: `secrets.token_urlsafe(32)` → 43 caracteres
- Access Token: `secrets.token_urlsafe(48)` → 64 caracteres

### Token Storage
- Client Secret: Hasheado con SHA256 en BD
- Access Token: Hasheado con SHA256 en BD
- Auth Code: Almacenado en texto plano (corta vida)

### Validation
- ✅ Verificar client_id existe
- ✅ Verificar client_secret es correcto
- ✅ Verificar redirect_uri está registrada
- ✅ Verificar código no expiró
- ✅ Verificar código no fue usado
- ✅ Verificar token no expiró
- ✅ Validar parámetro state (CSRF)

### Cookie Security
- HttpOnly: No accesible desde JavaScript
- SameSite=Lax: Protección CSRF
- Secure: Solo HTTPS en producción
- Max-Age: 30 días

## API Response Codes

| Código | Significado |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado |
| 400 | Bad Request - Parámetros inválidos |
| 401 | Unauthorized - Token inválido/expirado |
| 403 | Forbidden - Acceso denegado |
| 404 | Not Found - Recurso no existe |
| 500 | Internal Server Error |

## Rate Limiting (Futuro)

Implementar rate limiting en:
- `/oauth/authorize` - 100 req/min por IP
- `/oauth/token` - 50 req/min por IP
- `/oauth/userinfo` - 1000 req/min por token

## Audit Logging (Futuro)

Registrar:
- Creación de apps
- Autorizaciones de usuarios
- Intercambios de tokens
- Revocaciones
- Accesos a userinfo

## Scopes (Futuro)

```
profile      - Información básica del usuario
email        - Email del usuario
api_key      - Acceso a API Key
telegram_id  - ID de Telegram
```

## Refresh Tokens (Futuro)

```
POST /oauth/token
{
  "grant_type": "refresh_token",
  "refresh_token": "refresh_token_xxx",
  "client_id": "app_xxx",
  "client_secret": "secret_yyy"
}
```

## PKCE Support (Futuro)

Para apps móviles sin backend:

```
GET /oauth/authorize
  ?client_id=app_xxx
  &code_challenge=hash_of_verifier
  &code_challenge_method=S256
```
