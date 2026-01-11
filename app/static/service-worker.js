// Service Worker for CuraSlot PWA
const CACHE_NAME = 'curaslot-v1';
const urlsToCache = [
    '/',
    '/city/bhopal',
    '/city/dubai',
    '/city/new-york',
    '/doctor/login',
    '/static/images/curaslot-logo.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css'
];

// Install event - cache critical resources
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache hit - return response
                if (response) {
                    return response;
                }

                return fetch(event.request).then(
                    fetchResponse => {
                        // Check if valid response
                        if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
                            return fetchResponse;
                        }

                        // Clone the response
                        const responseToCache = fetchResponse.clone();

                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return fetchResponse;
                    }
                );
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];

    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
