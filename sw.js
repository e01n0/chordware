/* CHORDWARE service worker.
   - HTML (the app shell) is NETWORK-FIRST: every launch tries the
     server, so deploys show up on the next open; the cached copy is
     only used offline or on very slow connections (4s timeout).
   - Everything else (Google Fonts) is cache-first with a background
     refresh.
   The app itself is a single index.html; this sidecar exists only
   because browsers won't load a SW from an inline/blob source. */
/* __BUILD__ is replaced with the git commit SHA by the Render build
   command (see render.yaml), so every deploy changes this file's bytes,
   forcing the browser's SW update cycle and a fresh cache. Locally it
   stays as-is, which is still a valid (constant) cache name. */
const CACHE = "chordware-__BUILD__";

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(["./", "./index.html"]))
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

  const isShell = e.request.mode === "navigate"
    || new URL(e.request.url).pathname.endsWith("/index.html");

  if (isShell) {
    // network-first with offline fallback
    e.respondWith((async () => {
      try {
        const res = await Promise.race([
          fetch(e.request),
          new Promise((_, rej) => setTimeout(() => rej(new Error("sw-timeout")), 4000)),
        ]);
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return res;
      } catch (err) {
        return (await caches.match(e.request)) || (await caches.match("./index.html"));
      }
    })());
    return;
  }

  // assets: serve from cache, refresh in the background
  e.respondWith((async () => {
    const hit = await caches.match(e.request);
    const refresh = fetch(e.request).then(res => {
      const cacheable = res.ok || res.type === "opaque";
      const url = e.request.url;
      if (cacheable && (url.startsWith(self.location.origin) || url.includes("fonts.googleapis.com") || url.includes("fonts.gstatic.com"))) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    });
    if (hit) { refresh.catch(() => {}); return hit; }
    return refresh;
  })());
});
