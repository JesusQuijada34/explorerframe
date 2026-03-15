# ExplorerFrame OAuth 2.0 Platform - Setup Guide

## ¿Qué es?

ExplorerFrame ahora es una plataforma OAuth 2.0 completa. Los desarrolladores pueden:

1. **Registrar aplicaciones** en el panel de desarrolladores (`/dev/`)
2. **Obtener credenciales** (Client ID + Client Secret)
3. **Implementar login** con ExplorerFrame en sus apps
4. **Acceder a datos del usuario** de forma segura

## Características

### ✅ Panel de Desarrolladores (`/dev/`)
- Crear nuevas aplicaciones
- Ver Client ID y Client Secret
- Configurar URIs de redirección
- Eliminar aplicaciones

### ✅ Endpoints OAuth
- `GET /oauth/authorize` — Solicitar autorización
- `POST /oauth/token` — Intercambiar código por token
- `GET /oauth/userinfo` — Obtener datos del usuario
- `POST /oauth/revoke` — Revocar acceso

### ✅ Seguridad
- Códigos de autorización: válidos 10 minutos
- Access tokens: válidos 30 días
- Client Secret hasheado en BD
- Validación de redirect_uri
- CSRF protection con parámetro `state`

## Flujo OAuth 2.0

```
┌─────────────┐                    ┌──────────────────┐
│  Tu App     │                    │  ExplorerFrame   │
│  (Cliente)  │                    │  (Servidor OAuth)│
└─────────────┘                    └──────────────────┘
      │                                     │
      │ 1. Redirigir a /oauth/authorize     │
      ├────────────────────────────────────>│
      │                                     │
      │ 2. Usuario autoriza                 │
      │                                     │
      │ 3. Redirigir con código             │
      │<────────────────────────────────────┤
      │                                     │
      │ 4. POST /oauth/token (backend)      │
      ├────────────────────────────────────>│
      │                                     │
      │ 5. Devolver access_token            │
      │<────────────────────────────────────┤
      │                                     │
      │ 6. GET /oauth/userinfo              │
      ├────────────────────────────────────>│
      │                                     │
      │ 7. Datos del usuario                │
      │<────────────────────────────────────┤
```

## Instalación

### 1. Actualizar dependencias

```bash
pip install -r requirements.txt
```

Se agregó `PyJWT` para manejar tokens.

### 2. Reiniciar la app

```bash
python app.py
```

## Uso

### Para Desarrolladores

1. **Registrar app**:
   - Ve a `/dev/` en tu cuenta
   - Click en "+ Nueva Aplicación"
   - Ingresa nombre y URIs de redirección
   - Guarda Client ID y Client Secret

2. **Implementar login**:
   - Redirige usuarios a `/oauth/authorize?client_id=...&redirect_uri=...`
   - Recibe código en tu redirect_uri
   - Intercambia código por token en `/oauth/token`
   - Usa token para obtener datos en `/oauth/userinfo`

3. **Ejemplos**:
   - Ver `docs/oauth-examples.md` para código en Python, Node.js, PHP, etc.

### Para Usuarios

- Cuando una app solicita acceso, verás una pantalla de login de ExplorerFrame
- Autoriza y serás redirigido a la app
- Tu sesión se mantiene segura con JWT en cookies

## Estructura de Datos

### oauth_apps
```json
{
  "client_id": "app_xxx",
  "client_secret": "hash_del_secret",
  "owner": "telegram_username",
  "name": "Mi App",
  "redirect_uris": ["https://myapp.com/callback"],
  "created_at": "2024-03-14T10:30:00",
  "active": true
}
```

### oauth_codes
```json
{
  "code": "authorization_code",
  "client_id": "app_xxx",
  "user_id": "telegram_username",
  "redirect_uri": "https://myapp.com/callback",
  "scope": "profile",
  "expires": "2024-03-14T10:40:00",
  "used": false
}
```

### oauth_tokens
```json
{
  "token": "hash_del_token",
  "client_id": "app_xxx",
  "user_id": "telegram_username",
  "scope": "profile",
  "expires": "2024-04-13T10:30:00",
  "created_at": "2024-03-14T10:30:00"
}
```

## Seguridad

- ✅ Client Secret nunca se devuelve después de la creación
- ✅ Tokens hasheados en BD (SHA256)
- ✅ Códigos de autorización de corta vida (10 min)
- ✅ Access tokens de larga vida (30 días)
- ✅ Validación de redirect_uri
- ✅ HTTPS en producción (SESSION_COOKIE_SECURE)
- ✅ HttpOnly cookies (no accesibles desde JS)
- ✅ SameSite=Lax (CSRF protection)

## Troubleshooting

### Error: "invalid_client"
- Verifica que el `client_id` sea correcto
- Verifica que `redirect_uri` esté registrada en la app

### Error: "invalid_grant"
- El código expiró (válido 10 minutos)
- El código ya fue usado
- El `client_secret` es incorrecto

### Error: "invalid_token"
- El token expiró (válido 30 días)
- El token fue revocado
- El token es inválido

## Próximas Mejoras

- [ ] Scopes más granulares (email, profile, api_key)
- [ ] Refresh tokens
- [ ] PKCE para apps móviles
- [ ] Rate limiting en endpoints OAuth
- [ ] Audit log de autorizaciones
- [ ] Revocar acceso desde panel de usuario
