import React, { createContext, useContext, useEffect, useState } from 'react';
import { useMobile, useInstallPrompt, useNetworkStatus } from '../../hooks/useMobile';
import { pushNotificationService } from '../../services/pushNotifications';

interface PWAContextValue {
  // Mobile info
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  orientation: 'portrait' | 'landscape';
  touchSupport: boolean;
  
  // Network status
  isOnline: boolean;
  networkType: string;
  isSlowConnection: boolean;
  
  // Installation
  isInstallable: boolean;
  isStandalone: boolean;
  promptInstall: () => Promise<boolean>;
  
  // Push notifications
  notificationPermission: NotificationPermission;
  requestNotificationPermission: () => Promise<NotificationPermission>;
  subscribeToNotifications: () => Promise<void>;
  unsubscribeFromNotifications: () => Promise<void>;
  testNotification: () => Promise<void>;
  
  // PWA features
  showOfflineBanner: boolean;
  showInstallPrompt: boolean;
  dismissInstallPrompt: () => void;
}

const PWAContext = createContext<PWAContextValue | undefined>(undefined);

export const usePWA = () => {
  const context = useContext(PWAContext);
  if (!context) {
    throw new Error('usePWA must be used within a PWAProvider');
  }
  return context;
};

interface PWAProviderProps {
  children: React.ReactNode;
}

export const PWAProvider: React.FC<PWAProviderProps> = ({ children }) => {
  const mobileInfo = useMobile();
  const { isInstallable, promptInstall } = useInstallPrompt();
  const networkStatus = useNetworkStatus();
  
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>('default');
  const [showOfflineBanner, setShowOfflineBanner] = useState(false);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [offlineStartTime, setOfflineStartTime] = useState<number | null>(null);

  // Update notification permission status
  useEffect(() => {
    if (pushNotificationService.isSupported()) {
      setNotificationPermission(pushNotificationService.getPermissionStatus());
    }
  }, []);

  // Handle online/offline status
  useEffect(() => {
    if (!networkStatus.isOnline) {
      setOfflineStartTime(Date.now());
      // Show offline banner after 2 seconds
      const timer = setTimeout(() => {
        setShowOfflineBanner(true);
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      setShowOfflineBanner(false);
      if (offlineStartTime) {
        const offlineDuration = Date.now() - offlineStartTime;
        if (offlineDuration > 5000) { // Show notification if offline for more than 5 seconds
          pushNotificationService.showLocalNotification({
            title: 'חיבור לאינטרנט חודש',
            body: 'המערכת חזרה לפעילות רגילה',
            icon: '/icons/icon-192x192.png',
            tag: 'connection-restored'
          }).catch(console.error);
        }
        setOfflineStartTime(null);
      }
    }
  }, [networkStatus.isOnline, offlineStartTime]);

  // Handle install prompt
  useEffect(() => {
    if (isInstallable && !mobileInfo.isStandalone) {
      // Show install prompt after 30 seconds of usage
      const timer = setTimeout(() => {
        setShowInstallPrompt(true);
      }, 30000);
      return () => clearTimeout(timer);
    }
  }, [isInstallable, mobileInfo.isStandalone]);

  const requestNotificationPermission = async (): Promise<NotificationPermission> => {
    try {
      const permission = await pushNotificationService.requestPermission();
      setNotificationPermission(permission);
      return permission;
    } catch (error) {
      console.error('Failed to request notification permission:', error);
      return 'denied';
    }
  };

  const subscribeToNotifications = async (): Promise<void> => {
    try {
      await pushNotificationService.subscribe();
      setNotificationPermission('granted');
    } catch (error) {
      console.error('Failed to subscribe to notifications:', error);
      throw error;
    }
  };

  const unsubscribeFromNotifications = async (): Promise<void> => {
    try {
      await pushNotificationService.unsubscribe();
    } catch (error) {
      console.error('Failed to unsubscribe from notifications:', error);
      throw error;
    }
  };

  const testNotification = async (): Promise<void> => {
    try {
      await pushNotificationService.testNotification();
    } catch (error) {
      console.error('Failed to test notification:', error);
      throw error;
    }
  };

  const dismissInstallPrompt = () => {
    setShowInstallPrompt(false);
  };

  const contextValue: PWAContextValue = {
    // Mobile info
    isMobile: mobileInfo.isMobile,
    isTablet: mobileInfo.isTablet,
    isDesktop: mobileInfo.isDesktop,
    orientation: mobileInfo.orientation,
    touchSupport: mobileInfo.touchSupport,
    
    // Network status
    isOnline: networkStatus.isOnline,
    networkType: networkStatus.networkType,
    isSlowConnection: networkStatus.isSlowConnection,
    
    // Installation
    isInstallable,
    isStandalone: mobileInfo.isStandalone,
    promptInstall,
    
    // Push notifications
    notificationPermission,
    requestNotificationPermission,
    subscribeToNotifications,
    unsubscribeFromNotifications,
    testNotification,
    
    // PWA features
    showOfflineBanner,
    showInstallPrompt,
    dismissInstallPrompt
  };

  return (
    <PWAContext.Provider value={contextValue}>
      {children}
      {showOfflineBanner && <OfflineBanner />}
      {showInstallPrompt && <InstallPrompt onDismiss={dismissInstallPrompt} />}
    </PWAContext.Provider>
  );
};

// Offline Banner Component
const OfflineBanner: React.FC = () => {
  return (
    <div className="mobile-offline-banner show">
      <div className="flex items-center justify-center gap-2">
        <span>📱</span>
        <span>אין חיבור לאינטרנט - פועל במצב לא מקוון</span>
      </div>
    </div>
  );
};

// Install Prompt Component
interface InstallPromptProps {
  onDismiss: () => void;
}

const InstallPrompt: React.FC<InstallPromptProps> = ({ onDismiss }) => {
  const { promptInstall } = usePWA();

  const handleInstall = async () => {
    try {
      const accepted = await promptInstall();
      if (accepted) {
        onDismiss();
      }
    } catch (error) {
      console.error('Install failed:', error);
    }
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:max-w-sm md:left-auto md:right-4">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4 mobile-slide-up">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-xl">📱</span>
            </div>
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-gray-900 mb-1">
              התקן את האפליקציה
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              התקן את מערכת בדיקות IDF כאפליקציה עצמאית לגישה מהירה
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleInstall}
                className="flex-1 bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                התקן
              </button>
              <button
                onClick={onDismiss}
                className="flex-1 bg-gray-100 text-gray-700 px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                לא עכשיו
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PWAProvider;