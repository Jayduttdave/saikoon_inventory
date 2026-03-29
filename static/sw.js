const CACHE_NAME = 'saikoon-kitchen-cache-v1';
const ASSETS = [
  '/',
  '/static/style.css',
  '/static/manifest.json',
  '/images/logo.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request)
        .then((response) => {
          return caches.open(CACHE_NAME).then((cache) => {
            if (event.request.method === 'GET') {
              cache.put(event.request, response.clone());
            }
            return response;
          });
        })
        .catch(() => caches.match('/'));
    })
  );
});
