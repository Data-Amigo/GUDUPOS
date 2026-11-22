// Minimal service worker so the app can be installed on the home screen.
// Network first: the POS always shows live data; the cached shell is only a fallback.
const CACHE = "gudu-shell-v3";
const SHELL = ["/", "/static/styles.css?v=3", "/static/app.js?v=3", "/static/icon.svg"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match("/"))));
});
