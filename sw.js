/* CHORDWARE service worker — cache-first so the app works offline
   once loaded. The app itself is a single index.html; this sidecar
   exists only because browsers won't load a SW from an inline/blob
   source. Bump CACHE to invalidate after deploying changes. */
const CACHE = "chordware-v1";

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(["./", "./index.html", "./sw.js"]))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      // runtime-cache same-origin files and Google Fonts (css + woff2)
      const cacheable = res.ok || res.type === "opaque";
      const url = e.request.url;
      if (cacheable && (url.startsWith(self.location.origin) || url.includes("fonts.googleapis.com") || url.includes("fonts.gstatic.com"))) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() =>
      e.request.mode === "navigate" ? caches.match("./index.html") : Response.error()
    ))
  );
});
