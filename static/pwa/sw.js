// 🎯 Bassam Mathematics Pro - Service Worker (للتشغيل بدون إنترنت)

self.addEventListener('install', event => {
  console.log('🟣 Service Worker: installing...');
  event.waitUntil(
    caches.open('bassam-math-cache-v1').then(cache => {
      return cache.addAll([
        '/',
        '/static/style.css',
        '/static/main.js',
        '/static/pwa/manifest.json'
      ]);
    })
  );
});

self.addEventListener('activate', event => {
  console.log('🟢 Service Worker: activated');
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== 'bassam-math-cache-v1')
            .map(key => caches.delete(key))
      );
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      // ✅ استخدم الملف من الكاش إذا كان متوفرًا، أو من الإنترنت إن لم يكن
      return response || fetch(event.request);
    })
  );
});
