/**
 * ExplorerFrame OAuth Widget
 * 
 * Widget de login OAuth para usar en sitios estáticos (GitHub Pages, etc)
 * 
 * Uso:
 * <script src="https://explorerframe.onrender.com/static/oauth-widget.js"></script>
 * <div id="explorerframe-login"></div>
 * <script>
 *   ExplorerFrameOAuth.init({
 *     clientId: 'app_xxx',
 *     redirectUri: 'https://tudominio.com/callback.html',
 *     container: '#explorerframe-login'
 *   });
 * </script>
 */

const ExplorerFrameOAuth = (() => {
  const BASE_URL = 'https://explorerframe.onrender.com';
  let config = {};

  /**
   * Inicializa el widget
   */
  function init(options) {
    config = {
      clientId: options.clientId,
      redirectUri: options.redirectUri,
      container: options.container || '#explorerframe-login',
      onSuccess: options.onSuccess || (() => {}),
      onError: options.onError || (() => {}),
      ...options
    };

    renderWidget();
    handleCallback();
  }

  /**
   * Renderiza el botón de login
   */
  function renderWidget() {
    const container = document.querySelector(config.container);
    if (!container) {
      console.error(`[ExplorerFrame] Container ${config.container} not found`);
      return;
    }

    const html = `
      <div id="explorerframe-widget" style="
        display: inline-block;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      ">
        <button id="explorerframe-login-btn" style="
          background: linear-gradient(135deg, #3b82f6, #2563eb);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
          font-size: 14px;
          transition: opacity 0.2s;
          display: flex;
          align-items: center;
          gap: 8px;
        ">
          <span style="font-size: 16px;">⬡</span>
          Login with ExplorerFrame
        </button>
        <div id="explorerframe-loading" style="display: none; text-align: center;">
          <div style="
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #e5e7eb;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
          "></div>
          <p style="margin: 10px 0 0 0; color: #6b7280; font-size: 14px;">Autenticando...</p>
        </div>
        <style>
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
          #explorerframe-login-btn:hover {
            opacity: 0.9;
          }
          #explorerframe-login-btn:active {
            opacity: 0.8;
          }
        </style>
      </div>
    `;

    container.innerHTML = html;

    document.getElementById('explorerframe-login-btn').addEventListener('click', startLogin);
  }

  /**
   * Inicia el flujo de login
   */
  function startLogin() {
    const state = generateState();
    sessionStorage.setItem('explorerframe_state', state);
    sessionStorage.setItem('explorerframe_client_id', config.clientId);

    const params = new URLSearchParams({
      client_id: config.clientId,
      redirect_uri: config.redirectUri,
      scope: 'profile',
      state: state
    });

    window.location.href = `${BASE_URL}/oauth/authorize?${params.toString()}`;
  }

  /**
   * Maneja el callback después de autorizar
   */
  function handleCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    if (!code) return;

    // Validar state
    const savedState = sessionStorage.getItem('explorerframe_state');
    if (state !== savedState) {
      config.onError({ error: 'invalid_state', message: 'State mismatch' });
      return;
    }

    // Mostrar loading
    const widget = document.querySelector('#explorerframe-widget');
    if (widget) {
      widget.querySelector('#explorerframe-login-btn').style.display = 'none';
      widget.querySelector('#explorerframe-loading').style.display = 'block';
    }

    // Intercambiar código por token
    exchangeCodeForToken(code);
  }

  /**
   * Intercambia el código por un token (requiere backend)
   */
  async function exchangeCodeForToken(code) {
    try {
      // IMPORTANTE: Esta llamada debe hacerse desde tu backend
      // No hagas esto directamente desde el cliente porque expondrías el client_secret
      
      // Opción 1: Si tienes un backend propio
      const response = await fetch('/api/oauth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      if (!response.ok) {
        throw new Error('Token exchange failed');
      }

      const data = await response.json();
      
      // Guardar token
      sessionStorage.setItem('explorerframe_token', data.access_token);
      sessionStorage.setItem('explorerframe_user_id', data.user_id);

      // Callback de éxito
      config.onSuccess({
        access_token: data.access_token,
        user_id: data.user_id,
        token_type: data.token_type
      });

      // Limpiar URL
      window.history.replaceState({}, document.title, window.location.pathname);

    } catch (error) {
      config.onError({
        error: 'token_exchange_failed',
        message: error.message
      });
    }
  }

  /**
   * Obtiene la información del usuario
   */
  async function getUserInfo() {
    const token = sessionStorage.getItem('explorerframe_token');
    if (!token) {
      throw new Error('No token found');
    }

    const response = await fetch(`${BASE_URL}/oauth/userinfo`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch user info');
    }

    return response.json();
  }

  /**
   * Revoca el token actual
   */
  async function logout() {
    const token = sessionStorage.getItem('explorerframe_token');
    if (!token) return;

    try {
      await fetch(`${BASE_URL}/oauth/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    sessionStorage.removeItem('explorerframe_token');
    sessionStorage.removeItem('explorerframe_user_id');
    sessionStorage.removeItem('explorerframe_state');
  }

  /**
   * Obtiene el token actual
   */
  function getToken() {
    return sessionStorage.getItem('explorerframe_token');
  }

  /**
   * Obtiene el user_id actual
   */
  function getUserId() {
    return sessionStorage.getItem('explorerframe_user_id');
  }

  /**
   * Verifica si el usuario está autenticado
   */
  function isAuthenticated() {
    return !!sessionStorage.getItem('explorerframe_token');
  }

  /**
   * Genera un estado aleatorio para CSRF
   */
  function generateState() {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }

  return {
    init,
    getUserInfo,
    logout,
    getToken,
    getUserId,
    isAuthenticated
  };
})();
