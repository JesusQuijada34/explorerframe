# Ejemplos de Integración OAuth

## Python (Flask)

```python
from flask import Flask, redirect, request, session
import requests

app = Flask(__name__)
app.secret_key = 'your-secret-key'

CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:5000/callback'
BASE_URL = 'https://explorerframe.onrender.com'

@app.route('/login')
def login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    auth_url = f"{BASE_URL}/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state={state}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if state != session.get('oauth_state'):
        return 'Invalid state', 400
    
    # Intercambiar código por token
    token_response = requests.post(f"{BASE_URL}/oauth/token", json={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    })
    
    token_data = token_response.json()
    access_token = token_data['access_token']
    
    # Obtener información del usuario
    user_response = requests.get(f"{BASE_URL}/oauth/userinfo", 
        headers={"Authorization": f"Bearer {access_token}"})
    
    user = user_response.json()
    session['user'] = user
    session['access_token'] = access_token
    
    return redirect('/dashboard')
```

## JavaScript (React)

```jsx
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const CLIENT_ID = 'your_client_id';
const CLIENT_SECRET = 'your_client_secret';
const REDIRECT_URI = 'http://localhost:3000/callback';
const BASE_URL = 'https://explorerframe.onrender.com';

export function LoginButton() {
  const handleLogin = () => {
    const state = Math.random().toString(36).substring(7);
    localStorage.setItem('oauth_state', state);
    
    const authUrl = new URL(`${BASE_URL}/oauth/authorize`);
    authUrl.searchParams.set('client_id', CLIENT_ID);
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
    authParams.set('state', state);
    
    window.location.href = authUrl.toString();
  };
  
  return <button onClick={handleLogin}>Login with ExplorerFrame</button>;
}

export function OAuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    
    if (state !== localStorage.getItem('oauth_state')) {
      console.error('Invalid state');
      return;
    }
    
    // Intercambiar código por token (DEBE hacerse en backend)
    fetch('/api/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    })
    .then(r => r.json())
    .then(data => {
      localStorage.setItem('access_token', data.access_token);
      navigate('/dashboard');
    });
  }, [searchParams, navigate]);
  
  return <div>Autenticando...</div>;
}
```

## cURL

```bash
# 1. Obtener código de autorización (en el navegador)
https://explorerframe.onrender.com/oauth/authorize?client_id=app_xxx&redirect_uri=http://localhost:3000/callback&state=random123

# 2. Intercambiar código por token
curl -X POST https://explorerframe.onrender.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "client_id": "app_xxx",
    "client_secret": "secret_yyy",
    "code": "code_from_redirect",
    "redirect_uri": "http://localhost:3000/callback"
  }'

# 3. Obtener información del usuario
curl -H "Authorization: Bearer access_token_here" \
  https://explorerframe.onrender.com/oauth/userinfo

# 4. Revocar token
curl -X POST https://explorerframe.onrender.com/oauth/revoke \
  -H "Content-Type: application/json" \
  -d '{"token": "access_token_here"}'
```

## Flujo Completo en Postman

1. **Autorizar**: Abre en navegador:
   ```
   https://explorerframe.onrender.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000/callback&state=test123
   ```

2. **Obtener Token**: POST a `/oauth/token` con:
   ```json
   {
     "grant_type": "authorization_code",
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET",
     "code": "CODE_FROM_REDIRECT",
     "redirect_uri": "http://localhost:3000/callback"
   }
   ```

3. **Usar Token**: GET a `/oauth/userinfo` con header:
   ```
   Authorization: Bearer YOUR_ACCESS_TOKEN
   ```
