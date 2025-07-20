// Service Worker for IDF Testing System PWA
// Version: 1.0.0

const CACHE_NAME = 'idf-testing-v1';
const STATIC_CACHE_NAME = 'idf-static-v1';
const DYNAMIC_CACHE_NAME = 'idf-dynamic-v1';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/index.html',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
  '/api/auth/me',
  '/api/dashboard',
  '/api/buildings',
  '/api/tests'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .catch((error) => {
        console.error('Service Worker: Error caching static files:', error);
      })
  );
  
  // Force the service worker to activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  // Take control of all pages immediately
  return self.clients.claim();
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip chrome extension requests
  if (request.url.startsWith('chrome-extension://')) {
    return;
  }
  
  // Handle different types of requests
  if (request.url.includes('/api/')) {
    // API requests - Network first, then cache
    event.respondWith(networkFirstStrategy(request));
  } else if (request.destination === 'document') {
    // HTML documents - Network first, then cache
    event.respondWith(networkFirstStrategy(request));
  } else if (request.destination === 'image') {
    // Images - Cache first, then network
    event.respondWith(cacheFirstStrategy(request));
  } else {
    // Other static resources - Cache first, then network
    event.respondWith(cacheFirstStrategy(request));
  }
});

// Network first strategy - for API calls and HTML
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    
    // If network request succeeds, cache it
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Service Worker: Network failed, trying cache:', request.url);
    
    // If network fails, try cache
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // If no cache, return offline page for HTML requests
    if (request.destination === 'document') {
      return caches.match('/offline.html') || new Response(
        createOfflinePage(),
        {
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        }
      );
    }
    
    throw error;
  }
}

// Cache first strategy - for static resources
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Service Worker: Failed to fetch resource:', request.url);
    throw error;
  }
}

// Create offline page HTML
function createOfflinePage() {
  return `
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>אין חיבור לאינטרנט - מערכת בדיקות IDF</title>
      <style>
        body {
          font-family: 'Heebo', 'Arial', sans-serif;
          direction: rtl;
          text-align: center;
          padding: 2rem;
          background-color: #f8fafc;
          color: #1e293b;
        }
        .container {
          max-width: 600px;
          margin: 0 auto;
          background: white;
          padding: 3rem;
          border-radius: 10px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .icon {
          font-size: 4rem;
          margin-bottom: 1rem;
        }
        h1 {
          color: #dc2626;
          margin-bottom: 1rem;
        }
        p {
          color: #6b7280;
          margin-bottom: 1.5rem;
          line-height: 1.6;
        }
        .retry-btn {
          background: #2563eb;
          color: white;
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 5px;
          cursor: pointer;
          font-size: 1rem;
          transition: background-color 0.2s;
        }
        .retry-btn:hover {
          background: #1d4ed8;
        }
        .features {
          margin-top: 2rem;
          text-align: right;
        }
        .feature {
          margin: 1rem 0;
          padding: 1rem;
          background: #f1f5f9;
          border-radius: 5px;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="icon">📱</div>
        <h1>אין חיבור לאינטרנט</h1>
        <p>לא ניתן להתחבר לשרת. אנא בדוק את החיבור שלך לאינטרנט ונסה שוב.</p>
        
        <button class="retry-btn" onclick="window.location.reload()">נסה שוב</button>
        
        <div class="features">
          <h3>פונקציות זמינות במצב לא מקוון:</h3>
          <div class="feature">
            <strong>צפייה בנתונים שנשמרו:</strong> ניתן לצפות בנתונים שנטענו בעבר
          </div>
          <div class="feature">
            <strong>עריכה מקומית:</strong> ניתן לערוך נתונים, הם יסתנכרנו בחזרת החיבור
          </div>
          <div class="feature">
            <strong>ניווט באפליקציה:</strong> ניתן לנוע בין הדפים השונים
          </div>
        </div>
      </div>
    </body>
    </html>
  `;
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('Service Worker: Background sync triggered:', event.tag);
  
  if (event.tag === 'background-sync') {
    event.waitUntil(syncOfflineActions());
  }
});

// Sync offline actions when connection is restored
async function syncOfflineActions() {
  try {
    // Get offline actions from IndexedDB
    const offlineActions = await getOfflineActions();
    
    for (const action of offlineActions) {
      try {
        await fetch(action.url, {
          method: action.method,
          headers: action.headers,
          body: action.body
        });
        
        // Remove synced action from storage
        await removeOfflineAction(action.id);
      } catch (error) {
        console.error('Service Worker: Failed to sync action:', error);
      }
    }
  } catch (error) {
    console.error('Service Worker: Sync failed:', error);
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  console.log('Service Worker: Push message received');
  
  const options = {
    body: event.data ? event.data.text() : 'הודעה חדשה ממערכת בדיקות IDF',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    dir: 'rtl',
    lang: 'he',
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'עבור לאפליקציה',
        icon: '/icons/icon-192x192.png'
      },
      {
        action: 'close',
        title: 'סגור',
        icon: '/icons/icon-192x192.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('מערכת בדיקות IDF', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('Service Worker: Notification clicked');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    // Open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  } else if (event.action === 'close') {
    // Just close the notification
    event.notification.close();
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Helper functions for offline storage
async function getOfflineActions() {
  // This would typically use IndexedDB
  // For now, return empty array
  return [];
}

async function removeOfflineAction(id) {
  // This would typically remove from IndexedDB
  console.log('Service Worker: Removing offline action:', id);
}

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  console.log('Service Worker: Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('Service Worker: Loaded successfully');