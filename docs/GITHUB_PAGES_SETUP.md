# Usar ExplorerFrame OAuth en GitHub Pages

GitHub Pages es 100% estático, así que usaremos un widget JavaScript que se comunica con tu backend OAuth en Render.

## 1. Registrar tu app

1. Ve a `/dev/` en ExplorerFrame
2. Crea una nueva app con:
   - **Nombre**: "Mi Sitio GitHub Pages"
   - **Redirect URI**: `https://tuusuario.github.io/turepositorio/callback.html`

3. Guarda el **Client ID**

## 2. Crear la página de callback

En tu repositorio de GitHub Pages, crea `callback.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Autenticando...</title>
</head>
<body>
  <div id="status">Autenticando con ExplorerFrame...</div>
  
  <script>
    // Este script maneja el callback del OAuth
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    if (!code) {
      document.getElementById('status').textContent = 'Error: No authorization code';
      setTimeout(() => window.location.href = '/', 2000);
    } else {
      // Guardar código en sessionStorage
      sessionStorage.setItem('oauth_code', code);
      sessionStorage.setItem('oauth_state', state);
      
      // Redirigir a la página principal
      window.location.href = '/';
    }
  </script>
</body>
</html>
```

## 3. Crear un backend simple para intercambiar el código

**Opción A: Usar Render (recomendado)**

Ya tienes ExplorerFrame en Render. Crea un endpoint en `app.py`:

```python
@app.route("/api/oauth/token", methods=["POST"])
def api_oauth_token():
    """Intercambia código por token (para sitios estáticos)"""
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")  # NO envíes esto desde el cliente
    redirect_uri = data.get("redirect_uri")
    
    if not all([code, client_id, redirect_uri]):
        return jsonify({"error": "missing_parameters"}), 400
    
    # Intercambiar código por token
    result = exchange_code_for_token(client_id, client_secret, code, redirect_uri)
    if not result:
        return jsonify({"error": "invalid_grant"}), 400
    
    return jsonify(result)
```

**Opción B: Usar Netlify Functions**

Si usas Netlify en lugar de GitHub Pages:

```javascript
// netlify/functions/oauth-token.js
const fetch = require('node-fetch');

exports.handler = async (event) => {
  const { code } = JSON.parse(event.body);
  
  const response = await fetch('https://explorerframe.onrender.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grant_type: 'authorization_code',
      client_id: process.env.OAUTH_CLIENT_ID,
      client_secret: process.env.OAUTH_CLIENT_SECRET,
      code,
      redirect_uri: process.env.OAUTH_REDIRECT_URI
    })
  });
  
  const data = await response.json();
  return { statusCode: 200, body: JSON.stringify(data) };
};
```

## 4. Usar el widget en tu sitio

En tu `index.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Mi Sitio</title>
  <style>
    body { font-family: sans-serif; padding: 20px; }
    .container { max-width: 600px; margin: 0 auto; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Bienvenido</h1>
    
    <!-- Widget de login -->
    <div id="explorerframe-login"></div>
    
    <!-- Contenido protegido (solo visible si está autenticado) -->
    <div id="protected-content" style="display: none;">
      <h2>Contenido protegido</h2>
      <p>Hola, <span id="user-id"></span>!</p>
      <button onclick="logout()">Cerrar sesión</button>
    </div>
  </div>

  <!-- Cargar el widget -->
  <script src="https://explorerframe.onrender.com/static/oauth-widget.js"></script>
  
  <script>
    // Configurar el widget
    ExplorerFrameOAuth.init({
      clientId: 'app_xxx',  // Tu Client ID
      redirectUri: 'https://tuusuario.github.io/turepositorio/callback.html',
      container: '#explorerframe-login',
      
      onSuccess: (data) => {
        console.log('✅ Autenticado:', data);
        
        // Mostrar contenido protegido
        document.getElementById('explorerframe-login').style.display = 'none';
        document.getElementById('protected-content').style.display = 'block';
        
        // Obtener información del usuario
        ExplorerFrameOAuth.getUserInfo().then(user => {
          document.getElementById('user-id').textContent = user.user_id;
        });
      },
      
      onError: (error) => {
        console.error('❌ Error:', error);
        alert('Error en autenticación: ' + error.message);
      }
    });

    // Verificar si ya está autenticado
    if (ExplorerFrameOAuth.isAuthenticated()) {
      document.getElementById('explorerframe-login').style.display = 'none';
      document.getElementById('protected-content').style.display = 'block';
      
      ExplorerFrameOAuth.getUserInfo().then(user => {
        document.getElementById('user-id').textContent = user.user_id;
      });
    }

    function logout() {
      ExplorerFrameOAuth.logout();
      location.reload();
    }
  </script>
</body>
</html>
```

## 5. Estructura del repositorio

```
mi-sitio/
├── index.html          # Página principal con widget
├── callback.html       # Página de callback
├── style.css           # Estilos (opcional)
└── script.js           # Scripts adicionales (opcional)
```

## 6. Flujo completo

```
1. Usuario hace click en "Login with ExplorerFrame"
   ↓
2. Se redirige a ExplorerFrame (/oauth/authorize)
   ↓
3. Usuario inicia sesión y autoriza
   ↓
4. Se redirige a callback.html con código
   ↓
5. callback.html guarda el código y redirige a index.html
   ↓
6. index.html intercambia código por token (via tu backend)
   ↓
7. Token se guarda en sessionStorage
   ↓
8. Contenido protegido se muestra
```

## 7. Seguridad

⚠️ **IMPORTANTE**: 

- **Nunca** expongas tu `client_secret` en el cliente (JavaScript)
- El intercambio de código por token debe hacerse en tu backend
- Usa HTTPS siempre
- Valida el parámetro `state` para prevenir CSRF

## 8. Ejemplo completo

Repositorio de ejemplo: https://github.com/JesusQuijada34/explorerframe-oauth-example

Clona y personaliza:

```bash
git clone https://github.com/JesusQuijada34/explorerframe-oauth-example
cd explorerframe-oauth-example
# Edita index.html con tu Client ID
# Haz push a GitHub
```

## 9. Troubleshooting

### Error: "CORS error"
**Causa**: El navegador bloquea la solicitud
**Solución**: Asegúrate de que tu backend tiene CORS habilitado

### Error: "Redirect URI mismatch"
**Causa**: La URI en el callback no coincide con la registrada
**Solución**: Verifica que sean exactamente iguales (incluyendo protocolo y trailing slash)

### Error: "Invalid state"
**Causa**: El parámetro state no coincide
**Solución**: Esto es normal si abres el callback en otra pestaña

## 10. Próximos pasos

- [ ] Registrar tu app en `/dev/`
- [ ] Crear `callback.html`
- [ ] Crear endpoint `/api/oauth/token` en tu backend
- [ ] Agregar widget a `index.html`
- [ ] Probar el flujo completo
- [ ] Hacer push a GitHub Pages
