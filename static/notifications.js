/**
 * Sistema de notificaciones para ExplorerFrame
 * Maneja Web Push Notifications y lectura en tiempo real de NEWS.md
 */

// Solicitar permiso para notificaciones push
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

// Enviar notificación push del sistema
function sendSystemNotification(title, options = {}) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      icon: '/app/app-icon.ico',
      badge: '/app/app-icon.ico',
      ...options
    });
  }
}

// Cargar NEWS.md en tiempo real
async function loadNewsInRealTime() {
  const newsContainer = document.getElementById('news-container');
  if (!newsContainer) return;

  let lastModified = null;

  async function fetchNews() {
    try {
      const response = await fetch('/api/v1/news', { cache: 'no-store' });
      if (response.ok) {
        const data = await response.json();
        const currentModified = data.lastModified;

        // Si cambió, actualizar y notificar
        if (lastModified && currentModified !== lastModified) {
          newsContainer.innerHTML = data.html;
          sendSystemNotification('📰 Noticias Actualizadas', {
            body: 'Se han actualizado las novedades de ExplorerFrame',
            tag: 'news-update'
          });
        }

        lastModified = currentModified;
      }
    } catch (error) {
      console.error('Error cargando noticias:', error);
    }
  }

  // Cargar inicialmente
  await fetchNews();

  // Verificar cada 30 segundos
  setInterval(fetchNews, 30000);
}

// Registrar Service Worker para notificaciones push
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      await navigator.serviceWorker.register('/static/sw.js');
      console.log('Service Worker registrado');
    } catch (error) {
      console.error('Error registrando Service Worker:', error);
    }
  }
}

// Inicializar notificaciones al cargar la página
document.addEventListener('DOMContentLoaded', () => {
  requestNotificationPermission();
  registerServiceWorker();
  loadNewsInRealTime();
});
