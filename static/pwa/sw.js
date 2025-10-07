// 🎯 Bassam Mathematics Pro - Service Worker (Android + iOS Safari)
const CACHE = "bassam-math-cache-v1";
const ASSETS = [
  "/",
  "/static/style.css",
  "/static/main.js",
  "/static/pwa/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
});

self.addEventListener("fetch", e => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
