const SHELL = ["/tabsmith/", "/tabsmith/manifest.webmanifest", "/tabsmith/icon-192.png"];
self.addEventListener("install", e => e.waitUntil(caches.open("tabsmith-v1").then(c => c.addAll(SHELL))));
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.startsWith("/jobs") || u.pathname.startsWith("/share")) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
