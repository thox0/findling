// Macht den letzten Stand unterwegs lesbar. Geändert wird weiter nur im Heimnetz, auf dem Mac liegt das Original.
const SHELL = "findling-oberflaeche-v2";
const DATA = "werkstatt-daten-v1";
const SHELL_FILES = ["/", "/style.css", "/app.js", "/vendor/qrcode.js", "/vendor/jsQR.js", "/lang/en.js", "/manifest.webmanifest", "/icon-180.png", "/icon-192.png", "/icon-512.png", "/logo.svg", "/favicon.svg"];
const WAIT_MS = 3500;
const OFFLINE_MESSAGE = "Das geht nur im Heimnetz. Der Mac ist gerade nicht erreichbar.";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys()
    .then((names) => Promise.all(names.filter((name) => name !== SHELL && name !== DATA).map((name) => caches.delete(name))))
    .then(() => self.clients.claim()));
});

function withTimeout(request) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), WAIT_MS);
  return fetch(request, { signal: controller.signal }).finally(() => clearTimeout(timer));
}

function offlineAnswer() {
  return new Response(JSON.stringify({ error: OFFLINE_MESSAGE }), {
    status: 503,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

async function state(request) {
  const cache = await caches.open(DATA);
  try {
    const response = await withTimeout(request);
    if (response.ok) {
      const body = await response.clone().text();
      await cache.put("/api/state", new Response(body, {
        headers: { "Content-Type": "application/json; charset=utf-8", "X-Stand": String(Date.now()) },
      }));
    }
    return response;
  } catch {
    const saved = await cache.match("/api/state");
    if (!saved) return offlineAnswer();
    const headers = new Headers(saved.headers);
    headers.set("X-Offline-Stand", saved.headers.get("X-Stand") || "");
    return new Response(await saved.text(), { headers });
  }
}

async function photo(request) {
  const cache = await caches.open(DATA);
  const saved = await cache.match(request.url);
  if (saved) return saved;
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request.url, response.clone());
    return response;
  } catch {
    return new Response("", { status: 404 });
  }
}

async function shell(request) {
  const cache = await caches.open(SHELL);
  const key = request.mode === "navigate" ? "/" : request.url;
  try {
    const response = await withTimeout(request);
    if (response.ok) await cache.put(key, response.clone());
    return response;
  } catch {
    return (await cache.match(key)) || new Response("Nicht verfügbar", { status: 503 });
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/api/state") event.respondWith(state(request));
  else if (url.pathname.startsWith("/api/")) event.respondWith(fetch(request).catch(offlineAnswer));
  else if (url.pathname.startsWith("/fotos/")) event.respondWith(photo(request));
  else event.respondWith(shell(request));
});

// Schrankfotos und Raumpläne vorab sichern, damit die Suche unterwegs auch die Lage zeigt.
self.addEventListener("message", (event) => {
  if (event.data?.type !== "photos") return;
  event.waitUntil((async () => {
    const cache = await caches.open(DATA);
    for (const url of event.data.urls) {
      if (await cache.match(new URL(url, self.location.origin).href)) continue;
      try {
        const response = await fetch(url);
        if (response.ok) await cache.put(new URL(url, self.location.origin).href, response);
      } catch {
        return;
      }
    }
  })());
});
