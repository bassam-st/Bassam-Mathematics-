// sw.js — Bassam Math Pro (Offline Cache)
const CACHE_NAME = "bassam-math-cache-v1";
const OFFLINE_URLS = [
  "/",
  "/static/style.css",
  "/static/main.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

// عند التثبيت: نحفظ الملفات الأساسية
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(OFFLINE_URLS))
  );
  self.skipWaiting();
});

// عند التفعيل: نحذف النسخ القديمة
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(k => k !== CACHE_NAME && caches.delete(k)))
    )
  );
  self.clients.claim();
});

// عند الطلب: نحاول الشبكة أولاً، وإذا فشلت نستخدم الكاش
self.addEventListener("fetch", (event) => {
  const { request } = event;
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
