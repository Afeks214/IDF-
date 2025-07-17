/**
 * IDF Testing Infrastructure - Frontend Performance Monitor
 * Real-time performance monitoring and optimization for Hebrew applications
 */

class PerformanceMonitor {
  constructor() {
    this.metrics = {
      pageLoadTime: 0,
      firstContentfulPaint: 0,
      largestContentfulPaint: 0,
      firstInputDelay: 0,
      cumulativeLayoutShift: 0,
      timeToInteractive: 0,
      hebrewRenderTime: 0,
      memoryUsage: 0,
      bundleSize: 0
    };

    this.observers = new Map();
    this.hebrewMetrics = {
      rtlProcessingTime: [],
      fontLoadTime: 0,
      textRenderingTime: []
    };

    this.isMonitoring = false;
    this.reportingEndpoint = '/api/v1/metrics/frontend';
    
    this.initializeMonitoring();
  }

  initializeMonitoring() {
    if (typeof window === 'undefined') return;

    this.isMonitoring = true;
    
    // Initialize performance observers
    this.initWebVitals();
    this.initMemoryMonitoring();
    this.initHebrewPerformanceMonitoring();
    this.initBundleAnalysis();
    
    // Listen for page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.reportMetrics();
      }
    });

    // Report metrics before page unload
    window.addEventListener('beforeunload', () => {
      this.reportMetrics(true);
    });

    console.log('IDF Performance Monitor initialized');
  }

  initWebVitals() {
    // First Contentful Paint
    this.observePerformanceEntry('paint', (entries) => {
      const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
      if (fcpEntry) {
        this.metrics.firstContentfulPaint = fcpEntry.startTime;
      }
    });

    // Largest Contentful Paint
    this.observePerformanceEntry('largest-contentful-paint', (entries) => {
      const latestEntry = entries[entries.length - 1];
      if (latestEntry) {
        this.metrics.largestContentfulPaint = latestEntry.startTime;
      }
    });

    // First Input Delay
    this.observePerformanceEntry('first-input', (entries) => {
      const firstInput = entries[0];
      if (firstInput) {
        this.metrics.firstInputDelay = firstInput.processingStart - firstInput.startTime;
      }
    });

    // Cumulative Layout Shift
    this.observePerformanceEntry('layout-shift', (entries) => {
      let clsValue = 0;
      entries.forEach(entry => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      });
      this.metrics.cumulativeLayoutShift = clsValue;
    });

    // Page Load Time
    window.addEventListener('load', () => {
      const navigation = performance.getEntriesByType('navigation')[0];
      this.metrics.pageLoadTime = navigation.loadEventEnd - navigation.fetchStart;
      
      // Calculate Time to Interactive (simplified)
      this.calculateTimeToInteractive();
    });
  }

  initMemoryMonitoring() {
    if ('memory' in performance) {
      setInterval(() => {
        this.metrics.memoryUsage = performance.memory.usedJSHeapSize;
      }, 5000);
    }
  }

  initHebrewPerformanceMonitoring() {
    // Monitor Hebrew font loading
    if ('fonts' in document) {
      const hebrewFonts = ['Assistant', 'Rubik', 'Secular One']; // Common Hebrew fonts
      
      Promise.all(
        hebrewFonts.map(font => document.fonts.load(`16px ${font}`))
      ).then(() => {
        this.hebrewMetrics.fontLoadTime = performance.now();
      }).catch(err => {
        console.warn('Hebrew font loading error:', err);
      });
    }

    // Monitor RTL text processing
    this.monitorRTLProcessing();
  }

  initBundleAnalysis() {
    // Estimate bundle size from loaded resources
    window.addEventListener('load', () => {
      const resources = performance.getEntriesByType('resource');
      let totalSize = 0;
      
      resources.forEach(resource => {
        if (resource.transferSize) {
          totalSize += resource.transferSize;
        }
      });
      
      this.metrics.bundleSize = totalSize;
    });
  }

  observePerformanceEntry(entryType, callback) {
    try {
      const observer = new PerformanceObserver((list) => {
        callback(list.getEntries());
      });
      
      observer.observe({ entryTypes: [entryType] });
      this.observers.set(entryType, observer);
    } catch (error) {
      console.warn(`Performance observer for ${entryType} not supported:`, error);
    }
  }

  calculateTimeToInteractive() {
    // Simplified TTI calculation
    const navigation = performance.getEntriesByType('navigation')[0];
    const resources = performance.getEntriesByType('resource');
    
    let lastResourceTime = 0;
    resources.forEach(resource => {
      if (resource.responseEnd > lastResourceTime) {
        lastResourceTime = resource.responseEnd;
      }
    });
    
    this.metrics.timeToInteractive = Math.max(
      navigation.domContentLoadedEventEnd,
      lastResourceTime
    );
  }

  monitorRTLProcessing() {
    // Create a performance mark for RTL processing
    const originalTextContent = Object.getOwnPropertyDescriptor(
      Node.prototype, 
      'textContent'
    );
    
    if (originalTextContent) {
      Object.defineProperty(Node.prototype, 'textContent', {
        get: originalTextContent.get,
        set: function(value) {
          if (typeof value === 'string' && this.dir === 'rtl') {
            const startTime = performance.now();
            originalTextContent.set.call(this, value);
            const endTime = performance.now();
            
            window.performanceMonitor?.recordHebrewProcessing(endTime - startTime);
          } else {
            originalTextContent.set.call(this, value);
          }
        }
      });
    }
  }

  recordHebrewProcessing(duration) {
    this.hebrewMetrics.rtlProcessingTime.push(duration);
    
    // Keep only last 100 measurements
    if (this.hebrewMetrics.rtlProcessingTime.length > 100) {
      this.hebrewMetrics.rtlProcessingTime = this.hebrewMetrics.rtlProcessingTime.slice(-100);
    }
  }

  measureComponentRender(componentName, renderFunction) {
    const startTime = performance.now();
    
    return Promise.resolve(renderFunction()).then(result => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      this.recordComponentMetric(componentName, duration);
      return result;
    });
  }

  recordComponentMetric(componentName, duration) {
    if (!this.componentMetrics) {
      this.componentMetrics = {};
    }
    
    if (!this.componentMetrics[componentName]) {
      this.componentMetrics[componentName] = [];
    }
    
    this.componentMetrics[componentName].push(duration);
    
    // Keep only last 50 measurements per component
    if (this.componentMetrics[componentName].length > 50) {
      this.componentMetrics[componentName] = this.componentMetrics[componentName].slice(-50);
    }
  }

  measureAsyncOperation(operationName, asyncFunction) {
    const startTime = performance.now();
    
    return Promise.resolve(asyncFunction()).then(result => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      this.recordAsyncMetric(operationName, duration);
      return result;
    }).catch(error => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      this.recordAsyncMetric(operationName, duration, true);
      throw error;
    });
  }

  recordAsyncMetric(operationName, duration, isError = false) {
    if (!this.asyncMetrics) {
      this.asyncMetrics = {};
    }
    
    if (!this.asyncMetrics[operationName]) {
      this.asyncMetrics[operationName] = {
        durations: [],
        errors: 0,
        total: 0
      };
    }
    
    this.asyncMetrics[operationName].durations.push(duration);
    this.asyncMetrics[operationName].total++;
    
    if (isError) {
      this.asyncMetrics[operationName].errors++;
    }
    
    // Keep only last 100 measurements
    if (this.asyncMetrics[operationName].durations.length > 100) {
      this.asyncMetrics[operationName].durations = 
        this.asyncMetrics[operationName].durations.slice(-100);
    }
  }

  getMetricsSummary() {
    const summary = {
      coreWebVitals: {
        fcp: this.metrics.firstContentfulPaint,
        lcp: this.metrics.largestContentfulPaint,
        fid: this.metrics.firstInputDelay,
        cls: this.metrics.cumulativeLayoutShift,
        tti: this.metrics.timeToInteractive
      },
      performance: {
        pageLoadTime: this.metrics.pageLoadTime,
        memoryUsage: this.metrics.memoryUsage,
        bundleSize: this.metrics.bundleSize
      },
      hebrew: {
        fontLoadTime: this.hebrewMetrics.fontLoadTime,
        avgRtlProcessing: this.calculateAverage(this.hebrewMetrics.rtlProcessingTime),
        rtlOperations: this.hebrewMetrics.rtlProcessingTime.length
      }
    };

    // Add component metrics if available
    if (this.componentMetrics) {
      summary.components = {};
      Object.keys(this.componentMetrics).forEach(component => {
        summary.components[component] = {
          avgRenderTime: this.calculateAverage(this.componentMetrics[component]),
          renders: this.componentMetrics[component].length
        };
      });
    }

    // Add async operation metrics if available
    if (this.asyncMetrics) {
      summary.asyncOperations = {};
      Object.keys(this.asyncMetrics).forEach(operation => {
        const metrics = this.asyncMetrics[operation];
        summary.asyncOperations[operation] = {
          avgDuration: this.calculateAverage(metrics.durations),
          errorRate: metrics.errors / metrics.total,
          totalOperations: metrics.total
        };
      });
    }

    return summary;
  }

  calculateAverage(array) {
    if (!array || array.length === 0) return 0;
    return array.reduce((sum, value) => sum + value, 0) / array.length;
  }

  reportMetrics(isBeforeUnload = false) {
    if (!this.isMonitoring) return;

    const metricsData = {
      ...this.getMetricsSummary(),
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      connection: this.getConnectionInfo()
    };

    // Send metrics to backend
    if (isBeforeUnload) {
      // Use sendBeacon for immediate sending before page unload
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          this.reportingEndpoint,
          JSON.stringify(metricsData)
        );
      }
    } else {
      // Use fetch for regular reporting
      fetch(this.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(metricsData)
      }).catch(error => {
        console.warn('Failed to send performance metrics:', error);
      });
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('Performance Metrics:', metricsData);
    }
  }

  getConnectionInfo() {
    if ('connection' in navigator) {
      const conn = navigator.connection;
      return {
        effectiveType: conn.effectiveType,
        downlink: conn.downlink,
        rtt: conn.rtt,
        saveData: conn.saveData
      };
    }
    return null;
  }

  // Performance optimization suggestions
  getOptimizationSuggestions() {
    const suggestions = [];
    const summary = this.getMetricsSummary();

    // Check Core Web Vitals
    if (summary.coreWebVitals.lcp > 2500) {
      suggestions.push({
        type: 'performance',
        severity: 'high',
        message: 'Largest Contentful Paint is slow. Consider optimizing images and critical resources.'
      });
    }

    if (summary.coreWebVitals.fid > 100) {
      suggestions.push({
        type: 'performance',
        severity: 'medium',
        message: 'First Input Delay is high. Consider reducing JavaScript execution time.'
      });
    }

    if (summary.coreWebVitals.cls > 0.1) {
      suggestions.push({
        type: 'performance',
        severity: 'medium',
        message: 'Cumulative Layout Shift is high. Ensure elements have defined dimensions.'
      });
    }

    // Check bundle size
    if (summary.performance.bundleSize > 1000000) { // 1MB
      suggestions.push({
        type: 'bundle',
        severity: 'medium',
        message: 'Bundle size is large. Consider code splitting and tree shaking.'
      });
    }

    // Check Hebrew processing
    if (summary.hebrew.avgRtlProcessing > 10) {
      suggestions.push({
        type: 'hebrew',
        severity: 'low',
        message: 'RTL text processing is slow. Consider caching processed text.'
      });
    }

    return suggestions;
  }

  destroy() {
    this.isMonitoring = false;
    
    // Disconnect all observers
    this.observers.forEach(observer => {
      observer.disconnect();
    });
    
    this.observers.clear();
  }
}

// Create global instance
if (typeof window !== 'undefined') {
  window.performanceMonitor = new PerformanceMonitor();
}

export default PerformanceMonitor;