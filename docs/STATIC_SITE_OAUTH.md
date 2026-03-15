# OAuth para Sitios Estáticos (GitHub Pages, Netlify, etc)

## El Problema

GitHub Pages es 100% estático. No puedes ejecutar Flask, Node.js, Python, etc. Pero necesitas OAuth para autenticar usuarios.

## La Solución

Usar un **widget JavaScript** que se comunica con tu backend OAuth en Render.

```
GitHub Pages (estático)  ←→  ExplorerFrame (Render)
   index.html                  /oauth/authorize
   callback.html              /oauth/token
   oauth-widget.js            /oauth/userinfo
```

## Componentes

### 1. Widget JavaScript (`oauth-widget.js`)
- Botón de login
- Manejo del flujo OAuth
- Almacenamiento de token en sessionStorage
- Métodos para obtener usuario, logout, etc.

### 2. Página de Callback (`callback.html`)
- Recibe el código de autorización
- Lo guarda en sessionStorage
- Redirige a la página principal

### 3. Página Principal (`index.html`)
- Carga el widget
- Intercambia código por token (via backend)
- Muestra contenido protegido

### 4. Backend (`/api/oauth/token`)
- Intercambia código por token
- Valida credenciales
- Devuelve access_token

## Flujo Paso a Paso

```
1. Usuario hace click en "Login with ExplorerFrame"
   ↓
2. Widget redirige a: /oauth/authorize?client_id=...&redirect_uri=...
   ↓
3. Usuario inicia sesión en ExplorerFrame
   ↓
4. Usuario autoriza la app
   ↓
5. ExplorerFrame redirige a: callback.html?code=...&state=...
   ↓
6. callback.html guarda el código en sessionStorage
   ↓
7. callback.html redirige a index.html
   ↓
8. index.html detecta el código en sessionStorage
   ↓
9. index.html hace POST a /api/oauth/token con el código
   ↓
10. Backend intercambia código por token
   ↓
11. index.html recibe el token y lo guarda
   ↓
12. Contenido protegido se muestra
```

## Implementación Rápida

### Paso 1: Registrar tu app

1. Ve a `https://explorerframe.onrender.com/dev/`
2. Crea una app con:
   - **Nombre**: "Mi Sitio GitHub Pages"
   - **Redirect URI**: `https://tuusuario.github.io/turepositorio/callback.html`
3. Guarda el **Client ID**

### Paso 2: Crear archivos en tu repositorio

**callback.html**:
```html
<!DOCTYPE html>
<html>
<body>
  <script>
    const params = new URLSearchParams(window.location.search);
    sessionStorage.setItem('oauth_code', params.get('code'));
    sessionStorage.setItem('oauth_state', params.get('state'));
    window.location.href = '/';
  </script>
</body>
</html>
```

**index.html**:
```html
<!DOCTYPE html>
<html>
<body>
  <div id="explorerframe-login"></div>
  
  <script src="https://explorerframe.onrender.com/static/oauth-widget.js"></script>
  <script>
    ExplorerFrameOAuth.init({
      clientId: 'app_xxx',  // Tu Client ID
      redirectUri: 'https://tuusuario.github.io/turepositorio/callback.html',
      container: '#explorerframe-login',
      onSuccess: (data) => {
        console.log('✅ Autenticado:', data);
        // Mostrar contenido protegido
      }
    });
  </script>
</body>
</html>
```

### Paso 3: Hacer push a GitHub

```bash
git add .
git commit -m "Add ExplorerFrame OAuth"
git push
```

## Archivos de Ejemplo

- `docs/github-pages-example.html` — Ejemplo completo y funcional
- `docs/github-pages-callback.html` — Página de callback
- `docs/oauth-widget.js` — Widget JavaScript

## Seguridad

⚠️ **IMPORTANTE**:

1. **Nunca expongas `client_secret` en el cliente**
   - El intercambio de código por token debe hacerse en tu backend
   - Si usas Render, ya tienes el backend

2. **Usa HTTPS siempre**
   - GitHub Pages usa HTTPS automáticamente
   - Asegúrate de que tu redirect_uri sea HTTPS

3. **Valida el parámetro `state`**
   - Previene ataques CSRF
   - El widget lo hace automáticamente

4. **Guarda el token de forma segura**
   - sessionStorage es suficiente para sitios estáticos
   - Se borra cuando cierras la pestaña

## Métodos del Widget

```javascript
// Inicializar
ExplorerFrameOAuth.init({
  clientId: 'app_xxx',
  redirectUri: 'https://...',
  container: '#explorerframe-login',
  onSuccess: (data) => {},
  onError: (error) => {}
});

// Obtener información del usuario
const user = await ExplorerFrameOAuth.getUserInfo();
// { user_id: "telegram_username", api_key: "...", created_at: "..." }

// Obtener token actual
const token = ExplorerFrameOAuth.getToken();

// Obtener user_id actual
const userId = ExplorerFrameOAuth.getUserId();

// Verificar si está autenticado
if (ExplorerFrameOAuth.isAuthenticated()) {
  // Mostrar contenido protegido
}

// Cerrar sesión
ExplorerFrameOAuth.logout();
```

## Personalización

### Cambiar estilos del botón

El widget genera un botón con estilos por defecto. Puedes personalizarlo con CSS:

```css
#explorerframe-login-btn {
  background: #your-color !important;
  padding: 15px 30px !important;
  font-size: 16px !important;
}
```

### Mostrar/ocultar contenido según autenticación

```javascript
if (ExplorerFrameOAuth.isAuthenticated()) {
  document.getElementById('protected').style.display = 'block';
  document.getElementById('login').style.display = 'none';
} else {
  document.getElementById('protected').style.display = 'none';
  document.getElementById('login').style.display = 'block';
}
```

## Troubleshooting

### Error: "CORS error"
**Causa**: El navegador bloquea la solicitud
**Solución**: Asegúrate de que el backend tiene CORS habilitado

### Error: "Redirect URI mismatch"
**Causa**: La URI no coincide exactamente
**Solución**: Verifica protocolo, dominio, path y trailing slash

### Error: "Invalid state"
**Causa**: El parámetro state no coincide
**Solución**: Esto es normal si abres callback.html en otra pestaña

### Token no se guarda
**Causa**: sessionStorage está deshabilitado
**Solución**: Verifica que el navegador permita sessionStorage

## Ejemplos Completos

### Ejemplo 1: Sitio simple con login

Ver: `docs/github-pages-example.html`

### Ejemplo 2: Sitio con múltiples páginas

```
index.html          # Página principal
callback.html       # Callback del OAuth
protected.html      # Contenido protegido
public.html         # Contenido público
```

En cada página:
```javascript
<script src="https://explorerframe.onrender.com/static/oauth-widget.js"></script>
<script>
  if (!ExplorerFrameOAuth.isAuthenticated()) {
    window.location.href = '/';
  }
</script>
```

## Próximos Pasos

- [ ] Registrar tu app en `/dev/`
- [ ] Crear `callback.html`
- [ ] Crear `index.html` con el widget
- [ ] Hacer push a GitHub Pages
- [ ] Probar el flujo completo
- [ ] Personalizar estilos

## Documentación Completa

- [OAuth API Reference](oauth-api.md)
- [GitHub Pages Setup](GITHUB_PAGES_SETUP.md)
- [Quick Start](QUICK_START.md)
