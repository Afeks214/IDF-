/**
 * IDF Testing Infrastructure - Hebrew Testing Utilities
 * Comprehensive testing utilities for Hebrew/RTL functionality
 */

// Hebrew test data constants
export const HEBREW_TEST_DATA = {
  simple: 'שלום עולם',
  withNumbers: 'בדיקה 123 מספרים',
  withPunctuation: 'שלום, עולם! איך הולך?',
  mixed: 'Hello שלום World עולם',
  rtlMarks: '‏שלום‏ ‏עולם‏',
  longText: 'זהו טקסט ארוך בעברית לבדיקת ביצועים ועיבוד נכון של טקסט עברי. הטקסט כולל מילים רבות ומשפטים מורכבים כדי לוודא שהמערכת מטפלת נכון בעברית בכל המצבים האפשריים.',
  technicalTerms: [
    'מערכת תקשורת',
    'בדיקת רדיו VHF',
    'הצפנת מידע',
    'רשת תקשובת',
    'מערכת ניווט GPS',
    'אבטחת מידע',
    'פרוטוקול TCP/IP',
    'תדר UHF'
  ],
  statusValues: {
    active: 'פעיל',
    pending: 'ממתין',
    completed: 'הושלם',
    failed: 'נכשל',
    cancelled: 'מבוטל'
  }
};

// Unicode ranges for Hebrew characters
const HEBREW_RANGES = [
  [0x0590, 0x05FF], // Hebrew
  [0xFB1D, 0xFB4F], // Hebrew Presentation Forms
  [0x200F, 0x200F], // Right-to-Left Mark
  [0x202E, 0x202E]  // Right-to-Left Override
];

/**
 * Hebrew Text Processing Utilities
 */
export class HebrewTextUtils {
  /**
   * Check if a character is Hebrew
   */
  static isHebrewChar(char) {
    if (!char || typeof char !== 'string') return false;
    
    const codePoint = char.codePointAt(0);
    return HEBREW_RANGES.some(([start, end]) => 
      codePoint >= start && codePoint <= end
    );
  }

  /**
   * Check if text contains Hebrew characters
   */
  static isHebrewText(text) {
    if (!text || typeof text !== 'string') return false;
    
    return Array.from(text).some(char => this.isHebrewChar(char));
  }

  /**
   * Detect text direction (rtl/ltr/mixed)
   */
  static detectTextDirection(text) {
    if (!text) return 'ltr';

    const hebrewChars = Array.from(text).filter(char => this.isHebrewChar(char)).length;
    const latinChars = Array.from(text).filter(char => 
      char.match(/[a-zA-Z]/) !== null
    ).length;

    if (hebrewChars > latinChars) return 'rtl';
    if (latinChars > hebrewChars) return 'ltr';
    return 'mixed';
  }

  /**
   * Normalize Hebrew text for consistent processing
   */
  static normalizeHebrewText(text) {
    if (!text || typeof text !== 'string') return text;

    // Unicode normalization
    let normalized = text.normalize('NFKC');

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ').trim();

    return normalized;
  }

  /**
   * Extract Hebrew words from mixed content
   */
  static extractHebrewWords(text) {
    if (!text) return [];

    const words = [];
    let currentWord = '';

    for (const char of text) {
      if (this.isHebrewChar(char) || /\s/.test(char)) {
        if (/\s/.test(char) && currentWord) {
          if (Array.from(currentWord).some(c => this.isHebrewChar(c))) {
            words.push(currentWord.trim());
          }
          currentWord = '';
        } else if (!/\s/.test(char)) {
          currentWord += char;
        }
      }
    }

    // Add final word
    if (currentWord && Array.from(currentWord).some(c => this.isHebrewChar(c))) {
      words.push(currentWord.trim());
    }

    return words;
  }

  /**
   * Format Hebrew date using Intl API
   */
  static formatHebrewDate(date, format = 'full') {
    const options = {
      short: { year: 'numeric', month: 'short', day: 'numeric' },
      long: { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' },
      full: {
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
      return new Date(date).toString();
    }
  }

  /**
   * Format Hebrew numbers using Intl API
   */
  static formatHebrewNumber(number, style = 'decimal') {
    const options = {
      decimal: { style: 'decimal' },
      currency: { style: 'currency', currency: 'ILS' },
      percent: { style: 'percent' }
    };

    try {
      return new Intl.NumberFormat('he-IL', options[style] || options.decimal)
        .format(number);
    } catch (error) {
      console.warn('Hebrew number formatting error:', error);
      return number.toString();
    }
  }
}

/**
 * DOM Testing Utilities for Hebrew/RTL
 */
export class HebrewDOMUtils {
  /**
   * Check if element has correct RTL attributes
   */
  static hasCorrectRTLAttributes(element) {
    if (!element) return false;

    const textContent = element.textContent || '';
    const isHebrew = HebrewTextUtils.isHebrewText(textContent);

    if (isHebrew) {
      return element.dir === 'rtl' || 
             getComputedStyle(element).direction === 'rtl';
    }

    return true; // Non-Hebrew text doesn't require RTL
  }

  /**
   * Validate Hebrew font loading
   */
  static async validateHebrewFontLoading() {
    if (!document.fonts) {
      console.warn('Font loading API not supported');
      return false;
    }

    const hebrewFonts = ['Assistant', 'Rubik', 'Secular One', 'Heebo'];
    const loadPromises = hebrewFonts.map(font => 
      document.fonts.load(`16px ${font}`).catch(() => false)
    );

    const results = await Promise.allSettled(loadPromises);
    const loadedFonts = results.filter(result => 
      result.status === 'fulfilled' && result.value !== false
    ).length;

    return loadedFonts > 0;
  }

  /**
   * Measure text rendering performance
   */
  static measureTextRenderingPerformance(text, iterations = 100) {
    const testElement = document.createElement('div');
    testElement.style.position = 'absolute';
    testElement.style.left = '-9999px';
    testElement.style.fontSize = '16px';
    document.body.appendChild(testElement);

    const startTime = performance.now();

    for (let i = 0; i < iterations; i++) {
      testElement.textContent = text;
      testElement.offsetWidth; // Force reflow
    }

    const endTime = performance.now();
    document.body.removeChild(testElement);

    return endTime - startTime;
  }

  /**
   * Test input field RTL behavior
   */
  static testInputRTLBehavior(inputElement, testText) {
    if (!inputElement) return false;

    const originalValue = inputElement.value;
    const originalDir = inputElement.dir;

    try {
      // Set test text
      inputElement.value = testText;
      inputElement.dispatchEvent(new Event('input', { bubbles: true }));

      // Check if direction was set correctly
      const isHebrew = HebrewTextUtils.isHebrewText(testText);
      const hasCorrectDirection = isHebrew ? 
        (inputElement.dir === 'rtl' || getComputedStyle(inputElement).direction === 'rtl') :
        (inputElement.dir === 'ltr' || getComputedStyle(inputElement).direction === 'ltr');

      return hasCorrectDirection;
    } finally {
      // Restore original state
      inputElement.value = originalValue;
      inputElement.dir = originalDir;
    }
  }

  /**
   * Validate table RTL layout
   */
  static validateTableRTLLayout(tableElement) {
    if (!tableElement || tableElement.tagName !== 'TABLE') return false;

    const hasHebrewContent = Array.from(tableElement.querySelectorAll('td, th'))
      .some(cell => HebrewTextUtils.isHebrewText(cell.textContent));

    if (hasHebrewContent) {
      const computedStyle = getComputedStyle(tableElement);
      return computedStyle.direction === 'rtl';
    }

    return true; // Non-Hebrew tables don't require RTL
  }
}

/**
 * Test Data Generators for Hebrew Content
 */
export class HebrewTestDataGenerator {
  /**
   * Generate test data with Hebrew content
   */
  static generateTestData(count = 10) {
    const data = [];
    const { technicalTerms, statusValues } = HEBREW_TEST_DATA;
    const statusKeys = Object.keys(statusValues);

    for (let i = 0; i < count; i++) {
      data.push({
        id: i + 1,
        name: `${technicalTerms[i % technicalTerms.length]} ${i + 1}`,
        status: statusKeys[i % statusKeys.length],
        statusHebrew: statusValues[statusKeys[i % statusKeys.length]],
        description: `תיאור לבדיקה מספר ${i + 1}`,
        date: new Date(2024, 0, (i % 28) + 1).toISOString(),
        priority: ['high', 'medium', 'low'][i % 3],
        category: technicalTerms[i % technicalTerms.length].split(' ')[0]
      });
    }

    return data;
  }

  /**
   * Generate mixed RTL/LTR content
   */
  static generateMixedContent(count = 5) {
    const mixedTexts = [
      'Testing בדיקה System מערכת',
      'Radio רדיו Communication תקשורת',
      'Security אבטחה Protocol פרוטוקול',
      'Network רשת Infrastructure תשתית',
      'Data מידע Processing עיבוד'
    ];

    return Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      text: mixedTexts[i % mixedTexts.length],
      type: 'mixed',
      direction: HebrewTextUtils.detectTextDirection(mixedTexts[i % mixedTexts.length])
    }));
  }

  /**
   * Generate form validation test cases
   */
  static generateFormTestCases() {
    return [
      {
        name: 'hebrew_only',
        value: HEBREW_TEST_DATA.simple,
        expectedDirection: 'rtl',
        shouldValidate: true
      },
      {
        name: 'english_only',
        value: 'Hello World',
        expectedDirection: 'ltr',
        shouldValidate: true
      },
      {
        name: 'mixed_content',
        value: HEBREW_TEST_DATA.mixed,
        expectedDirection: 'mixed',
        shouldValidate: true
      },
      {
        name: 'hebrew_with_numbers',
        value: HEBREW_TEST_DATA.withNumbers,
        expectedDirection: 'rtl',
        shouldValidate: true
      },
      {
        name: 'empty_string',
        value: '',
        expectedDirection: 'ltr',
        shouldValidate: false
      },
      {
        name: 'whitespace_only',
        value: '   ',
        expectedDirection: 'ltr',
        shouldValidate: false
      }
    ];
  }
}

/**
 * Performance Testing Utilities
 */
export class HebrewPerformanceUtils {
  /**
   * Benchmark Hebrew text processing
   */
  static benchmarkTextProcessing(text, iterations = 1000) {
    const operations = [
      () => HebrewTextUtils.isHebrewText(text),
      () => HebrewTextUtils.detectTextDirection(text),
      () => HebrewTextUtils.normalizeHebrewText(text),
      () => HebrewTextUtils.extractHebrewWords(text)
    ];

    const results = {};

    operations.forEach((operation, index) => {
      const operationNames = ['isHebrewText', 'detectDirection', 'normalize', 'extractWords'];
      const startTime = performance.now();

      for (let i = 0; i < iterations; i++) {
        operation();
      }

      const endTime = performance.now();
      results[operationNames[index]] = {
        totalTime: endTime - startTime,
        averageTime: (endTime - startTime) / iterations,
        iterations
      };
    });

    return results;
  }

  /**
   * Test memory usage during Hebrew processing
   */
  static testMemoryUsage(callback) {
    if (!performance.memory) {
      console.warn('Performance memory API not available');
      return null;
    }

    const initialMemory = performance.memory.usedJSHeapSize;
    callback();
    const finalMemory = performance.memory.usedJSHeapSize;

    return {
      initial: initialMemory,
      final: finalMemory,
      delta: finalMemory - initialMemory
    };
  }
}

/**
 * Accessibility Testing for Hebrew Content
 */
export class HebrewA11yUtils {
  /**
   * Check if Hebrew content has proper accessibility attributes
   */
  static validateHebrewAccessibility(element) {
    const issues = [];

    // Check for proper lang attribute
    if (HebrewTextUtils.isHebrewText(element.textContent)) {
      if (!element.lang && !element.closest('[lang]')) {
        issues.push('Missing lang attribute for Hebrew content');
      }

      // Check for proper direction
      if (!this.hasCorrectDirection(element)) {
        issues.push('Incorrect text direction for Hebrew content');
      }

      // Check for aria-label if content is not descriptive
      if (element.textContent.length < 3 && !element.getAttribute('aria-label')) {
        issues.push('Short Hebrew content missing aria-label');
      }
    }

    return {
      isAccessible: issues.length === 0,
      issues
    };
  }

  /**
   * Check if element has correct direction
   */
  static hasCorrectDirection(element) {
    const isHebrew = HebrewTextUtils.isHebrewText(element.textContent);
    if (!isHebrew) return true;

    const style = getComputedStyle(element);
    return style.direction === 'rtl' || element.dir === 'rtl';
  }

  /**
   * Generate accessibility test report for Hebrew content
   */
  static generateA11yReport(container) {
    const elements = container.querySelectorAll('*');
    const results = {
      totalElements: elements.length,
      hebrewElements: 0,
      accessibleElements: 0,
      issues: []
    };

    elements.forEach((element, index) => {
      if (HebrewTextUtils.isHebrewText(element.textContent)) {
        results.hebrewElements++;
        
        const validation = this.validateHebrewAccessibility(element);
        if (validation.isAccessible) {
          results.accessibleElements++;
        } else {
          results.issues.push({
            element: element.tagName,
            index,
            issues: validation.issues
          });
        }
      }
    });

    results.accessibilityRate = results.hebrewElements > 0 ? 
      (results.accessibleElements / results.hebrewElements) * 100 : 100;

    return results;
  }
}

/**
 * Test Suite Runner for Hebrew Functionality
 */
export class HebrewTestRunner {
  constructor() {
    this.results = {
      passed: 0,
      failed: 0,
      total: 0,
      details: []
    };
  }

  /**
   * Run a comprehensive Hebrew test suite
   */
  async runComprehensiveTests(container) {
    console.log('Starting comprehensive Hebrew tests...');

    const tests = [
      () => this.testTextDetection(),
      () => this.testDirectionDetection(),
      () => this.testNormalization(),
      () => this.testFontLoading(),
      () => this.testDOMElements(container),
      () => this.testPerformance(),
      () => this.testAccessibility(container)
    ];

    for (const test of tests) {
      try {
        await test();
        this.results.passed++;
      } catch (error) {
        this.results.failed++;
        this.results.details.push({
          test: test.name,
          error: error.message
        });
      }
      this.results.total++;
    }

    return this.results;
  }

  testTextDetection() {
    const tests = [
      [HEBREW_TEST_DATA.simple, true],
      [HEBREW_TEST_DATA.mixed, true],
      ['Hello World', false],
      ['', false]
    ];

    tests.forEach(([text, expected]) => {
      const result = HebrewTextUtils.isHebrewText(text);
      if (result !== expected) {
        throw new Error(`Text detection failed for "${text}"`);
      }
    });
  }

  testDirectionDetection() {
    const tests = [
      [HEBREW_TEST_DATA.simple, 'rtl'],
      ['Hello World', 'ltr'],
      [HEBREW_TEST_DATA.mixed, 'mixed']
    ];

    tests.forEach(([text, expected]) => {
      const result = HebrewTextUtils.detectTextDirection(text);
      if (result !== expected) {
        throw new Error(`Direction detection failed for "${text}"`);
      }
    });
  }

  testNormalization() {
    const result = HebrewTextUtils.normalizeHebrewText(HEBREW_TEST_DATA.simple);
    if (!result || typeof result !== 'string') {
      throw new Error('Normalization failed');
    }
  }

  async testFontLoading() {
    const result = await HebrewDOMUtils.validateHebrewFontLoading();
    if (!result) {
      throw new Error('Hebrew font loading validation failed');
    }
  }

  testDOMElements(container) {
    if (!container) return;

    const hebrewElements = Array.from(container.querySelectorAll('*'))
      .filter(el => HebrewTextUtils.isHebrewText(el.textContent));

    hebrewElements.forEach(element => {
      if (!HebrewDOMUtils.hasCorrectRTLAttributes(element)) {
        throw new Error(`Element missing RTL attributes: ${element.tagName}`);
      }
    });
  }

  testPerformance() {
    const benchmark = HebrewPerformanceUtils.benchmarkTextProcessing(
      HEBREW_TEST_DATA.longText, 
      100
    );

    // Check if operations complete within reasonable time
    Object.values(benchmark).forEach(result => {
      if (result.averageTime > 1) { // 1ms per operation threshold
        throw new Error(`Performance test failed: ${result.averageTime}ms average`);
      }
    });
  }

  testAccessibility(container) {
    if (!container) return;

    const report = HebrewA11yUtils.generateA11yReport(container);
    if (report.accessibilityRate < 80) { // 80% threshold
      throw new Error(`Accessibility rate too low: ${report.accessibilityRate}%`);
    }
  }
}

export default {
  HebrewTextUtils,
  HebrewDOMUtils,
  HebrewTestDataGenerator,
  HebrewPerformanceUtils,
  HebrewA11yUtils,
  HebrewTestRunner,
  HEBREW_TEST_DATA
};