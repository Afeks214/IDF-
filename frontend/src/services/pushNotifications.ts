// Push Notification Service for IDF Testing System
// Hebrew-optimized push notifications with RTL support

export interface PushNotificationPayload {
  title: string;
  body: string;
  icon?: string;
  badge?: string;
  tag?: string;
  data?: any;
  actions?: Array<{
    action: string;
    title: string;
    icon?: string;
  }>;
  silent?: boolean;
  timestamp?: number;
  priority?: 'high' | 'normal' | 'low';
}

export interface PushSubscriptionInfo {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  userAgent: string;
  platform: string;
}

class PushNotificationService {
  private vapidPublicKey: string = import.meta.env.VITE_VAPID_PUBLIC_KEY || '';
  private serviceWorkerRegistration: ServiceWorkerRegistration | null = null;

  constructor() {
    this.initialize();
  }

  private async initialize() {
    if ('serviceWorker' in navigator) {
      try {
        this.serviceWorkerRegistration = await navigator.serviceWorker.getRegistration() || null;
        console.log('Push service initialized');
      } catch (error) {
        console.error('Failed to initialize push service:', error);
      }
    }
  }

  // Check if push notifications are supported
  isSupported(): boolean {
    return (
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  // Get current permission status
  getPermissionStatus(): NotificationPermission {
    return Notification.permission;
  }

  // Request permission for push notifications
  async requestPermission(): Promise<NotificationPermission> {
    if (!this.isSupported()) {
      throw new Error('Push notifications are not supported');
    }

    let permission = Notification.permission;

    if (permission === 'default') {
      permission = await Notification.requestPermission();
    }

    return permission;
  }

  // Subscribe to push notifications
  async subscribe(): Promise<PushSubscriptionInfo | null> {
    if (!this.isSupported()) {
      throw new Error('Push notifications are not supported');
    }

    const permission = await this.requestPermission();
    if (permission !== 'granted') {
      throw new Error('Push notification permission denied');
    }

    if (!this.serviceWorkerRegistration) {
      throw new Error('Service worker not registered');
    }

    try {
      const subscription = await this.serviceWorkerRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlB64ToUint8Array(this.vapidPublicKey)
      });

      const subscriptionInfo: PushSubscriptionInfo = {
        endpoint: subscription.endpoint,
        keys: {
          p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')!),
          auth: this.arrayBufferToBase64(subscription.getKey('auth')!)
        },
        userAgent: navigator.userAgent,
        platform: navigator.platform
      };

      // Send subscription to server
      await this.sendSubscriptionToServer(subscriptionInfo);

      return subscriptionInfo;
    } catch (error) {
      console.error('Failed to subscribe to push notifications:', error);
      throw error;
    }
  }

  // Unsubscribe from push notifications
  async unsubscribe(): Promise<boolean> {
    if (!this.serviceWorkerRegistration) {
      return false;
    }

    try {
      const subscription = await this.serviceWorkerRegistration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
        // Notify server about unsubscription
        await this.removeSubscriptionFromServer(subscription.endpoint);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to unsubscribe from push notifications:', error);
      return false;
    }
  }

  // Get current subscription
  async getSubscription(): Promise<PushSubscription | null> {
    if (!this.serviceWorkerRegistration) {
      return null;
    }

    try {
      return await this.serviceWorkerRegistration.pushManager.getSubscription();
    } catch (error) {
      console.error('Failed to get push subscription:', error);
      return null;
    }
  }

  // Show local notification (for testing)
  async showLocalNotification(payload: PushNotificationPayload): Promise<void> {
    const permission = await this.requestPermission();
    if (permission !== 'granted') {
      throw new Error('Notification permission denied');
    }

    const options: NotificationOptions = {
      body: payload.body,
      icon: payload.icon || '/icons/icon-192x192.png',
      badge: payload.badge || '/icons/icon-72x72.png',
      tag: payload.tag || 'idf-notification',
      data: payload.data || {},
      // timestamp: payload.timestamp || Date.now(), // Removed due to type issues
      dir: 'rtl',
      lang: 'he',
      silent: payload.silent || false,
      actions: payload.actions || [],
      vibrate: [100, 50, 100],
      requireInteraction: payload.priority === 'high'
    };

    const notification = new Notification(payload.title, options);

    // Auto-close notification after 5 seconds unless high priority
    if (payload.priority !== 'high') {
      setTimeout(() => {
        notification.close();
      }, 5000);
    }

    notification.onclick = () => {
      window.focus();
      if (payload.data && payload.data.url) {
        window.location.href = payload.data.url;
      }
      notification.close();
    };
  }

  // Send subscription to server
  private async sendSubscriptionToServer(subscription: PushSubscriptionInfo): Promise<void> {
    try {
      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(subscription)
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to send subscription to server:', error);
      throw error;
    }
  }

  // Remove subscription from server
  private async removeSubscriptionFromServer(endpoint: string): Promise<void> {
    try {
      const response = await fetch('/api/push/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ endpoint })
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to remove subscription from server:', error);
      throw error;
    }
  }

  // Utility function to convert VAPID key
  private urlB64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
  }

  // Convert ArrayBuffer to base64
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }

  // Test notification functionality
  async testNotification(): Promise<void> {
    const testPayload: PushNotificationPayload = {
      title: 'מערכת בדיקות IDF',
      body: 'זוהי הודעת בדיקה למערכת ההתראות',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      tag: 'test-notification',
      data: {
        url: '/dashboard',
        type: 'test'
      },
      actions: [
        {
          action: 'view',
          title: 'הצג',
          icon: '/icons/icon-192x192.png'
        },
        {
          action: 'dismiss',
          title: 'סגור',
          icon: '/icons/icon-192x192.png'
        }
      ],
      priority: 'normal'
    };

    await this.showLocalNotification(testPayload);
  }

  // Hebrew-specific notification templates
  createHebrewNotification(type: string, data: any): PushNotificationPayload {
    const templates = {
      'test_completed': {
        title: 'בדיקה הושלמה',
        body: `בדיקה ${data.testName} הושלמה בהצלחה`,
        icon: '/icons/icon-192x192.png',
        data: { url: '/tests', testId: data.testId }
      },
      'test_failed': {
        title: 'בדיקה נכשלה',
        body: `בדיקה ${data.testName} נכשלה - נדרשת התערבות`,
        icon: '/icons/icon-192x192.png',
        data: { url: '/tests', testId: data.testId },
        priority: 'high' as const
      },
      'system_alert': {
        title: 'התראת מערכת',
        body: data.message,
        icon: '/icons/icon-192x192.png',
        data: { url: '/dashboard' },
        priority: 'high' as const
      },
      'maintenance_scheduled': {
        title: 'תחזוקה מתוכננת',
        body: `תחזוקת מערכת מתוכננת ל-${data.scheduledTime}`,
        icon: '/icons/icon-192x192.png',
        data: { url: '/dashboard' }
      },
      'report_ready': {
        title: 'דוח מוכן',
        body: `דוח ${data.reportName} מוכן לצפייה`,
        icon: '/icons/icon-192x192.png',
        data: { url: '/reports', reportId: data.reportId }
      }
    };

    return templates[type as keyof typeof templates] || {
      title: 'הודעה חדשה',
      body: data.message || 'הודעה חדשה ממערכת בדיקות IDF',
      icon: '/icons/icon-192x192.png',
      data: { url: '/dashboard' }
    };
  }

  // Schedule local notification
  scheduleNotification(payload: PushNotificationPayload, delayMs: number): void {
    setTimeout(() => {
      this.showLocalNotification(payload);
    }, delayMs);
  }

  // Clear all notifications
  clearAllNotifications(): void {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(registration => {
          if (registration.getNotifications) {
            registration.getNotifications().then(notifications => {
              notifications.forEach(notification => {
                notification.close();
              });
            });
          }
        });
      });
    }
  }
}

// Export singleton instance
export const pushNotificationService = new PushNotificationService();
export default pushNotificationService;