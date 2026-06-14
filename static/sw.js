/**
 * ExplorerFrame Service Worker
 * PWA con caché offline + notificaciones push
 */

const CACHE_NAME = 'explorerframe-v1.2';
const STATIC_ASSETS = [
  '/',
  '/static/style.css',
  '/static/notifications.js',
  '/static/manifest.json',
  '/app/app-icon.ico'
];

// ── Install: cachear assets estáticos ──────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Cacheando assets estáticos');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: limpiar cachés antiguos ──────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activando...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Eliminando caché antigua:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// ── Fetch: estrategia Network First con fallback a caché ──────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Solo cachear requests del mismo origen
  if (url.origin !== location.origin) return;

  // API de noticias: siempre network first (no cachear)
  if (url.pathname === '/api/v1/news') {
    event.respondWith(fetch(request));
    return;
  }

  // Estrategia: Network First, fallback a Cache
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Si la respuesta es válida, cachearla
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Si falla la red, intentar desde caché
        return caches.match(request).then((cached) => {
          if (cached) {
            console.log('[SW] Sirviendo desde caché:', request.url);
            return cached;
          }
          // Si no hay caché, mostrar página offline
          if (request.mode === 'navigate') {
            return caches.match('/');
          }
        });
      })
  );
});

// ── Push: notificaciones push ──────────────────────────────────────────────
self.addEventListener('push', (event) => {
  console.log('[SW] Push recibido');
  
  let data = { title: 'ExplorerFrame', body: 'Nueva notificación' };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || 'Nueva notificación de ExplorerFrame',
    icon: '/app/app-icon.ico',
    badge: '/app/app-icon.ico',
    tag: data.tag || 'explorerframe-notification',
    requireInteraction: data.requireInteraction || false,
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' }
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'ExplorerFrame', options)
  );
});

// ── Notification Click: abrir la app ───────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notificación clickeada');
  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Si ya hay una ventana abierta, enfocarla
      for (const client of clientList) {
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      // Si no, abrir nueva ventana
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// ── Sync: sincronización en segundo plano ──────────────────────────────────
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync:', event.tag);
  if (event.tag === 'sync-news') {
    event.waitUntil(
      fetch('/api/v1/news', { cache: 'no-store' })
        .then((response) => response.json())
        .then((data) => {
          console.log('[SW] Noticias sincronizadas');
          // Notificar a todos los clientes
          return self.clients.matchAll().then((clients) => {
            clients.forEach((client) => {
              client.postMessage({
                type: 'NEWS_UPDATED',
                data: data
              });
            });
          });
        })
        .catch((err) => console.warn('[SW] Error en sync:', err))
    );
  }
});

// ── Message: comunicación con la página ───────────────────────────────────
self.addEventListener('message', (event) => {
  console.log('[SW] Mensaje recibido:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.addAll(event.data.urls);
      })
    );
  }
});
