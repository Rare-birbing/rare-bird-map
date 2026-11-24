// Service Worker：讓這個網頁可以「安裝」到手機主畫面，並把程式本身存起來加快開啟。
// 鳥況資料（eBird / iNaturalist / 地圖）一律即時從網路抓，不存舊的。
const CACHE = 'rarebird-v1';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  const isShell = e.request.mode === 'navigate' || url.origin === location.origin || url.hostname === 'cdnjs.cloudflare.com';
  if (!isShell || e.request.method !== 'GET') return;           // 其他請求照常走網路
  // 先用網路拿最新版，沒網路時才用存起來的
  e.respondWith(fetch(e.request).then(r => {
    const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r;
  }).catch(() => caches.match(e.request).then(r => r || caches.match('./index.html'))));
});
