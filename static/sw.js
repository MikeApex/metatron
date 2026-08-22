// Service worker for Life Manager PWA v2
// Handles Web Push notifications, and serves an offline shell when the server
// cannot be reached.
//
// Deliberately NOT a caching service worker. Only offline.html is ever cached,
// and it is only ever served when a navigation request has already failed on
// the network. `/` and index.html are never cached: a stale app shell served
// from a service worker is sticky and painful to recover from, which is the
// whole reason this was built as a fallback rather than a cache-first shell.
//
// Recovery lever: bump OFFLINE_CACHE. `activate` deletes every cache whose name
// is not the current one, so a wrong shell is cleared by the next SW update
// (and /sw.js is served no-store, so that update propagates immediately).
const OFFLINE_CACHE = 'offline-v1';
const OFFLINE_URL = '/static/offline.html';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(OFFLINE_CACHE)
      // cache: 'reload' so the shell comes from the network, never from an
      // HTTP cache entry that may itself be stale.
      .then(cache => cache.add(new Request(OFFLINE_URL, { cache: 'reload' })))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== OFFLINE_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Navigations only. API calls, the WebSocket upgrade and every static asset
  // pass through untouched — returning without calling respondWith() leaves the
  // request entirely to the browser.
  if (event.request.mode !== 'navigate') return;

  // Network first, always. The cached shell is the catch path only.
  event.respondWith(
    fetch(event.request).catch(() =>
      caches.open(OFFLINE_CACHE)
        .then(cache => cache.match(OFFLINE_URL))
        .then(cached => cached || new Response(
          'Offline',
          { status: 503, headers: { 'Content-Type': 'text/plain' } }
        ))
    )
  );
});

self.addEventListener('push', event => {
  let title = 'Life Manager';
  let body = 'New message';
  if (event.data) {
    try {
      const d = JSON.parse(event.data.text());
      if (d.title) title = d.title;
      if (d.body) body = d.body;
    } catch {
      body = event.data.text() || 'New message';
    }
  }
  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      tag: 'life-manager',
      renotify: true,
      requireInteraction: false,
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
