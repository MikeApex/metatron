// Service worker for Life Manager PWA v2
// Handles Web Push notifications and displays them on the device.
const CACHE_VERSION = 'v2';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
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
