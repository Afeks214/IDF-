/**
 * Hebrew Text Processing and Validation Utilities
 * Supports RTL text, Unicode normalization, and Hebrew-specific validations
 */

// Hebrew Unicode ranges
const HEBREW_BLOCK = /[\u0590-\u05FF]/;
const HEBREW_LETTERS = /[\u05D0-\u05EA]/;
const HEBREW_POINTS = /[\u05B0-\u05BD\u05BF-\u05C2\u05C4-\u05C5\u05C7]/;
const HEBREW_PUNCTUATION = /[\u05BE\u05C0\u05C3\u05C6\u05F3-\u05F4]/;

export class HebrewTextProcessor {
  /**
   * Check if text contains Hebrew characters
   */
  static containsHebrew(text: string): boolean {
    return HEBREW_BLOCK.test(text);
  }

  /**
   * Check if text is primarily Hebrew
   */
  static isHebrewText(text: string, threshold = 0.3): boolean {
    const hebrewChars = (text.match(HEBREW_LETTERS) || []).length;
    const totalChars = text.replace(/\s/g, '').length;
    return totalChars > 0 && (hebrewChars / totalChars) >= threshold;
  }

  /**
   * Normalize Hebrew text (remove points, standardize format)
   */
  static normalizeHebrew(text: string): string {
    return text
      .normalize('NFD') // Decompose combined characters
      .replace(HEBREW_POINTS, '') // Remove Hebrew points/vowels
      .replace(/\u05F0/g, '\u05D5\u05D5') // Replace װ with וו
      .replace(/\u05F1/g, '\u05D5\u05D9') // Replace ױ with וי
      .replace(/\u05F2/g, '\u05D9\u05D9') // Replace ײ with יי
      .trim();
  }

  /**
   * Clean Hebrew text for search (normalize + remove special chars)
   */
  static cleanForSearch(text: string): string {
    return this.normalizeHebrew(text)
      .replace(/[^\u05D0-\u05EA\s\d]/g, '') // Keep only Hebrew letters, spaces, and digits
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim()
      .toLowerCase();
  }

  /**
   * Validate Hebrew name (person or place)
   */
  static validateHebrewName(name: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!name || name.trim().length === 0) {
      errors.push('השם לא יכול להיות רק');
    }

    if (name.length > 100) {
      errors.push('השם לא יכול להיות יותר מ-100 תווים');
    }

    if (name.length < 2) {
      errors.push('השם חייב להיות לפחות 2 תווים');
    }

    // Check for Hebrew content
    if (!this.containsHebrew(name)) {
      errors.push('השם חייב לכלול אותיות עבריות');
    }

    // Check for invalid characters
    const invalidChars = /[<>'"&{}()]/g;
    if (invalidChars.test(name)) {
      errors.push('השם מכיל תווים לא חוקיים');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Validate military ID (Hebrew context)
   */
  static validateMilitaryId(id: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!id || id.trim().length === 0) {
      errors.push('מספר אישי נדרש');
    }

    // Israeli military ID is typically 7-8 digits
    const cleanId = id.replace(/\D/g, '');
    if (cleanId.length < 6 || cleanId.length > 9) {
      errors.push('מספר אישי חייב להיות 6-9 ספרות');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Format Hebrew text for display (ensure proper RTL)
   */
  static formatForDisplay(text: string): string {
    if (!this.containsHebrew(text)) {
      return text;
    }

    // Add RTL marker for mixed content
    return `\u202D${text}\u202C`;
  }

  /**
   * Extract Hebrew words from mixed text
   */
  static extractHebrewWords(text: string): string[] {
    const words = text.split(/\s+/);
    return words.filter(word => this.containsHebrew(word));
  }

  /**
   * Generate search variations for Hebrew text
   */
  static generateSearchVariations(text: string): string[] {
    const normalized = this.normalizeHebrew(text);
    const cleaned = this.cleanForSearch(text);
    
    const variations = [
      text,
      normalized,
      cleaned,
      text.replace(/["']/g, ''), // Remove quotes
      text.replace(/\s+/g, ''), // Remove spaces
    ];

    // Add partial matches (useful for autocomplete)
    const words = cleaned.split(' ');
    if (words.length > 1) {
      variations.push(...words);
    }

    return [...new Set(variations)].filter(v => v.length > 0);
  }

  /**
   * Check text direction (RTL/LTR)
   */
  static getTextDirection(text: string): 'rtl' | 'ltr' | 'mixed' {
    const hebrewChars = (text.match(HEBREW_LETTERS) || []).length;
    const latinChars = (text.match(/[a-zA-Z]/) || []).length;
    
    if (hebrewChars > latinChars) return 'rtl';
    if (latinChars > hebrewChars) return 'ltr';
    return 'mixed';
  }

  /**
   * Sort Hebrew text array properly
   */
  static sortHebrewArray(arr: string[]): string[] {
    return arr.sort((a, b) => {
      const normalizedA = this.normalizeHebrew(a);
      const normalizedB = this.normalizeHebrew(b);
      return normalizedA.localeCompare(normalizedB, 'he');
    });
  }

  /**
   * Hebrew-aware text truncation
   */
  static truncateHebrew(text: string, maxLength: number, suffix = '...'): string {
    if (text.length <= maxLength) return text;
    
    // Try to break at word boundary
    const truncated = text.substring(0, maxLength - suffix.length);
    const lastSpace = truncated.lastIndexOf(' ');
    
    if (lastSpace > maxLength * 0.7) {
      return truncated.substring(0, lastSpace) + suffix;
    }
    
    return truncated + suffix;
  }

  /**
   * Convert Hebrew numerals to digits
   */
  static hebrewNumeralsToDigits(text: string): string {
    const hebrewNumerals: Record<string, string> = {
      'א': '1', 'ב': '2', 'ג': '3', 'ד': '4', 'ה': '5',
      'ו': '6', 'ז': '7', 'ח': '8', 'ט': '9', 'י': '10',
      'כ': '20', 'ל': '30', 'מ': '40', 'נ': '50',
      'ס': '60', 'ע': '70', 'פ': '80', 'צ': '90',
      'ק': '100', 'ר': '200', 'ש': '300', 'ת': '400'
    };

    let result = text;
    for (const [hebrew, digit] of Object.entries(hebrewNumerals)) {
      result = result.replace(new RegExp(hebrew, 'g'), digit);
    }
    
    return result;
  }
}

export default HebrewTextProcessor;