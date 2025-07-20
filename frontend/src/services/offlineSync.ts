// Offline Data Synchronization Service
// Handles offline data storage and synchronization for the IDF Testing System

export interface OfflineAction {
  id: string;
  type: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  data?: any;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
}

export interface OfflineData {
  key: string;
  data: any;
  timestamp: number;
  expiresAt?: number;
}

class OfflineSyncService {
  private dbName = 'idf-testing-offline';
  private dbVersion = 1;
  private db: IDBDatabase | null = null;
  private isOnline = navigator.onLine;
  private syncQueue: OfflineAction[] = [];
  private syncInProgress = false;

  constructor() {
    this.initDB();
    this.setupEventListeners();
  }

  // Initialize IndexedDB
  private async initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create object stores
        if (!db.objectStoreNames.contains('offlineActions')) {
          const actionsStore = db.createObjectStore('offlineActions', { keyPath: 'id' });
          actionsStore.createIndex('timestamp', 'timestamp', { unique: false });
          actionsStore.createIndex('type', 'type', { unique: false });
        }

        if (!db.objectStoreNames.contains('offlineData')) {
          const dataStore = db.createObjectStore('offlineData', { keyPath: 'key' });
          dataStore.createIndex('timestamp', 'timestamp', { unique: false });
          dataStore.createIndex('expiresAt', 'expiresAt', { unique: false });
        }

        if (!db.objectStoreNames.contains('syncStatus')) {
          db.createObjectStore('syncStatus', { keyPath: 'key' });
        }
      };
    });
  }

  // Setup event listeners for online/offline
  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.syncOfflineActions();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });

    // Sync on page load if online
    if (this.isOnline) {
      setTimeout(() => this.syncOfflineActions(), 1000);
    }
  }

  // Store data for offline access
  async storeOfflineData(key: string, data: any, expiresInMs?: number): Promise<void> {
    if (!this.db) await this.initDB();

    const offlineData: OfflineData = {
      key,
      data,
      timestamp: Date.now(),
      expiresAt: expiresInMs ? Date.now() + expiresInMs : undefined
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineData'], 'readwrite');
      const store = transaction.objectStore('offlineData');
      const request = store.put(offlineData);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // Get stored offline data
  async getOfflineData(key: string): Promise<any | null> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineData'], 'readonly');
      const store = transaction.objectStore('offlineData');
      const request = store.get(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const result = request.result;
        
        if (!result) {
          resolve(null);
          return;
        }

        // Check if data has expired
        if (result.expiresAt && Date.now() > result.expiresAt) {
          this.deleteOfflineData(key);
          resolve(null);
          return;
        }

        resolve(result.data);
      };
    });
  }

  // Delete offline data
  async deleteOfflineData(key: string): Promise<void> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineData'], 'readwrite');
      const store = transaction.objectStore('offlineData');
      const request = store.delete(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // Queue action for offline sync
  async queueOfflineAction(action: Omit<OfflineAction, 'id' | 'timestamp' | 'retryCount'>): Promise<void> {
    if (!this.db) await this.initDB();

    const offlineAction: OfflineAction = {
      ...action,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      retryCount: 0
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineActions'], 'readwrite');
      const store = transaction.objectStore('offlineActions');
      const request = store.add(offlineAction);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.syncQueue.push(offlineAction);
        resolve();
      };
    });
  }

  // Get all pending offline actions
  async getOfflineActions(): Promise<OfflineAction[]> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineActions'], 'readonly');
      const store = transaction.objectStore('offlineActions');
      const request = store.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  // Remove synced action
  async removeOfflineAction(id: string): Promise<void> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineActions'], 'readwrite');
      const store = transaction.objectStore('offlineActions');
      const request = store.delete(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // Sync all offline actions
  async syncOfflineActions(): Promise<void> {
    if (!this.isOnline || this.syncInProgress) return;

    this.syncInProgress = true;
    console.log('Starting offline sync...');

    try {
      const actions = await this.getOfflineActions();
      
      for (const action of actions) {
        try {
          await this.executeAction(action);
          await this.removeOfflineAction(action.id);
          console.log(`Synced action: ${action.type}`);
        } catch (error) {
          console.error(`Failed to sync action ${action.id}:`, error);
          
          // Increment retry count
          action.retryCount++;
          
          if (action.retryCount >= action.maxRetries) {
            console.error(`Action ${action.id} exceeded max retries, removing from queue`);
            await this.removeOfflineAction(action.id);
          } else {
            // Update retry count in storage
            await this.updateOfflineAction(action);
          }
        }
      }

      console.log('Offline sync completed');
    } catch (error) {
      console.error('Offline sync failed:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  // Execute a single action
  private async executeAction(action: OfflineAction): Promise<void> {
    const response = await fetch(action.url, {
      method: action.method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: action.data ? JSON.stringify(action.data) : undefined
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Update offline action
  private async updateOfflineAction(action: OfflineAction): Promise<void> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineActions'], 'readwrite');
      const store = transaction.objectStore('offlineActions');
      const request = store.put(action);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // Cache API response
  async cacheApiResponse(url: string, data: any, expiresInMs: number = 60000): Promise<void> {
    const cacheKey = `api_${url}`;
    await this.storeOfflineData(cacheKey, data, expiresInMs);
  }

  // Get cached API response
  async getCachedApiResponse(url: string): Promise<any | null> {
    const cacheKey = `api_${url}`;
    return await this.getOfflineData(cacheKey);
  }

  // Smart fetch with offline support
  async smartFetch(url: string, options: RequestInit = {}): Promise<any> {
    // Try network first
    if (this.isOnline) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            ...options.headers
          }
        });

        if (response.ok) {
          const data = await response.json();
          
          // Cache GET responses
          if (options.method === 'GET' || !options.method) {
            await this.cacheApiResponse(url, data);
          }
          
          return data;
        }
      } catch (error) {
        console.warn('Network request failed, trying cache:', error);
      }
    }

    // Fall back to cache for GET requests
    if (options.method === 'GET' || !options.method) {
      const cachedData = await this.getCachedApiResponse(url);
      if (cachedData) {
        console.log('Returning cached data for:', url);
        return cachedData;
      }
    }

    // Queue non-GET requests for later sync
    if (options.method && options.method !== 'GET') {
      await this.queueOfflineAction({
        type: 'api_call',
        method: options.method as any,
        url,
        data: options.body ? JSON.parse(options.body as string) : undefined,
        maxRetries: 3
      });
      
      // Return a placeholder response
      return { success: true, queued: true, message: 'הפעולה תבוצע כשהחיבור יחזור' };
    }

    throw new Error('No network connection and no cached data available');
  }

  // Clear expired cache
  async clearExpiredCache(): Promise<void> {
    if (!this.db) await this.initDB();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['offlineData'], 'readwrite');
      const store = transaction.objectStore('offlineData');
      const index = store.index('expiresAt');
      const request = index.openCursor();

      request.onerror = () => reject(request.error);
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          const data = cursor.value;
          if (data.expiresAt && Date.now() > data.expiresAt) {
            cursor.delete();
          }
          cursor.continue();
        } else {
          resolve();
        }
      };
    });
  }

  // Get sync status
  async getSyncStatus(): Promise<{
    pendingActions: number;
    lastSync: number | null;
    isOnline: boolean;
  }> {
    const actions = await this.getOfflineActions();
    const lastSync = await this.getOfflineData('lastSyncTime');

    return {
      pendingActions: actions.length,
      lastSync: lastSync,
      isOnline: this.isOnline
    };
  }

  // Force sync
  async forceSync(): Promise<void> {
    if (!this.isOnline) {
      throw new Error('Cannot sync while offline');
    }

    await this.syncOfflineActions();
    await this.storeOfflineData('lastSyncTime', Date.now());
  }

  // Clear all offline data
  async clearAllOfflineData(): Promise<void> {
    if (!this.db) await this.initDB();

    const transaction = this.db.transaction(['offlineData', 'offlineActions'], 'readwrite');
    
    await Promise.all([
      new Promise<void>((resolve, reject) => {
        const request = transaction.objectStore('offlineData').clear();
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
      }),
      new Promise<void>((resolve, reject) => {
        const request = transaction.objectStore('offlineActions').clear();
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
      })
    ]);
  }
}

// Export singleton instance
export const offlineSyncService = new OfflineSyncService();
export default offlineSyncService;