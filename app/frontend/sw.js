// Service Worker do CondoOS
const CACHE_NAME = 'condoos-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192x192.png',
  '/icon-512x512.png'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Cache aberto');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((err) => {
        console.error('[SW] Erro ao adicionar ao cache:', err);
      })
  );
  
  self.skipWaiting();
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Ativando...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deletando cache antigo:', name);
            return caches.delete(name);
          })
      );
    })
  );
  
  self.clients.claim();
});

// Interceptação de requisições
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Estratégia: Network First para API, Cache First para assets estáticos
  if (url.pathname.startsWith('/api/')) {
    // Network First para API
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clonar resposta para cache
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // Se falhar, tentar do cache
          return caches.match(request);
        })
    );
  } else if (request.method === 'GET') {
    // Cache First para assets estáticos
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          // Retornar do cache e atualizar em background
          fetch(request)
            .then((response) => {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, response);
              });
            })
            .catch(() => {});
          return cachedResponse;
        }
        
        // Se não estiver no cache, buscar e adicionar
        return fetch(request).then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        });
      })
    );
  }
});

// Notificações Push
self.addEventListener('push', (event) => {
  console.log('[SW] Push recebido:', event);
  
  const data = event.data?.json() || {};
  const title = data.title || 'CondoOS';
  const options = {
    body: data.message || 'Nova notificação',
    icon: '/icon-192x192.png',
    badge: '/icon-72x72.png',
    tag: data.order_id || 'default',
    data: data,
    actions: [
      {
        action: 'open',
        title: 'Abrir'
      },
      {
        action: 'close',
        title: 'Fechar'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Clique na notificação:', event);
  
  event.notification.close();
  
  const { notification } = event;
  const orderId = notification.data?.order_id;
  
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((clientList) => {
        const url = orderId ? `/orders/${orderId}` : '/';
        
        // Se já tiver uma janela aberta, focar nela
        for (const client of clientList) {
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Senão, abrir nova janela
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
    );
  }
});

// Sincronização em background
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event);
  
  if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  }
});

async function syncOrders() {
  // Implementar sincronização de ordens pendentes
  console.log('[SW] Sincronizando ordens...');
}
