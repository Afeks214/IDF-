# Hebrew Text Rendering & Font Optimization
## Comprehensive Strategy for Maximum Performance

### Overview
This document outlines advanced optimization techniques specifically designed for Hebrew text rendering, font loading, and RTL (Right-to-Left) text processing to ensure maximum performance and excellent user experience.

## 1. FONT LOADING OPTIMIZATION

### 1.1 Progressive Font Loading Strategy
```html
<!-- Critical font preloading -->
<link rel="preload" href="/fonts/hebrew-main.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/hebrew-bold.woff2" as="font" type="font/woff2" crossorigin>

<!-- Fallback font detection -->
<script>
  // Font loading detection and fallback
  class HebrewFontLoader {
    constructor() {
      this.loadedFonts = new Set();
      this.fallbackTimeout = 3000; // 3 seconds
      this.initFontLoading();
    }
    
    initFontLoading() {
      // Use CSS Font Loading API
      if ('fonts' in document) {
        this.loadWithFontAPI();
      } else {
        this.loadWithFallback();
      }
    }
    
    async loadWithFontAPI() {
      const fonts = [
        new FontFace('HebrewMain', 'url(/fonts/hebrew-main.woff2)', {
          display: 'swap',
          unicodeRange: 'U+0590-05FF, U+FB1D-FB4F'
        }),
        new FontFace('HebrewBold', 'url(/fonts/hebrew-bold.woff2)', {
          display: 'swap',
          weight: 'bold',
          unicodeRange: 'U+0590-05FF, U+FB1D-FB4F'
        })
      ];
      
      try {
        // Load fonts with timeout
        const loadPromises = fonts.map(font => 
          Promise.race([
            font.load(),
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Font load timeout')), this.fallbackTimeout)
            )
          ])
        );
        
        const loadedFonts = await Promise.allSettled(loadPromises);
        
        loadedFonts.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            document.fonts.add(result.value);
            this.loadedFonts.add(fonts[index].family);
          } else {
            console.warn(`Failed to load font: ${fonts[index].family}`);
            this.applyFallback(fonts[index].family);
          }
        });
        
        this.dispatchFontLoadEvent();
      } catch (error) {
        console.error('Font loading error:', error);
        this.applySystemFallbacks();
      }
    }
    
    applyFallback(fontFamily) {
      // Apply system font fallbacks for Hebrew
      const fallbackRules = `
        .hebrew-text {
          font-family: ${fontFamily}, 'Arial Hebrew', 'Times New Roman', 'Noto Sans Hebrew', Arial, sans-serif;
        }
      `;
      this.injectCSS(fallbackRules);
    }
    
    injectCSS(rules) {
      const style = document.createElement('style');
      style.textContent = rules;
      document.head.appendChild(style);
    }
    
    dispatchFontLoadEvent() {
      document.dispatchEvent(new CustomEvent('hebrewFontsLoaded', {
        detail: { loadedFonts: Array.from(this.loadedFonts) }
      }));
    }
  }
  
  // Initialize font loader
  new HebrewFontLoader();
</script>
```

### 1.2 Optimized Font CSS
```css
/* Hebrew font optimization with unicode-range */
@font-face {
  font-family: 'HebrewMain';
  src: url('/fonts/hebrew-main.woff2') format('woff2'),
       url('/fonts/hebrew-main.woff') format('woff'),
       url('/fonts/hebrew-main.ttf') format('truetype');
  font-display: swap;
  font-weight: normal;
  font-style: normal;
  unicode-range: U+0590-05FF, U+FB1D-FB4F, U+FB2A-FB4E;
}

@font-face {
  font-family: 'HebrewBold';
  src: url('/fonts/hebrew-bold.woff2') format('woff2'),
       url('/fonts/hebrew-bold.woff') format('woff');
  font-display: swap;
  font-weight: bold;
  unicode-range: U+0590-05FF, U+FB1D-FB4F;
}

/* Optimized Hebrew text class */
.hebrew-text {
  font-family: 'HebrewMain', 'Arial Hebrew', 'Times New Roman', Arial, sans-serif;
  direction: rtl;
  text-align: right;
  font-feature-settings: 'kern' 1, 'liga' 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.hebrew-bold {
  font-family: 'HebrewBold', 'Arial Hebrew', 'Times New Roman', Arial, sans-serif;
  font-weight: bold;
}

/* Performance-optimized text rendering */
.hebrew-text-optimized {
  contain: layout style;
  will-change: auto;
  transform: translateZ(0); /* Force GPU acceleration */
}

/* Responsive Hebrew text */
@media (max-width: 768px) {
  .hebrew-text {
    font-size: clamp(14px, 4vw, 18px);
    line-height: 1.6;
  }
}
```

### 1.3 Font Subsetting Strategy
```javascript
// Dynamic font subsetting for Hebrew characters
class HebrewFontSubsetter {
  constructor() {
    this.hebrewRanges = {
      basic: 'U+0590-05FF',        // Hebrew block
      extended: 'U+FB1D-FB4F',     // Hebrew presentation forms
      punctuation: 'U+05BE,U+05C0,U+05C3,U+05C6', // Hebrew punctuation
      yiddish: 'U+FB2A-FB4E'       // Yiddish digraphs
    };
    this.loadedSubsets = new Set();
  }
  
  async loadSubsetForText(text) {
    const requiredSubsets = this.analyzeTextRequirements(text);
    const unloadedSubsets = requiredSubsets.filter(subset => 
      !this.loadedSubsets.has(subset)
    );
    
    if (unloadedSubsets.length > 0) {
      await this.loadFontSubsets(unloadedSubsets);
    }
  }
  
  analyzeTextRequirements(text) {
    const codePoints = Array.from(text).map(char => char.codePointAt(0));
    const requiredSubsets = [];
    
    // Check which Hebrew ranges are needed
    if (codePoints.some(cp => cp >= 0x0590 && cp <= 0x05FF)) {
      requiredSubsets.push('basic');
    }
    if (codePoints.some(cp => cp >= 0xFB1D && cp <= 0xFB4F)) {
      requiredSubsets.push('extended');
    }
    
    return requiredSubsets;
  }
  
  async loadFontSubsets(subsets) {
    const loadPromises = subsets.map(subset => 
      this.loadSingleSubset(subset)
    );
    
    try {
      await Promise.all(loadPromises);
      subsets.forEach(subset => this.loadedSubsets.add(subset));
    } catch (error) {
      console.error('Font subset loading failed:', error);
    }
  }
  
  async loadSingleSubset(subset) {
    const fontFace = new FontFace(
      `HebrewMain-${subset}`,
      `url(/fonts/hebrew-main-${subset}.woff2)`,
      {
        unicodeRange: this.hebrewRanges[subset],
        display: 'swap'
      }
    );
    
    await fontFace.load();
    document.fonts.add(fontFace);
  }
}
```

## 2. RTL TEXT PROCESSING OPTIMIZATION

### 2.1 Efficient RTL Detection and Processing
```javascript
// High-performance Hebrew/RTL text processor
class HebrewTextProcessor {
  constructor() {
    this.rtlCache = new Map();
    this.hebrewRegex = /[\u0590-\u05FF\u200F\u200E\uFB1D-\uFB4F]/;
    this.strongRTL = /[\u0590-\u05FF\uFB1D-\uFB4F]/;
    this.observer = null;
    this.initMutationObserver();
  }
  
  initMutationObserver() {
    // Automatically process dynamically added Hebrew text
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
              this.processTextNode(node);
            } else if (node.nodeType === Node.ELEMENT_NODE) {
              this.processElement(node);
            }
          });
        }
      });
    });
    
    this.observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
  
  processTextNode(textNode) {
    const text = textNode.textContent;
    if (this.containsHebrew(text)) {
      const processed = this.optimizeHebrewText(text);
      if (processed !== text) {
        const span = document.createElement('span');
        span.className = 'hebrew-text-auto';
        span.innerHTML = processed;
        textNode.parentNode.replaceChild(span, textNode);
      }
    }
  }
  
  processElement(element) {
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );
    
    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
      if (this.containsHebrew(node.textContent)) {
        textNodes.push(node);
      }
    }
    
    textNodes.forEach(textNode => this.processTextNode(textNode));
  }
  
  containsHebrew(text) {
    return this.hebrewRegex.test(text);
  }
  
  optimizeHebrewText(text) {
    // Check cache first
    if (this.rtlCache.has(text)) {
      return this.rtlCache.get(text);
    }
    
    const processed = this.processRTLText(text);
    
    // Cache result (limit cache size)
    if (this.rtlCache.size >= 1000) {
      const firstKey = this.rtlCache.keys().next().value;
      this.rtlCache.delete(firstKey);
    }
    this.rtlCache.set(text, processed);
    
    return processed;
  }
  
  processRTLText(text) {
    // Split text into segments (Hebrew vs non-Hebrew)
    const segments = this.segmentText(text);
    
    return segments.map(segment => {
      if (segment.isHebrew) {
        return `<span dir="rtl" class="hebrew-segment">${segment.text}</span>`;
      } else {
        return `<span dir="ltr" class="latin-segment">${segment.text}</span>`;
      }
    }).join('');
  }
  
  segmentText(text) {
    const segments = [];
    let currentSegment = '';
    let isCurrentHebrew = false;
    
    for (const char of text) {
      const isHebrew = this.strongRTL.test(char);
      
      if (currentSegment === '' || isHebrew === isCurrentHebrew) {
        currentSegment += char;
        isCurrentHebrew = isHebrew;
      } else {
        segments.push({
          text: currentSegment,
          isHebrew: isCurrentHebrew
        });
        currentSegment = char;
        isCurrentHebrew = isHebrew;
      }
    }
    
    if (currentSegment) {
      segments.push({
        text: currentSegment,
        isHebrew: isCurrentHebrew
      });
    }
    
    return segments;
  }
  
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}

// Initialize Hebrew text processor
const hebrewProcessor = new HebrewTextProcessor();
```

### 2.2 Bidirectional Text Algorithm Optimization
```javascript
// Optimized bidirectional text handling
class BidiTextOptimizer {
  constructor() {
    this.bidiCache = new WeakMap();
    this.rtlMarker = '\u200F'; // Right-to-left mark
    this.ltrMarker = '\u200E'; // Left-to-right mark
  }
  
  optimizeBidiText(element) {
    // Check if already processed
    if (this.bidiCache.has(element)) {
      return this.bidiCache.get(element);
    }
    
    const originalText = element.textContent;
    const optimizedText = this.processBidiText(originalText);
    
    if (optimizedText !== originalText) {
      element.innerHTML = optimizedText;
      element.classList.add('bidi-optimized');
    }
    
    this.bidiCache.set(element, true);
    return true;
  }
  
  processBidiText(text) {
    // Handle mixed Hebrew-English text
    return text.replace(
      /([a-zA-Z0-9\s]+)([\u0590-\u05FF]+)/g,
      (match, latin, hebrew) => {
        return `${latin}${this.rtlMarker}${hebrew}${this.ltrMarker}`;
      }
    ).replace(
      /([\u0590-\u05FF]+)([a-zA-Z0-9\s]+)/g,
      (match, hebrew, latin) => {
        return `${this.rtlMarker}${hebrew}${this.ltrMarker}${latin}`;
      }
    );
  }
  
  // Batch process multiple elements
  batchOptimize(elements) {
    const fragment = document.createDocumentFragment();
    const processedElements = [];
    
    elements.forEach(element => {
      const clone = element.cloneNode(true);
      this.optimizeBidiText(clone);
      processedElements.push({ original: element, optimized: clone });
    });
    
    // Replace all elements at once
    processedElements.forEach(({ original, optimized }) => {
      original.parentNode.replaceChild(optimized, original);
    });
  }
}
```

## 3. VIRTUALIZED HEBREW TEXT RENDERING

### 3.1 Virtual Scrolling for Hebrew Lists
```javascript
// High-performance virtual scrolling for Hebrew content
class HebrewVirtualList {
  constructor(container, options = {}) {
    this.container = container;
    this.itemHeight = options.itemHeight || 50;
    this.bufferSize = options.bufferSize || 5;
    this.data = [];
    this.visibleStart = 0;
    this.visibleEnd = 0;
    this.scrollTop = 0;
    
    this.viewport = this.createViewport();
    this.content = this.createContent();
    
    this.setupEventListeners();
    this.hebrewProcessor = new HebrewTextProcessor();
  }
  
  createViewport() {
    const viewport = document.createElement('div');
    viewport.className = 'virtual-list-viewport';
    viewport.style.cssText = `
      height: 100%;
      overflow-y: auto;
      position: relative;
    `;
    this.container.appendChild(viewport);
    return viewport;
  }
  
  createContent() {
    const content = document.createElement('div');
    content.className = 'virtual-list-content';
    content.style.cssText = `
      position: relative;
      will-change: transform;
    `;
    this.viewport.appendChild(content);
    return content;
  }
  
  setupEventListeners() {
    this.viewport.addEventListener('scroll', (e) => {
      this.scrollTop = e.target.scrollTop;
      this.updateVisibleRange();
      this.renderVisibleItems();
    });
  }
  
  setData(data) {
    this.data = data;
    this.content.style.height = `${data.length * this.itemHeight}px`;
    this.updateVisibleRange();
    this.renderVisibleItems();
  }
  
  updateVisibleRange() {
    const containerHeight = this.viewport.clientHeight;
    const visibleStart = Math.floor(this.scrollTop / this.itemHeight);
    const visibleEnd = Math.min(
      visibleStart + Math.ceil(containerHeight / this.itemHeight),
      this.data.length
    );
    
    this.visibleStart = Math.max(0, visibleStart - this.bufferSize);
    this.visibleEnd = Math.min(this.data.length, visibleEnd + this.bufferSize);
  }
  
  renderVisibleItems() {
    // Clear existing items
    this.content.innerHTML = '';
    
    // Create document fragment for batch DOM manipulation
    const fragment = document.createDocumentFragment();
    
    for (let i = this.visibleStart; i < this.visibleEnd; i++) {
      const item = this.createItemElement(this.data[i], i);
      fragment.appendChild(item);
    }
    
    this.content.appendChild(fragment);
  }
  
  createItemElement(data, index) {
    const item = document.createElement('div');
    item.className = 'virtual-list-item';
    item.style.cssText = `
      position: absolute;
      top: ${index * this.itemHeight}px;
      height: ${this.itemHeight}px;
      width: 100%;
      display: flex;
      align-items: center;
      padding: 0 15px;
      box-sizing: border-box;
    `;
    
    // Process Hebrew content
    const content = this.hebrewProcessor.optimizeHebrewText(data.text || data);
    item.innerHTML = content;
    
    // Add Hebrew text class if contains Hebrew
    if (this.hebrewProcessor.containsHebrew(data.text || data)) {
      item.classList.add('hebrew-text');
    }
    
    return item;
  }
  
  scrollToIndex(index) {
    const targetScrollTop = index * this.itemHeight;
    this.viewport.scrollTop = targetScrollTop;
  }
  
  destroy() {
    this.hebrewProcessor.destroy();
    this.viewport.removeEventListener('scroll', this.handleScroll);
  }
}
```

### 3.2 Optimized Hebrew Table Rendering
```javascript
// Virtual table for Hebrew data with optimized rendering
class HebrewVirtualTable {
  constructor(container, columns, options = {}) {
    this.container = container;
    this.columns = columns;
    this.rowHeight = options.rowHeight || 40;
    this.headerHeight = options.headerHeight || 50;
    this.data = [];
    
    this.table = this.createTable();
    this.header = this.createHeader();
    this.body = this.createBody();
    
    this.setupEventListeners();
    this.hebrewProcessor = new HebrewTextProcessor();
  }
  
  createTable() {
    const table = document.createElement('div');
    table.className = 'hebrew-virtual-table';
    table.style.cssText = `
      height: 100%;
      display: flex;
      flex-direction: column;
      direction: rtl;
      font-family: 'HebrewMain', Arial, sans-serif;
    `;
    this.container.appendChild(table);
    return table;
  }
  
  createHeader() {
    const header = document.createElement('div');
    header.className = 'table-header';
    header.style.cssText = `
      height: ${this.headerHeight}px;
      display: flex;
      background: #f5f5f5;
      border-bottom: 1px solid #ddd;
      position: sticky;
      top: 0;
      z-index: 10;
    `;
    
    this.columns.forEach((column, index) => {
      const headerCell = document.createElement('div');
      headerCell.className = 'header-cell';
      headerCell.style.cssText = `
        flex: ${column.width || 1};
        padding: 10px;
        font-weight: bold;
        text-align: ${column.align || 'right'};
        display: flex;
        align-items: center;
        justify-content: ${column.align === 'center' ? 'center' : 'flex-end'};
      `;
      headerCell.textContent = column.title;
      header.appendChild(headerCell);
    });
    
    this.table.appendChild(header);
    return header;
  }
  
  createBody() {
    const body = document.createElement('div');
    body.className = 'table-body';
    body.style.cssText = `
      flex: 1;
      overflow-y: auto;
      position: relative;
    `;
    
    this.table.appendChild(body);
    return body;
  }
  
  setData(data) {
    this.data = data;
    this.renderVisibleRows();
  }
  
  renderVisibleRows() {
    // Clear existing rows
    this.body.innerHTML = '';
    
    const fragment = document.createDocumentFragment();
    
    this.data.forEach((rowData, rowIndex) => {
      const row = this.createRow(rowData, rowIndex);
      fragment.appendChild(row);
    });
    
    this.body.appendChild(fragment);
  }
  
  createRow(rowData, rowIndex) {
    const row = document.createElement('div');
    row.className = 'table-row';
    row.style.cssText = `
      display: flex;
      height: ${this.rowHeight}px;
      border-bottom: 1px solid #eee;
      background: ${rowIndex % 2 === 0 ? '#fff' : '#f9f9f9'};
    `;
    
    this.columns.forEach((column, colIndex) => {
      const cell = this.createCell(rowData[column.key], column, rowIndex, colIndex);
      row.appendChild(cell);
    });
    
    return row;
  }
  
  createCell(cellData, column, rowIndex, colIndex) {
    const cell = document.createElement('div');
    cell.className = 'table-cell';
    cell.style.cssText = `
      flex: ${column.width || 1};
      padding: 10px;
      text-align: ${column.align || 'right'};
      display: flex;
      align-items: center;
      justify-content: ${column.align === 'center' ? 'center' : 'flex-end'};
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    `;
    
    // Process Hebrew content
    let content = cellData;
    if (typeof cellData === 'string' && this.hebrewProcessor.containsHebrew(cellData)) {
      content = this.hebrewProcessor.optimizeHebrewText(cellData);
      cell.classList.add('hebrew-cell');
    }
    
    // Apply column formatter if available
    if (column.formatter) {
      content = column.formatter(content, rowIndex, colIndex);
    }
    
    cell.innerHTML = content;
    return cell;
  }
}
```

## 4. HEBREW SEARCH OPTIMIZATION

### 4.1 Hebrew Text Indexing
```javascript
// Optimized Hebrew search with indexing
class HebrewSearchIndex {
  constructor() {
    this.index = new Map();
    this.wordIndex = new Map();
    this.hebrewNormalizer = new HebrewNormalizer();
    this.searchCache = new Map();
  }
  
  addDocument(id, text) {
    const normalizedText = this.hebrewNormalizer.normalize(text);
    const words = this.extractWords(normalizedText);
    
    // Add to main index
    this.index.set(id, {
      originalText: text,
      normalizedText: normalizedText,
      words: words
    });
    
    // Add to word index
    words.forEach(word => {
      if (!this.wordIndex.has(word)) {
        this.wordIndex.set(word, new Set());
      }
      this.wordIndex.get(word).add(id);
    });
  }
  
  search(query, options = {}) {
    const cacheKey = `${query}:${JSON.stringify(options)}`;
    
    if (this.searchCache.has(cacheKey)) {
      return this.searchCache.get(cacheKey);
    }
    
    const normalizedQuery = this.hebrewNormalizer.normalize(query);
    const queryWords = this.extractWords(normalizedQuery);
    
    let results = new Set();
    
    if (options.exact) {
      results = this.exactSearch(normalizedQuery);
    } else if (options.fuzzy) {
      results = this.fuzzySearch(queryWords, options.threshold || 0.8);
    } else {
      results = this.wordSearch(queryWords, options.matchAll || false);
    }
    
    const finalResults = Array.from(results).map(id => ({
      id: id,
      document: this.index.get(id),
      relevance: this.calculateRelevance(id, queryWords)
    })).sort((a, b) => b.relevance - a.relevance);
    
    // Cache results
    this.searchCache.set(cacheKey, finalResults);
    
    return finalResults;
  }
  
  extractWords(text) {
    // Hebrew word extraction with proper boundaries
    return text.match(/[\u0590-\u05FF]+/g) || [];
  }
  
  exactSearch(query) {
    const results = new Set();
    
    for (const [id, doc] of this.index) {
      if (doc.normalizedText.includes(query)) {
        results.add(id);
      }
    }
    
    return results;
  }
  
  wordSearch(words, matchAll) {
    if (words.length === 0) return new Set();
    
    let results = new Set();
    
    if (matchAll) {
      // Find documents containing ALL words
      results = this.wordIndex.get(words[0]) || new Set();
      
      for (let i = 1; i < words.length; i++) {
        const wordResults = this.wordIndex.get(words[i]) || new Set();
        results = new Set([...results].filter(id => wordResults.has(id)));
      }
    } else {
      // Find documents containing ANY word
      words.forEach(word => {
        const wordResults = this.wordIndex.get(word) || new Set();
        wordResults.forEach(id => results.add(id));
      });
    }
    
    return results;
  }
  
  calculateRelevance(documentId, queryWords) {
    const doc = this.index.get(documentId);
    if (!doc) return 0;
    
    let score = 0;
    const docWords = doc.words;
    
    queryWords.forEach(queryWord => {
      const wordCount = docWords.filter(word => word === queryWord).length;
      score += wordCount / docWords.length;
    });
    
    return score / queryWords.length;
  }
}

// Hebrew text normalizer for consistent searching
class HebrewNormalizer {
  constructor() {
    // Hebrew normalization mappings
    this.mappings = new Map([
      ['ך', 'כ'], ['ם', 'מ'], ['ן', 'נ'], ['ף', 'פ'], ['ץ', 'צ'], // Final forms
      ['ו', 'ו'], ['י', 'י']  // Consistent vav/yud
    ]);
    
    // Remove diacritics (niqqud)
    this.diacritics = /[\u0591-\u05BD\u05BF\u05C1-\u05C2\u05C4-\u05C5\u05C7]/g;
  }
  
  normalize(text) {
    // Remove diacritics
    let normalized = text.replace(this.diacritics, '');
    
    // Apply character mappings
    for (const [from, to] of this.mappings) {
      normalized = normalized.replace(new RegExp(from, 'g'), to);
    }
    
    // Convert to lowercase equivalent and trim
    return normalized.trim();
  }
}
```

## 5. PERFORMANCE MONITORING

### 5.1 Hebrew Text Rendering Metrics
```javascript
// Performance monitoring for Hebrew text rendering
class HebrewRenderingMetrics {
  constructor() {
    this.metrics = {
      fontLoadTime: 0,
      textRenderTime: 0,
      bidiProcessingTime: 0,
      cacheHitRate: 0,
      memoryUsage: 0
    };
    
    this.observers = [];
    this.initializeObservers();
  }
  
  initializeObservers() {
    // Font loading performance
    document.addEventListener('hebrewFontsLoaded', (event) => {
      this.metrics.fontLoadTime = performance.now() - this.startTime;
      this.reportMetrics('fontLoad', this.metrics.fontLoadTime);
    });
    
    // Text rendering performance observer
    if ('PerformanceObserver' in window) {
      const renderObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          if (entry.name.includes('hebrew-render')) {
            this.metrics.textRenderTime = entry.duration;
          }
        });
      });
      
      renderObserver.observe({ entryTypes: ['measure'] });
      this.observers.push(renderObserver);
    }
    
    // Memory usage monitoring
    setInterval(() => {
      if (performance.memory) {
        this.metrics.memoryUsage = performance.memory.usedJSHeapSize;
        this.checkMemoryThreshold();
      }
    }, 5000);
  }
  
  measureTextRendering(operation, label = 'hebrew-render') {
    const startMark = `${label}-start`;
    const endMark = `${label}-end`;
    
    performance.mark(startMark);
    
    const result = operation();
    
    performance.mark(endMark);
    performance.measure(label, startMark, endMark);
    
    return result;
  }
  
  measureBidiProcessing(text, processor) {
    const start = performance.now();
    const result = processor.processBidiText(text);
    const duration = performance.now() - start;
    
    this.metrics.bidiProcessingTime += duration;
    return result;
  }
  
  updateCacheHitRate(hits, total) {
    this.metrics.cacheHitRate = total > 0 ? hits / total : 0;
  }
  
  checkMemoryThreshold() {
    const threshold = 50 * 1024 * 1024; // 50MB
    if (this.metrics.memoryUsage > threshold) {
      this.reportAlert('high-memory-usage', {
        current: this.metrics.memoryUsage,
        threshold: threshold
      });
    }
  }
  
  reportMetrics(type, data) {
    // Send metrics to analytics
    if (typeof gtag !== 'undefined') {
      gtag('event', 'hebrew_performance', {
        metric_type: type,
        value: data,
        custom_map: this.metrics
      });
    }
  }
  
  reportAlert(type, data) {
    console.warn(`Hebrew rendering alert: ${type}`, data);
    
    // Could also send to monitoring service
    fetch('/api/metrics/alert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, data, timestamp: Date.now() })
    }).catch(err => console.error('Failed to report alert:', err));
  }
  
  getPerformanceReport() {
    return {
      metrics: { ...this.metrics },
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      recommendations: this.generateRecommendations()
    };
  }
  
  generateRecommendations() {
    const recommendations = [];
    
    if (this.metrics.fontLoadTime > 3000) {
      recommendations.push('Consider font preloading or subsetting');
    }
    
    if (this.metrics.textRenderTime > 100) {
      recommendations.push('Enable text rendering optimization');
    }
    
    if (this.metrics.cacheHitRate < 0.8) {
      recommendations.push('Increase cache size or TTL');
    }
    
    if (this.metrics.memoryUsage > 30 * 1024 * 1024) {
      recommendations.push('Consider reducing cache size or enabling compression');
    }
    
    return recommendations;
  }
  
  destroy() {
    this.observers.forEach(observer => observer.disconnect());
  }
}

// Initialize performance monitoring
const hebrewMetrics = new HebrewRenderingMetrics();
```

## 6. IMPLEMENTATION CHECKLIST

### Phase 1: Font Optimization (Week 1)
- [ ] Implement progressive font loading
- [ ] Set up font subsetting
- [ ] Configure font caching
- [ ] Add fallback mechanisms

### Phase 2: Text Processing (Week 2)
- [ ] Implement RTL text processor
- [ ] Add bidirectional text optimization
- [ ] Set up Hebrew text cache
- [ ] Configure mutation observer

### Phase 3: Advanced Features (Week 3)
- [ ] Implement virtual scrolling
- [ ] Add Hebrew search indexing
- [ ] Set up performance monitoring
- [ ] Optimize rendering pipeline

### Success Metrics
- **Font Load Time**: < 2 seconds
- **Text Render Time**: < 50ms per 1000 characters
- **Cache Hit Rate**: > 90%
- **Memory Usage**: < 30MB for text processing
- **Search Response**: < 100ms for Hebrew queries

This comprehensive Hebrew text optimization strategy ensures maximum performance while maintaining excellent readability and user experience for RTL text processing.