/* Service worker: offline app shell (precache) + web push. API calls are never cached. */
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()
self.addEventListener('message', (e) => e.data?.type === 'SKIP_WAITING' && self.skipWaiting())

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {}
  event.waitUntil(self.registration.showNotification(data.title || 'Thisissus 💌', {
    body: data.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    data: { url: data.url || '/' },
  }))
})

// Tap on a notification: reuse an open app window if there is one, else open the app at the target page.
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
    const open = windows.find((w) => 'focus' in w)
    if (open) return open.navigate(url).then((w) => (w || open).focus())
    return self.clients.openWindow(url)
  }))
})
