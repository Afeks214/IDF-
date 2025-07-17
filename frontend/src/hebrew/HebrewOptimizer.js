/**
 * IDF Testing Infrastructure - Hebrew Text Optimizer
 * High-performance Hebrew text processing and RTL optimization
 */

class HebrewOptimizer {
  constructor() {
    this.cache = new Map();
    this.maxCacheSize = 10000;
    this.metrics = {
      cacheHits: 0,
      cacheMisses: 0,
      processingTime: []
    };
    
    // Hebrew character ranges
    this.hebrewRanges = [
      [0x0590, 0x05FF], // Hebrew
      [0xFB1D, 0xFB4F], // Hebrew Presentation Forms
      [0x200F, 0x200F], // Right-to-Left Mark
      [0x202E, 0x202E]  // Right-to-Left Override
    ];
    
    this.rtlCache = new Map();
    this.fontLoadPromise = this.loadHebrewFonts();
    
    console.log('Hebrew Optimizer initialized');
  }

  async loadHebrewFonts() {
    if (typeof document === 'undefined') return;

    const hebrewFonts = [
      'Assistant',
      'Rubik', 
      'Secular One',
      'Heebo',
      'Alef'
    ];

    const fontLoadPromises = hebrewFonts.map(font => {
      return document.fonts.load(`16px ${font}`).catch(() => {
        console.warn(`Failed to load Hebrew font: ${font}`);
      });
    });

    try {
      await Promise.allSettled(fontLoadPromises);
      console.log('Hebrew fonts loaded');
    } catch (error) {
      console.warn('Error loading Hebrew fonts:', error);
    }
  }

  isHebrew(text) {
    if (!text || typeof text !== 'string') return false;
    
    return Array.from(text).some(char => {
      const codePoint = char.codePointAt(0);
      return this.hebrewRanges.some(([start, end]) => 
        codePoint >= start && codePoint <= end
      );
    });
  }

  normalizeHebrewText(text) {
    if (!text || typeof text !== 'string') return text;

    const cacheKey = `normalize:${text}`;
    if (this.cache.has(cacheKey)) {
      this.metrics.cacheHits++;
      return this.cache.get(cacheKey);
    }

    this.metrics.cacheMisses++;
    const startTime = performance.now();

    let normalized = text;

    // Unicode normalization for Hebrew
    normalized = normalized.normalize('NFKC');

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ').trim();

    // Handle mixed RTL/LTR content
    normalized = this.normalizeMixedContent(normalized);

    const processingTime = performance.now() - startTime;
    this.metrics.processingTime.push(processingTime);

    // Cache the result
    this.setCacheValue(cacheKey, normalized);

    return normalized;
  }

  normalizeMixedContent(text) {
    // Handle mixed Hebrew and English content
    const segments = this.segmentText(text);
    
    return segments.map(segment => {
      if (segment.isHebrew) {
        return this.processHebrewSegment(segment.text);
      } else {
        return segment.text;
      }
    }).join('');
  }

  segmentText(text) {
    const segments = [];
    let currentSegment = '';
    let isCurrentHebrew = false;

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      const isCharHebrew = this.isHebrew(char);

      if (currentSegment === '') {
        // Start new segment
        currentSegment = char;
        isCurrentHebrew = isCharHebrew;
      } else if (isCharHebrew === isCurrentHebrew) {
        // Continue current segment
        currentSegment += char;
      } else {
        // Segment change
        segments.push({
          text: currentSegment,
          isHebrew: isCurrentHebrew
        });
        currentSegment = char;
        isCurrentHebrew = isCharHebrew;
      }
    }

    // Add final segment
    if (currentSegment) {
      segments.push({
        text: currentSegment,
        isHebrew: isCurrentHebrew
      });
    }

    return segments;
  }

  processHebrewSegment(text) {
    // Specific Hebrew text processing
    let processed = text;

    // Handle common Hebrew punctuation
    processed = processed.replace(/([א-ת])([.!?])/g, '$2$1');
    
    // Handle number formatting in Hebrew context
    processed = this.formatHebrewNumbers(processed);

    return processed;
  }

  formatHebrewNumbers(text) {
    // Format numbers within Hebrew text for better readability
    return text.replace(/(\d+)/g, (match) => {
      // Add proper spacing around numbers in Hebrew context
      return ` ${match} `;
    }).replace(/\s+/g, ' ').trim();
  }

  generateRTLWrapper(text, options = {}) {
    const {
      className = 'rtl-text',
      inline = false,
      forceDirection = false
    } = options;

    if (!this.isHebrew(text) && !forceDirection) {
      return text;
    }

    const cacheKey = `rtl:${text}:${JSON.stringify(options)}`;
    if (this.rtlCache.has(cacheKey)) {
      this.metrics.cacheHits++;
      return this.rtlCache.get(cacheKey);
    }

    this.metrics.cacheMisses++;

    const normalizedText = this.normalizeHebrewText(text);
    const tag = inline ? 'span' : 'div';
    
    const wrapper = `<${tag} dir="rtl" class="${className}" lang="he">${normalizedText}</${tag}>`;
    
    this.setRTLCacheValue(cacheKey, wrapper);
    
    return wrapper;
  }

  createOptimizedElement(text, options = {}) {
    if (typeof document === 'undefined') return null;

    const {
      tagName = 'div',
      className = 'hebrew-text',
      attributes = {}
    } = options;

    const element = document.createElement(tagName);
    
    // Set Hebrew-specific attributes
    if (this.isHebrew(text)) {
      element.dir = 'rtl';
      element.lang = 'he';
    }
    
    element.className = className;
    element.textContent = this.normalizeHebrewText(text);

    // Apply additional attributes
    Object.keys(attributes).forEach(key => {
      element.setAttribute(key, attributes[key]);
    });

    return element;
  }

  optimizeInputField(inputElement, options = {}) {
    if (!inputElement || typeof document === 'undefined') return;

    const {
      autoDetect = true,
      forceRTL = false
    } = options;

    const updateDirection = () => {
      const value = inputElement.value;
      
      if (forceRTL || (autoDetect && this.isHebrew(value))) {
        inputElement.dir = 'rtl';
        inputElement.style.textAlign = 'right';
      } else {
        inputElement.dir = 'ltr';
        inputElement.style.textAlign = 'left';
      }
    };

    // Set initial direction
    updateDirection();

    // Listen for input changes
    inputElement.addEventListener('input', updateDirection);
    inputElement.addEventListener('paste', () => {
      setTimeout(updateDirection, 0);
    });

    return () => {
      inputElement.removeEventListener('input', updateDirection);
    };
  }

  formatHebrewDate(date, format = 'full') {
    if (typeof Intl === 'undefined') return date.toString();

    const options = {
      'short': { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      },
      'long': { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
      },
      'full': {
        year: 'numeric',
        month: 'long', 
        day: 'numeric',
        weekday: 'long',
        hour: '2-digit',
        minute: '2-digit'
      }
    };

    try {
      return new Intl.DateTimeFormat('he-IL', options[format] || options.full)
        .format(new Date(date));
    } catch (error) {
      console.warn('Hebrew date formatting error:', error);
      return date.toString();
    }
  }

  formatHebrewNumber(number, style = 'decimal') {
    if (typeof Intl === 'undefined') return number.toString();

    const options = {
      'decimal': { style: 'decimal' },
      'currency': { style: 'currency', currency: 'ILS' },
      'percent': { style: 'percent' }
    };

    try {
      return new Intl.NumberFormat('he-IL', options[style] || options.decimal)
        .format(number);
    } catch (error) {
      console.warn('Hebrew number formatting error:', error);
      return number.toString();
    }
  }

  searchHebrewText(text, query, options = {}) {
    const {
      caseSensitive = false,
      normalizeSearch = true,
      highlightMatches = false
    } = options;

    if (!text || !query) return [];

    const searchText = normalizeSearch ? this.normalizeHebrewText(text) : text;
    const searchQuery = normalizeSearch ? this.normalizeHebrewText(query) : query;

    const flags = caseSensitive ? 'g' : 'gi';
    const regex = new RegExp(searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags);
    
    const matches = [];
    let match;

    while ((match = regex.exec(searchText)) !== null) {
      matches.push({
        index: match.index,
        length: match[0].length,
        text: match[0],
        highlighted: highlightMatches ? this.highlightMatch(text, match.index, match[0].length) : null
      });
    }

    return matches;
  }

  highlightMatch(text, index, length) {
    const before = text.substring(0, index);
    const match = text.substring(index, index + length);
    const after = text.substring(index + length);

    return `${before}<mark class="hebrew-highlight">${match}</mark>${after}`;
  }

  setCacheValue(key, value) {
    if (this.cache.size >= this.maxCacheSize) {
      // Remove oldest entries (simple LRU)
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  setRTLCacheValue(key, value) {
    if (this.rtlCache.size >= this.maxCacheSize / 2) {
      const firstKey = this.rtlCache.keys().next().value;
      this.rtlCache.delete(firstKey);
    }
    this.rtlCache.set(key, value);
  }

  clearCache() {
    this.cache.clear();
    this.rtlCache.clear();
  }

  getPerformanceMetrics() {
    const totalRequests = this.metrics.cacheHits + this.metrics.cacheMisses;
    const hitRate = totalRequests > 0 ? this.metrics.cacheHits / totalRequests : 0;
    const avgProcessingTime = this.metrics.processingTime.length > 0 
      ? this.metrics.processingTime.reduce((a, b) => a + b, 0) / this.metrics.processingTime.length 
      : 0;

    return {
      cacheHitRate: hitRate,
      totalRequests,
      avgProcessingTime,
      cacheSize: this.cache.size,
      rtlCacheSize: this.rtlCache.size
    };
  }

  // React Hook for Hebrew optimization
  useHebrewOptimization() {
    if (typeof React === 'undefined') return {};

    const [isReady, setIsReady] = React.useState(false);

    React.useEffect(() => {
      this.fontLoadPromise.then(() => {
        setIsReady(true);
      });
    }, []);

    return {
      isReady,
      normalizeText: this.normalizeHebrewText.bind(this),
      isHebrew: this.isHebrew.bind(this),
      formatDate: this.formatHebrewDate.bind(this),
      formatNumber: this.formatHebrewNumber.bind(this),
      searchText: this.searchHebrewText.bind(this),
      optimizeInput: this.optimizeInputField.bind(this)
    };
  }
}

// Create global instance
const hebrewOptimizer = new HebrewOptimizer();

// Export for ES modules
export default hebrewOptimizer;

// Global access
if (typeof window !== 'undefined') {
  window.hebrewOptimizer = hebrewOptimizer;
}