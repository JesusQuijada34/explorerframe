/**
 * ExplorerFrame — Notificaciones + NEWS.md en tiempo real
 */

'use strict';

// ── Permiso de notificaciones ──────────────────────────────────────────────
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function sendSystemNotification(title, body, tag = 'ef-notification') {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/app/app-icon.ico',
      badge: '/app/app-icon.ico',
      tag,
      renotify: true
    });
  }
}

// ── Service Worker ─────────────────────────────────────────────────────────
async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register('/static/sw.js', { scope: '/' });
    console.log('[SW] registrado:', reg.scope);
  } catch (err) {
    console.warn('[SW] error al registrar:', err);
  }
}

// ── Convertir Markdown a HTML (cards por sección) ─────────────────────────
function markdownToCards(md) {
  const ACCENT_COLORS = ['#ff6b6b','#51cf66','#4dabf7','#ffd43b','#a78bfa','#f783ac','#74c0fc'];
  let colorIdx = 0;

  const lines = md.split('\n');
  let html = '';
  let inCard = false;
  let inList = false;
  let inStats = false;

  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  const closeCard = () => {
    closeList();
    if (inStats) { html += '</div>'; inStats = false; }
    if (inCard)  { html += '</div>'; inCard = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // H1 → título principal de la sección
    if (/^# /.test(line)) {
      closeCard();
      const title = line.replace(/^# /, '').trim();
      html += `<h2 class="news-title">${title}</h2>`;
      continue;
    }

    // H2 → nueva card
    if (/^## /.test(line)) {
      closeCard();
      const color = ACCENT_COLORS[colorIdx++ % ACCENT_COLORS.length];
      const title = line.replace(/^## /, '').trim();
      html += `<div class="news-card" style="--card-accent:${color}">`;
      html += `<h3 class="news-card-title">${title}</h3>`;
      inCard = true;
      continue;
    }

    // H3 → subtítulo dentro de card
    if (/^### /.test(line)) {
      closeList();
      const title = line.replace(/^### /, '').trim();
      html += `<h4 class="news-card-sub">${title}</h4>`;
      continue;
    }

    // Separador ---
    if (/^---+$/.test(line.trim())) {
      closeCard();
      continue;
    }

    // Lista
    if (/^[-*] /.test(line)) {
      if (!inList) { html += '<ul class="news-list">'; inList = true; }
      const item = line.replace(/^[-*] /, '').trim();
      html += `<li>${inlineFormat(item)}</li>`;
      continue;
    }

    // Línea vacía
    if (line.trim() === '') {
      closeList();
      continue;
    }

    // Párrafo normal
    if (inCard) {
      closeList();
      html += `<p class="news-p">${inlineFormat(line.trim())}</p>`;
    }
  }

  closeCard();
  return html;
}

// Formato inline: **bold**, `code`
function inlineFormat(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

// ── Carga en tiempo real ───────────────────────────────────────────────────
let _lastModified = null;

async function fetchAndRenderNews(container, isInitial = false) {
  try {
    const res = await fetch('/api/v1/news', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    const modified = data.lastModified;

    // Primera carga: siempre renderizar
    // Cargas siguientes: solo si cambió
    if (isInitial || modified !== _lastModified) {
      if (!isInitial && _lastModified !== null) {
        // Hubo un cambio real → notificar
        sendSystemNotification(
          '📰 Noticias actualizadas',
          'Se han publicado novedades en ExplorerFrame'
        );
      }
      _lastModified = modified;

      // Renderizar desde el markdown crudo
      const cards = markdownToCards(data.markdown);
      container.innerHTML = cards;
      container.classList.remove('news-loading');
    }
  } catch (err) {
    if (isInitial) {
      container.innerHTML = '<p class="news-error">No se pudieron cargar las noticias.</p>';
      container.classList.remove('news-loading');
    }
    console.warn('[NEWS] error:', err);
  }
}

function initNewsRealTime() {
  const container = document.getElementById('news-container');
  if (!container) return;

  // Carga inicial inmediata
  fetchAndRenderNews(container, true);

  // Polling cada 30 s
  setInterval(() => fetchAndRenderNews(container, false), 30_000);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  requestNotificationPermission();
  registerServiceWorker();
  initNewsRealTime();
});


// ── PWA Install Prompt ─────────────────────────────────────────────────────
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  showInstallPrompt();
});

function showInstallPrompt() {
  const prompt = document.createElement('div');
  prompt.className = 'pwa-install-prompt';
  prompt.innerHTML = `
    <h3>📱 Instalar ExplorerFrame</h3>
    <p>Instala la app para acceso rápido y notificaciones en tiempo real.</p>
    <div class="pwa-install-actions">
      <button class="btn-install">Instalar</button>
      <button class="btn-dismiss">Ahora no</button>
    </div>
  `;

  prompt.querySelector('.btn-install').addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log('[PWA] Resultado:', outcome);
    deferredPrompt = null;
    prompt.remove();
  });

  prompt.querySelector('.btn-dismiss').addEventListener('click', () => {
    prompt.remove();
    // No mostrar de nuevo en esta sesión
    sessionStorage.setItem('pwa-prompt-dismissed', 'true');
  });

  // Solo mostrar si no se ha descartado en esta sesión
  if (!sessionStorage.getItem('pwa-prompt-dismissed')) {
    document.body.appendChild(prompt);
  }
}

// Detectar cuando la app se instala
window.addEventListener('appinstalled', () => {
  console.log('[PWA] App instalada');
  sendSystemNotification(
    '✅ ExplorerFrame instalado',
    'La app está lista para usar offline'
  );
});

// ── Actualización del Service Worker ──────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    console.log('[SW] Nueva versión disponible');
    if (confirm('Hay una nueva versión de ExplorerFrame. ¿Recargar ahora?')) {
      window.location.reload();
    }
  });
}
