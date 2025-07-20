// PWA Testing Utilities
// Comprehensive testing suite for PWA functionality

import { pushNotificationService } from '../services/pushNotifications';
import { offlineSyncService } from '../services/offlineSync';

export interface PWATestResult {
  test: string;
  passed: boolean;
  message: string;
  details?: any;
}

export class PWATestSuite {
  private results: PWATestResult[] = [];

  async runAllTests(): Promise<PWATestResult[]> {
    this.results = [];
    
    console.log('🧪 Starting PWA Test Suite...');
    
    await this.testServiceWorker();
    await this.testPushNotifications();
    await this.testOfflineSync();
    await this.testManifest();
    await this.testMobileFeatures();
    await this.testHebrewRTL();
    await this.testNetworkStatus();
    await this.testInstallPrompt();
    
    console.log('🏁 PWA Test Suite Complete');
    console.table(this.results);
    
    return this.results;
  }

  private addResult(test: string, passed: boolean, message: string, details?: any): void {
    this.results.push({ test, passed, message, details });
    console.log(`${passed ? '✅' : '❌'} ${test}: ${message}`);
  }

  // Test Service Worker Registration
  private async testServiceWorker(): Promise<void> {
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        if (registration) {
          this.addResult(
            'Service Worker Registration',
            true,
            'Service worker is registered and active',
            { scope: registration.scope, state: registration.active?.state }
          );
        } else {
          this.addResult(
            'Service Worker Registration',
            false,
            'Service worker is not registered'
          );
        }
      } else {
        this.addResult(
          'Service Worker Support',
          false,
          'Service workers are not supported in this browser'
        );
      }
    } catch (error) {
      this.addResult(
        'Service Worker Registration',
        false,
        `Service worker test failed: ${error}`
      );
    }
  }

  // Test Push Notifications
  private async testPushNotifications(): Promise<void> {
    try {
      const isSupported = pushNotificationService.isSupported();
      this.addResult(
        'Push Notification Support',
        isSupported,
        isSupported ? 'Push notifications are supported' : 'Push notifications not supported'
      );

      if (isSupported) {
        const permission = pushNotificationService.getPermissionStatus();
        this.addResult(
          'Push Notification Permission',
          permission !== 'denied',
          `Permission status: ${permission}`
        );

        // Test local notification
        try {
          if (permission === 'granted') {
            await pushNotificationService.showLocalNotification({
              title: 'PWA Test',
              body: 'Push notification test successful',
              tag: 'pwa-test',
              silent: true
            });
            this.addResult(
              'Local Notification',
              true,
              'Local notification displayed successfully'
            );
          }
        } catch (error) {
          this.addResult(
            'Local Notification',
            false,
            `Local notification failed: ${error}`
          );
        }
      }
    } catch (error) {
      this.addResult(
        'Push Notifications',
        false,
        `Push notification test failed: ${error}`
      );
    }
  }

  // Test Offline Sync
  private async testOfflineSync(): Promise<void> {
    try {
      // Test storing offline data
      await offlineSyncService.storeOfflineData('test-key', { test: 'data' }, 60000);
      const retrievedData = await offlineSyncService.getOfflineData('test-key');
      
      this.addResult(
        'Offline Data Storage',
        retrievedData?.test === 'data',
        retrievedData ? 'Offline data stored and retrieved successfully' : 'Failed to store/retrieve offline data'
      );

      // Test sync status
      const syncStatus = await offlineSyncService.getSyncStatus();
      this.addResult(
        'Sync Status',
        typeof syncStatus === 'object',
        `Sync status: ${syncStatus.pendingActions} pending actions, online: ${syncStatus.isOnline}`
      );

      // Clean up test data
      await offlineSyncService.deleteOfflineData('test-key');
    } catch (error) {
      this.addResult(
        'Offline Sync',
        false,
        `Offline sync test failed: ${error}`
      );
    }
  }

  // Test PWA Manifest
  private async testManifest(): Promise<void> {
    try {
      const manifestLink = document.querySelector('link[rel="manifest"]') as HTMLLinkElement;
      if (manifestLink) {
        const response = await fetch(manifestLink.href);
        const manifest = await response.json();
        
        this.addResult(
          'PWA Manifest',
          manifest.name && manifest.short_name,
          `Manifest loaded: ${manifest.name}`,
          { name: manifest.name, display: manifest.display, lang: manifest.lang }
        );
      } else {
        this.addResult(
          'PWA Manifest',
          false,
          'Manifest link not found in document'
        );
      }
    } catch (error) {
      this.addResult(
        'PWA Manifest',
        false,
        `Manifest test failed: ${error}`
      );
    }
  }

  // Test Mobile Features
  private async testMobileFeatures(): Promise<void> {
    const isMobile = window.innerWidth < 768;
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    
    this.addResult(
      'Mobile Detection',
      true,
      `Mobile: ${isMobile}, Touch: ${hasTouch}, Standalone: ${isStandalone}`,
      { isMobile, hasTouch, isStandalone, width: window.innerWidth }
    );

    // Test viewport meta tag
    const viewportMeta = document.querySelector('meta[name="viewport"]') as HTMLMetaElement;
    this.addResult(
      'Viewport Meta Tag',
      viewportMeta !== null,
      viewportMeta ? `Viewport: ${viewportMeta.content}` : 'Viewport meta tag not found'
    );

    // Test safe area support
    const rootStyle = getComputedStyle(document.documentElement);
    const safeAreaSupport = rootStyle.getPropertyValue('--safe-area-inset-top') !== '';
    this.addResult(
      'Safe Area Support',
      true,
      `Safe area insets ${safeAreaSupport ? 'detected' : 'not detected'}`
    );
  }

  // Test Hebrew RTL Support
  private async testHebrewRTL(): Promise<void> {
    const htmlElement = document.documentElement;
    const direction = htmlElement.dir || getComputedStyle(htmlElement).direction;
    
    this.addResult(
      'Hebrew RTL Support',
      direction === 'rtl',
      `Document direction: ${direction}`
    );

    // Test Hebrew font loading
    const computedStyle = getComputedStyle(document.body);
    const fontFamily = computedStyle.fontFamily;
    const hasHebrewFont = fontFamily.includes('Heebo') || fontFamily.includes('Hebrew');
    
    this.addResult(
      'Hebrew Font Loading',
      hasHebrewFont,
      `Font family: ${fontFamily}`
    );

    // Test Hebrew text rendering
    const testElement = document.createElement('div');
    testElement.textContent = 'בדיקה עברית';
    testElement.style.direction = 'rtl';
    testElement.style.visibility = 'hidden';
    testElement.style.position = 'absolute';
    document.body.appendChild(testElement);
    
    const textAlign = getComputedStyle(testElement).textAlign;
    document.body.removeChild(testElement);
    
    this.addResult(
      'Hebrew Text Alignment',
      textAlign === 'right' || textAlign === 'start',
      `Text alignment: ${textAlign}`
    );
  }

  // Test Network Status
  private async testNetworkStatus(): Promise<void> {
    const isOnline = navigator.onLine;
    this.addResult(
      'Network Status',
      true,
      `Network status: ${isOnline ? 'online' : 'offline'}`
    );

    // Test connection type if available
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      this.addResult(
        'Connection Type',
        true,
        `Connection: ${connection.effectiveType || 'unknown'}`,
        { type: connection.type, effectiveType: connection.effectiveType }
      );
    } else {
      this.addResult(
        'Connection Type',
        false,
        'Connection API not supported'
      );
    }
  }

  // Test Install Prompt
  private async testInstallPrompt(): Promise<void> {
    const isInstalled = window.matchMedia('(display-mode: standalone)').matches;
    
    this.addResult(
      'PWA Installation Status',
      true,
      isInstalled ? 'PWA is installed' : 'PWA not installed',
      { isInstalled }
    );

    // Test beforeinstallprompt event
    let installPromptAvailable = false;
    const testPrompt = (e: Event) => {
      installPromptAvailable = true;
    };
    
    window.addEventListener('beforeinstallprompt', testPrompt);
    
    // Wait briefly to see if event fires
    await new Promise(resolve => setTimeout(resolve, 100));
    
    window.removeEventListener('beforeinstallprompt', testPrompt);
    
    this.addResult(
      'Install Prompt Availability',
      installPromptAvailable || isInstalled,
      installPromptAvailable ? 'Install prompt is available' : 
       isInstalled ? 'Already installed' : 'Install prompt not available'
    );
  }

  // Generate test report
  generateReport(): string {
    const passed = this.results.filter(r => r.passed).length;
    const total = this.results.length;
    const percentage = Math.round((passed / total) * 100);
    
    let report = `PWA Test Report\n`;
    report += `================\n`;
    report += `Tests Passed: ${passed}/${total} (${percentage}%)\n\n`;
    
    this.results.forEach(result => {
      report += `${result.passed ? '✅' : '❌'} ${result.test}\n`;
      report += `   ${result.message}\n`;
      if (result.details) {
        report += `   Details: ${JSON.stringify(result.details, null, 2)}\n`;
      }
      report += `\n`;
    });
    
    return report;
  }

  // Test specific PWA features
  async testPWAFeature(feature: string): Promise<PWATestResult> {
    switch (feature) {
      case 'service-worker':
        await this.testServiceWorker();
        break;
      case 'push-notifications':
        await this.testPushNotifications();
        break;
      case 'offline-sync':
        await this.testOfflineSync();
        break;
      case 'manifest':
        await this.testManifest();
        break;
      case 'mobile':
        await this.testMobileFeatures();
        break;
      case 'hebrew-rtl':
        await this.testHebrewRTL();
        break;
      case 'network':
        await this.testNetworkStatus();
        break;
      case 'install':
        await this.testInstallPrompt();
        break;
      default:
        return {
          test: feature,
          passed: false,
          message: `Unknown test feature: ${feature}`
        };
    }
    
    return this.results[this.results.length - 1];
  }
}

// Global test runner
export const pwaTestSuite = new PWATestSuite();

// Console helper for manual testing
if (typeof window !== 'undefined') {
  (window as any).testPWA = async () => {
    const results = await pwaTestSuite.runAllTests();
    console.log('\n' + pwaTestSuite.generateReport());
    return results;
  };
}