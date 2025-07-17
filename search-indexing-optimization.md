# Efficient Search Indexing for Hebrew Content
## Advanced Search Architecture for Maximum Performance

### Overview
This document outlines a comprehensive search indexing strategy specifically optimized for Hebrew content, providing lightning-fast search capabilities while handling the complexities of Hebrew text processing, morphology, and bidirectional text.

## 1. SEARCH ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH FRONTEND                         │
├─────────────────────────────────────────────────────────────┤
│  Search UI  │  Auto-complete  │  Results Display          │
│  (Hebrew)   │  (Real-time)    │  (Highlighted)            │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   SEARCH ENGINE                            │
├─────────────────────────────────────────────────────────────┤
│  Query Parser │  Hebrew Analyzer │  Result Ranker         │
│  (Morphology) │  (Normalization) │  (Relevance)           │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   SEARCH INDEXES                           │
├─────────────────────────────────────────────────────────────┤
│  Inverted     │  N-gram        │  Phonetic               │
│  Index        │  Index         │  Index                  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  Document     │  Metadata      │  Cache Layer            │
│  Store        │  Store         │  (Redis)                │
└─────────────────────────────────────────────────────────────┘
```

## 2. HEBREW TEXT PREPROCESSING

### 2.1 Hebrew Text Analyzer
```python
import re
import unicodedata
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class HebrewToken:
    text: str
    normalized: str
    root: str = None
    morphology: Dict = None
    position: int = 0

class HebrewTextAnalyzer:
    def __init__(self):
        # Hebrew character ranges
        self.hebrew_letters = re.compile(r'[\u0590-\u05FF]+')
        self.niqqud = re.compile(r'[\u0591-\u05BD\u05BF\u05C1-\u05C2\u05C4-\u05C5\u05C7]')
        
        # Final form mappings
        self.final_forms = {
            'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'
        }
        
        # Common Hebrew prefixes and suffixes
        self.prefixes = {'ב', 'ל', 'מ', 'ש', 'ה', 'ו', 'כ'}
        self.suffixes = {'ים', 'ות', 'ה', 'י', 'ך', 'נו', 'כם', 'הן'}
        
        # Hebrew stop words
        self.stop_words = {
            'את', 'של', 'על', 'אל', 'זה', 'זו', 'זאת', 'הוא', 'היא', 'הם', 'הן',
            'אני', 'אתה', 'אתם', 'אתן', 'אנחנו', 'כל', 'כמו', 'לא', 'או', 'גם',
            'רק', 'עם', 'בין', 'תחת', 'אחרי', 'לפני', 'אם', 'כי', 'מה', 'איך'
        }
    
    def analyze_text(self, text: str) -> List[HebrewToken]:
        """Analyze Hebrew text and return tokenized representation"""
        # Remove diacritics (niqqud)
        clean_text = self.niqqud.sub('', text)
        
        # Extract Hebrew words
        words = self.hebrew_letters.findall(clean_text)
        
        tokens = []
        position = 0
        
        for word in words:
            if len(word) < 2:  # Skip single characters
                continue
                
            normalized = self.normalize_word(word)
            
            if normalized not in self.stop_words:
                token = HebrewToken(
                    text=word,
                    normalized=normalized,
                    root=self.extract_root(normalized),
                    morphology=self.analyze_morphology(normalized),
                    position=position
                )
                tokens.append(token)
            
            position += 1
        
        return tokens
    
    def normalize_word(self, word: str) -> str:
        """Normalize Hebrew word for consistent indexing"""
        # Convert final forms to regular forms
        normalized = ''.join(self.final_forms.get(char, char) for char in word)
        
        # Remove common prefixes
        for prefix in self.prefixes:
            if normalized.startswith(prefix) and len(normalized) > 3:
                # Check if removing prefix leaves a valid word
                without_prefix = normalized[1:]
                if len(without_prefix) >= 2:
                    normalized = without_prefix
                break
        
        # Remove common suffixes
        for suffix in sorted(self.suffixes, key=len, reverse=True):
            if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized.lower()
    
    def extract_root(self, word: str) -> str:
        """Extract Hebrew root (simplified implementation)"""
        if len(word) < 3:
            return word
        
        # Simple 3-letter root extraction
        # In a real implementation, this would use sophisticated morphological analysis
        if len(word) == 3:
            return word
        elif len(word) == 4:
            # Try removing common patterns
            patterns = ['מ', 'ת', 'ה', 'נ']
            for pattern in patterns:
                if word.startswith(pattern):
                    return word[1:]
                if word.endswith(pattern):
                    return word[:-1]
        
        # Default to first 3 letters for longer words
        return word[:3]
    
    def analyze_morphology(self, word: str) -> Dict:
        """Analyze morphological features of Hebrew word"""
        morphology = {
            'length': len(word),
            'has_prefix': any(word.startswith(p) for p in self.prefixes),
            'has_suffix': any(word.endswith(s) for s in self.suffixes),
            'pattern': self.get_pattern(word)
        }
        return morphology
    
    def get_pattern(self, word: str) -> str:
        """Get consonant pattern of Hebrew word"""
        # Simplified pattern extraction
        consonants = []
        vowels = {'א', 'ה', 'ו', 'י', 'ע'}
        
        for char in word:
            if char in vowels:
                consonants.append('V')
            else:
                consonants.append('C')
        
        return ''.join(consonants)
```

### 2.2 Search Index Builder
```python
import json
import sqlite3
import pickle
from collections import defaultdict
from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

class HebrewSearchIndex:
    def __init__(self, db_path: str = "hebrew_search.db"):
        self.db_path = db_path
        self.analyzer = HebrewTextAnalyzer()
        self.inverted_index = defaultdict(set)
        self.document_store = {}
        self.tfidf_vectorizer = None
        self.document_vectors = None
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for persistent storage"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                vector BLOB,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS word_index (
                word TEXT,
                document_id TEXT,
                positions TEXT,
                tf_score REAL,
                PRIMARY KEY (word, document_id)
            )
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_word ON word_index(word);
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_doc_id ON word_index(document_id);
        ''')
        
        self.conn.commit()
    
    def add_document(self, doc_id: str, content: str, metadata: Dict = None):
        """Add document to search index"""
        tokens = self.analyzer.analyze_text(content)
        
        # Store document
        metadata_json = json.dumps(metadata or {})
        
        # Build word frequency and positions
        word_freq = defaultdict(int)
        word_positions = defaultdict(list)
        
        for token in tokens:
            word = token.normalized
            word_freq[word] += 1
            word_positions[word].append(token.position)
            
            # Add to inverted index
            self.inverted_index[word].add(doc_id)
        
        # Calculate TF scores and store in database
        total_words = len(tokens)
        
        for word, freq in word_freq.items():
            tf_score = freq / total_words if total_words > 0 else 0
            positions_json = json.dumps(word_positions[word])
            
            self.conn.execute('''
                INSERT OR REPLACE INTO word_index 
                (word, document_id, positions, tf_score)
                VALUES (?, ?, ?, ?)
            ''', (word, doc_id, positions_json, tf_score))
        
        # Store document content
        self.conn.execute('''
            INSERT OR REPLACE INTO documents 
            (id, content, metadata, vector)
            VALUES (?, ?, ?, ?)
        ''', (doc_id, content, metadata_json, None))  # Vector will be computed later
        
        self.conn.commit()
        self.document_store[doc_id] = {
            'content': content,
            'metadata': metadata or {},
            'tokens': tokens
        }
    
    def build_tfidf_vectors(self):
        """Build TF-IDF vectors for all documents"""
        documents = []
        doc_ids = []
        
        for doc_id, doc_data in self.document_store.items():
            # Create normalized text for TF-IDF
            tokens = [token.normalized for token in doc_data['tokens']]
            documents.append(' '.join(tokens))
            doc_ids.append(doc_id)
        
        if documents:
            self.tfidf_vectorizer = TfidfVectorizer(
                lowercase=False,  # Already normalized
                token_pattern=r'\S+',  # Use whitespace as delimiter
                max_features=10000
            )
            
            self.document_vectors = self.tfidf_vectorizer.fit_transform(documents)
            
            # Store vectors in database
            for i, doc_id in enumerate(doc_ids):
                vector_bytes = pickle.dumps(self.document_vectors[i].toarray())
                self.conn.execute('''
                    UPDATE documents SET vector = ? WHERE id = ?
                ''', (vector_bytes, doc_id))
            
            self.conn.commit()
    
    def search(self, query: str, limit: int = 10, search_type: str = 'hybrid') -> List[Dict]:
        """Search documents using various strategies"""
        query_tokens = self.analyzer.analyze_text(query)
        query_words = [token.normalized for token in query_tokens]
        
        if search_type == 'boolean':
            return self.boolean_search(query_words, limit)
        elif search_type == 'fuzzy':
            return self.fuzzy_search(query_words, limit)
        elif search_type == 'semantic':
            return self.semantic_search(query, limit)
        else:  # hybrid
            return self.hybrid_search(query_words, query, limit)
    
    def boolean_search(self, query_words: List[str], limit: int) -> List[Dict]:
        """Boolean search using inverted index"""
        if not query_words:
            return []
        
        # Get candidate documents
        candidate_docs = None
        
        for word in query_words:
            word_docs = set()
            
            cursor = self.conn.execute('''
                SELECT document_id FROM word_index WHERE word = ?
            ''', (word,))
            
            for row in cursor:
                word_docs.add(row[0])
            
            if candidate_docs is None:
                candidate_docs = word_docs
            else:
                # Intersection for AND operation
                candidate_docs = candidate_docs.intersection(word_docs)
        
        # Score and rank results
        results = []
        for doc_id in candidate_docs or []:
            score = self.calculate_boolean_score(doc_id, query_words)
            if doc_id in self.document_store:
                results.append({
                    'id': doc_id,
                    'score': score,
                    'content': self.document_store[doc_id]['content'],
                    'metadata': self.document_store[doc_id]['metadata'],
                    'type': 'boolean'
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def fuzzy_search(self, query_words: List[str], limit: int, threshold: float = 0.7) -> List[Dict]:
        """Fuzzy search using edit distance"""
        from difflib import SequenceMatcher
        
        candidate_docs = defaultdict(float)
        
        # Get all words from index
        cursor = self.conn.execute('SELECT DISTINCT word FROM word_index')
        indexed_words = [row[0] for row in cursor]
        
        # Find similar words for each query word
        for query_word in query_words:
            similar_words = []
            
            for indexed_word in indexed_words:
                similarity = SequenceMatcher(None, query_word, indexed_word).ratio()
                if similarity >= threshold:
                    similar_words.append((indexed_word, similarity))
            
            # Get documents containing similar words
            for word, similarity in similar_words:
                cursor = self.conn.execute('''
                    SELECT document_id, tf_score FROM word_index WHERE word = ?
                ''', (word,))
                
                for doc_id, tf_score in cursor:
                    candidate_docs[doc_id] += tf_score * similarity
        
        # Convert to results format
        results = []
        for doc_id, score in candidate_docs.items():
            if doc_id in self.document_store:
                results.append({
                    'id': doc_id,
                    'score': score,
                    'content': self.document_store[doc_id]['content'],
                    'metadata': self.document_store[doc_id]['metadata'],
                    'type': 'fuzzy'
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def semantic_search(self, query: str, limit: int) -> List[Dict]:
        """Semantic search using TF-IDF vectors"""
        if not self.tfidf_vectorizer:
            return []
        
        # Vectorize query
        query_tokens = self.analyzer.analyze_text(query)
        query_text = ' '.join(token.normalized for token in query_tokens)
        query_vector = self.tfidf_vectorizer.transform([query_text])
        
        # Calculate similarities
        similarities = []
        doc_ids = list(self.document_store.keys())
        
        for i, doc_id in enumerate(doc_ids):
            if i < self.document_vectors.shape[0]:
                doc_vector = self.document_vectors[i]
                similarity = (query_vector * doc_vector.T).toarray()[0][0]
                similarities.append((doc_id, similarity))
        
        # Sort and return results
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in similarities[:limit]:
            if score > 0 and doc_id in self.document_store:
                results.append({
                    'id': doc_id,
                    'score': score,
                    'content': self.document_store[doc_id]['content'],
                    'metadata': self.document_store[doc_id]['metadata'],
                    'type': 'semantic'
                })
        
        return results
    
    def hybrid_search(self, query_words: List[str], query: str, limit: int) -> List[Dict]:
        """Hybrid search combining multiple approaches"""
        # Get results from different methods
        boolean_results = self.boolean_search(query_words, limit * 2)
        fuzzy_results = self.fuzzy_search(query_words, limit * 2)
        semantic_results = self.semantic_search(query, limit * 2)
        
        # Combine and re-score results
        combined_scores = defaultdict(float)
        all_results = {}
        
        # Weight different search types
        weights = {'boolean': 0.4, 'fuzzy': 0.3, 'semantic': 0.3}
        
        for results, search_type in [
            (boolean_results, 'boolean'),
            (fuzzy_results, 'fuzzy'),
            (semantic_results, 'semantic')
        ]:
            for result in results:
                doc_id = result['id']
                combined_scores[doc_id] += result['score'] * weights[search_type]
                all_results[doc_id] = result
        
        # Create final results
        final_results = []
        for doc_id, score in combined_scores.items():
            result = all_results[doc_id].copy()
            result['score'] = score
            result['type'] = 'hybrid'
            final_results.append(result)
        
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:limit]
    
    def calculate_boolean_score(self, doc_id: str, query_words: List[str]) -> float:
        """Calculate relevance score for boolean search"""
        total_score = 0.0
        
        for word in query_words:
            cursor = self.conn.execute('''
                SELECT tf_score FROM word_index 
                WHERE word = ? AND document_id = ?
            ''', (word, doc_id))
            
            row = cursor.fetchone()
            if row:
                total_score += row[0]
        
        return total_score / len(query_words) if query_words else 0.0
    
    def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get word suggestions for autocomplete"""
        cursor = self.conn.execute('''
            SELECT word, COUNT(*) as freq FROM word_index 
            WHERE word LIKE ? 
            GROUP BY word 
            ORDER BY freq DESC 
            LIMIT ?
        ''', (f'{prefix}%', limit))
        
        return [row[0] for row in cursor]
    
    def get_statistics(self) -> Dict:
        """Get index statistics"""
        stats = {}
        
        # Document count
        cursor = self.conn.execute('SELECT COUNT(*) FROM documents')
        stats['document_count'] = cursor.fetchone()[0]
        
        # Unique words count
        cursor = self.conn.execute('SELECT COUNT(DISTINCT word) FROM word_index')
        stats['unique_words'] = cursor.fetchone()[0]
        
        # Total word occurrences
        cursor = self.conn.execute('SELECT COUNT(*) FROM word_index')
        stats['total_word_occurrences'] = cursor.fetchone()[0]
        
        # Average document length
        if self.document_store:
            total_tokens = sum(len(doc['tokens']) for doc in self.document_store.values())
            stats['avg_document_length'] = total_tokens / len(self.document_store)
        else:
            stats['avg_document_length'] = 0
        
        return stats
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
```

## 3. REAL-TIME SEARCH INTERFACE

### 3.1 Frontend Search Component
```javascript
// High-performance Hebrew search interface
class HebrewSearchInterface {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = {
      debounceMs: 300,
      minQueryLength: 2,
      maxSuggestions: 10,
      enableAutoComplete: true,
      enableFuzzySearch: true,
      ...options
    };
    
    this.searchIndex = null;
    this.currentQuery = '';
    this.searchCache = new Map();
    this.searchHistory = [];
    
    this.initializeInterface();
    this.setupEventListeners();
  }
  
  initializeInterface() {
    this.container.innerHTML = `
      <div class="hebrew-search-container">
        <div class="search-input-container">
          <input type="text" 
                 class="hebrew-search-input" 
                 placeholder="חיפוש..."
                 dir="rtl"
                 autocomplete="off">
          <div class="search-suggestions"></div>
        </div>
        <div class="search-filters">
          <label>
            <input type="radio" name="searchType" value="exact" checked>
            חיפוש מדויק
          </label>
          <label>
            <input type="radio" name="searchType" value="fuzzy">
            חיפוש מטושטש
          </label>
          <label>
            <input type="radio" name="searchType" value="semantic">
            חיפוש סמנטי
          </label>
        </div>
        <div class="search-results"></div>
        <div class="search-stats"></div>
      </div>
    `;
    
    // Add CSS for Hebrew search interface
    this.addStyles();
    
    // Get DOM elements
    this.searchInput = this.container.querySelector('.hebrew-search-input');
    this.suggestionsContainer = this.container.querySelector('.search-suggestions');
    this.resultsContainer = this.container.querySelector('.search-results');
    this.statsContainer = this.container.querySelector('.search-stats');
  }
  
  addStyles() {
    const styles = `
      <style>
      .hebrew-search-container {
        font-family: 'HebrewMain', Arial, sans-serif;
        direction: rtl;
        max-width: 800px;
        margin: 0 auto;
      }
      
      .search-input-container {
        position: relative;
        margin-bottom: 20px;
      }
      
      .hebrew-search-input {
        width: 100%;
        padding: 15px;
        font-size: 18px;
        border: 2px solid #ddd;
        border-radius: 8px;
        direction: rtl;
        text-align: right;
        font-family: inherit;
      }
      
      .hebrew-search-input:focus {
        outline: none;
        border-color: #007bff;
        box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
      }
      
      .search-suggestions {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
        display: none;
      }
      
      .suggestion-item {
        padding: 10px 15px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
      }
      
      .suggestion-item:hover,
      .suggestion-item.selected {
        background: #f5f5f5;
      }
      
      .search-filters {
        margin-bottom: 20px;
        text-align: right;
      }
      
      .search-filters label {
        margin-left: 20px;
        cursor: pointer;
      }
      
      .search-results {
        min-height: 200px;
      }
      
      .search-result {
        padding: 15px;
        border: 1px solid #eee;
        border-radius: 4px;
        margin-bottom: 10px;
        background: white;
      }
      
      .result-title {
        font-weight: bold;
        margin-bottom: 5px;
        color: #333;
      }
      
      .result-snippet {
        color: #666;
        line-height: 1.5;
      }
      
      .result-metadata {
        font-size: 12px;
        color: #999;
        margin-top: 10px;
      }
      
      .highlight {
        background-color: yellow;
        font-weight: bold;
      }
      
      .search-stats {
        font-size: 14px;
        color: #666;
        text-align: right;
        margin-top: 20px;
      }
      
      .loading {
        text-align: center;
        padding: 20px;
        color: #666;
      }
      
      .no-results {
        text-align: center;
        padding: 40px;
        color: #999;
      }
      </style>
    `;
    
    document.head.insertAdjacentHTML('beforeend', styles);
  }
  
  setupEventListeners() {
    // Debounced search input
    let searchTimeout;
    this.searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      const query = e.target.value.trim();
      
      if (query.length >= this.options.minQueryLength) {
        searchTimeout = setTimeout(() => {
          this.performSearch(query);
          if (this.options.enableAutoComplete) {
            this.showSuggestions(query);
          }
        }, this.options.debounceMs);
      } else {
        this.clearResults();
        this.hideSuggestions();
      }
    });
    
    // Search type change
    const searchTypeInputs = this.container.querySelectorAll('input[name="searchType"]');
    searchTypeInputs.forEach(input => {
      input.addEventListener('change', () => {
        if (this.currentQuery) {
          this.performSearch(this.currentQuery);
        }
      });
    });
    
    // Keyboard navigation for suggestions
    this.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        this.navigateSuggestions(e.key === 'ArrowDown' ? 1 : -1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        this.selectCurrentSuggestion();
      } else if (e.key === 'Escape') {
        this.hideSuggestions();
      }
    });
    
    // Hide suggestions on outside click
    document.addEventListener('click', (e) => {
      if (!this.container.contains(e.target)) {
        this.hideSuggestions();
      }
    });
  }
  
  async performSearch(query) {
    this.currentQuery = query;
    const searchType = this.getSelectedSearchType();
    
    // Check cache first
    const cacheKey = `${query}:${searchType}`;
    if (this.searchCache.has(cacheKey)) {
      this.displayResults(this.searchCache.get(cacheKey));
      return;
    }
    
    this.showLoading();
    
    try {
      const startTime = performance.now();
      
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          search_type: searchType,
          limit: 20
        })
      });
      
      const results = await response.json();
      const searchTime = performance.now() - startTime;
      
      // Cache results
      this.searchCache.set(cacheKey, results);
      
      // Limit cache size
      if (this.searchCache.size > 100) {
        const firstKey = this.searchCache.keys().next().value;
        this.searchCache.delete(firstKey);
      }
      
      this.displayResults(results);
      this.updateStats(results.length, searchTime);
      
      // Add to search history
      this.addToHistory(query, searchType, results.length);
      
    } catch (error) {
      console.error('Search error:', error);
      this.showError('שגיאה בחיפוש. אנא נסה שוב.');
    }
  }
  
  async showSuggestions(query) {
    try {
      const response = await fetch(`/api/suggestions?prefix=${encodeURIComponent(query)}&limit=${this.options.maxSuggestions}`);
      const suggestions = await response.json();
      
      if (suggestions.length > 0) {
        this.displaySuggestions(suggestions);
      } else {
        this.hideSuggestions();
      }
    } catch (error) {
      console.error('Suggestions error:', error);
    }
  }
  
  displaySuggestions(suggestions) {
    this.suggestionsContainer.innerHTML = suggestions.map(suggestion => 
      `<div class="suggestion-item" data-suggestion="${suggestion}">${suggestion}</div>`
    ).join('');
    
    this.suggestionsContainer.style.display = 'block';
    
    // Add click listeners
    this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', () => {
        this.searchInput.value = item.dataset.suggestion;
        this.hideSuggestions();
        this.performSearch(item.dataset.suggestion);
      });
    });
  }
  
  hideSuggestions() {
    this.suggestionsContainer.style.display = 'none';
  }
  
  navigateSuggestions(direction) {
    const items = this.suggestionsContainer.querySelectorAll('.suggestion-item');
    const currentSelected = this.suggestionsContainer.querySelector('.selected');
    
    let newIndex = 0;
    if (currentSelected) {
      const currentIndex = Array.from(items).indexOf(currentSelected);
      newIndex = currentIndex + direction;
    }
    
    // Wrap around
    if (newIndex < 0) newIndex = items.length - 1;
    if (newIndex >= items.length) newIndex = 0;
    
    // Update selection
    items.forEach(item => item.classList.remove('selected'));
    if (items[newIndex]) {
      items[newIndex].classList.add('selected');
    }
  }
  
  selectCurrentSuggestion() {
    const selected = this.suggestionsContainer.querySelector('.selected');
    if (selected) {
      this.searchInput.value = selected.dataset.suggestion;
      this.hideSuggestions();
      this.performSearch(selected.dataset.suggestion);
    }
  }
  
  displayResults(results) {
    if (results.length === 0) {
      this.resultsContainer.innerHTML = `
        <div class="no-results">
          לא נמצאו תוצאות עבור החיפוש
        </div>
      `;
      return;
    }
    
    const highlightedResults = results.map(result => 
      this.highlightResult(result, this.currentQuery)
    );
    
    this.resultsContainer.innerHTML = highlightedResults.map(result => `
      <div class="search-result">
        <div class="result-title">${result.title || 'ללא כותרת'}</div>
        <div class="result-snippet">${result.snippet}</div>
        <div class="result-metadata">
          ציון: ${result.score.toFixed(3)} | 
          סוג: ${result.type} |
          מזהה: ${result.id}
        </div>
      </div>
    `).join('');
  }
  
  highlightResult(result, query) {
    const queryWords = query.split(/\s+/).filter(word => word.length > 0);
    let snippet = result.content.substring(0, 200);
    
    // Highlight query words in snippet
    queryWords.forEach(word => {
      const regex = new RegExp(`(${word})`, 'gi');
      snippet = snippet.replace(regex, '<span class="highlight">$1</span>');
    });
    
    return {
      ...result,
      title: result.metadata?.title || result.id,
      snippet: snippet + (result.content.length > 200 ? '...' : '')
    };
  }
  
  showLoading() {
    this.resultsContainer.innerHTML = `
      <div class="loading">
        מחפש...
      </div>
    `;
  }
  
  showError(message) {
    this.resultsContainer.innerHTML = `
      <div class="no-results">
        ${message}
      </div>
    `;
  }
  
  clearResults() {
    this.resultsContainer.innerHTML = '';
    this.statsContainer.innerHTML = '';
  }
  
  updateStats(resultCount, searchTime) {
    this.statsContainer.innerHTML = `
      נמצאו ${resultCount} תוצאות (${searchTime.toFixed(0)} ms)
    `;
  }
  
  getSelectedSearchType() {
    const selected = this.container.querySelector('input[name="searchType"]:checked');
    return selected ? selected.value : 'exact';
  }
  
  addToHistory(query, searchType, resultCount) {
    this.searchHistory.unshift({
      query,
      searchType,
      resultCount,
      timestamp: Date.now()
    });
    
    // Keep last 50 searches
    if (this.searchHistory.length > 50) {
      this.searchHistory = this.searchHistory.slice(0, 50);
    }
  }
  
  getSearchHistory() {
    return this.searchHistory;
  }
  
  destroy() {
    // Cleanup event listeners and resources
    this.searchCache.clear();
    this.searchHistory = [];
  }
}

// Initialize Hebrew search interface
document.addEventListener('DOMContentLoaded', () => {
  const searchInterface = new HebrewSearchInterface('search-container', {
    debounceMs: 250,
    minQueryLength: 2,
    maxSuggestions: 8,
    enableAutoComplete: true,
    enableFuzzySearch: true
  });
});
```

## 4. BACKEND SEARCH API

### 4.1 Flask Search Endpoint
```python
from flask import Flask, request, jsonify
import time
import logging
from typing import Dict, List

app = Flask(__name__)
search_index = HebrewSearchIndex()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/search', methods=['POST'])
def search_documents():
    """Main search endpoint"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        search_type = data.get('search_type', 'hybrid')
        limit = min(data.get('limit', 10), 100)  # Max 100 results
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        start_time = time.time()
        
        # Perform search
        results = search_index.search(query, limit=limit, search_type=search_type)
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log search metrics
        logger.info(f"Search query: '{query}' | Type: {search_type} | "
                   f"Results: {len(results)} | Time: {search_time:.2f}ms")
        
        return jsonify({
            'results': results,
            'query': query,
            'search_type': search_type,
            'total_results': len(results),
            'search_time_ms': search_time
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': 'Internal search error'}), 500

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Autocomplete suggestions endpoint"""
    try:
        prefix = request.args.get('prefix', '').strip()
        limit = min(int(request.args.get('limit', 10)), 20)
        
        if len(prefix) < 2:
            return jsonify([])
        
        suggestions = search_index.get_suggestions(prefix, limit)
        
        return jsonify(suggestions)
        
    except Exception as e:
        logger.error(f"Suggestions error: {str(e)}")
        return jsonify([])

@app.route('/api/index/stats', methods=['GET'])
def get_index_stats():
    """Get search index statistics"""
    try:
        stats = search_index.get_statistics()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/index/add', methods=['POST'])
def add_document():
    """Add document to search index"""
    try:
        data = request.get_json()
        doc_id = data.get('id')
        content = data.get('content')
        metadata = data.get('metadata', {})
        
        if not doc_id or not content:
            return jsonify({'error': 'ID and content are required'}), 400
        
        search_index.add_document(doc_id, content, metadata)
        
        logger.info(f"Added document to index: {doc_id}")
        
        return jsonify({'success': True, 'id': doc_id})
        
    except Exception as e:
        logger.error(f"Add document error: {str(e)}")
        return jsonify({'error': 'Failed to add document'}), 500

@app.route('/api/index/rebuild', methods=['POST'])
def rebuild_index():
    """Rebuild TF-IDF vectors"""
    try:
        start_time = time.time()
        search_index.build_tfidf_vectors()
        rebuild_time = time.time() - start_time
        
        logger.info(f"Index rebuilt in {rebuild_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'rebuild_time_seconds': rebuild_time
        })
        
    except Exception as e:
        logger.error(f"Rebuild error: {str(e)}")
        return jsonify({'error': 'Failed to rebuild index'}), 500

if __name__ == '__main__':
    # Initialize with sample data on startup
    logger.info("Initializing search index...")
    
    # Add sample documents (replace with actual data loading)
    sample_docs = [
        {
            'id': 'doc1',
            'content': 'זהו מסמך דוגמה בעברית עם טקסט לבדיקת החיפוש',
            'metadata': {'title': 'מסמך דוגמה 1', 'category': 'בדיקה'}
        },
        {
            'id': 'doc2', 
            'content': 'מסמך נוסף לבדיקת יכולות החיפוש בעברית',
            'metadata': {'title': 'מסמך דוגמה 2', 'category': 'בדיקה'}
        }
    ]
    
    for doc in sample_docs:
        search_index.add_document(doc['id'], doc['content'], doc['metadata'])
    
    # Build TF-IDF vectors
    search_index.build_tfidf_vectors()
    
    logger.info("Search index initialized successfully")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
```

## 5. PERFORMANCE MONITORING

### 5.1 Search Performance Metrics
```python
import time
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta

class SearchPerformanceMonitor:
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.query_times = deque(maxlen=window_size)
        self.query_types = defaultdict(int)
        self.query_results = deque(maxlen=window_size)
        self.error_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
    def record_search(self, query, search_type, result_count, execution_time, cached=False):
        """Record search performance metrics"""
        timestamp = time.time()
        
        self.query_times.append({
            'timestamp': timestamp,
            'execution_time': execution_time,
            'query_length': len(query),
            'result_count': result_count,
            'search_type': search_type,
            'cached': cached
        })
        
        self.query_types[search_type] += 1
        self.query_results.append(result_count)
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_error(self, query, error_type):
        """Record search errors"""
        self.error_count += 1
        logger.error(f"Search error - Query: '{query}' | Error: {error_type}")
    
    def get_performance_stats(self, time_window_hours=1):
        """Get performance statistics for time window"""
        cutoff_time = time.time() - (time_window_hours * 3600)
        
        recent_queries = [
            q for q in self.query_times 
            if q['timestamp'] > cutoff_time
        ]
        
        if not recent_queries:
            return {'error': 'No recent queries'}
        
        execution_times = [q['execution_time'] for q in recent_queries]
        result_counts = [q['result_count'] for q in recent_queries]
        
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        stats = {
            'total_queries': len(recent_queries),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'avg_result_count': sum(result_counts) / len(result_counts),
            'cache_hit_rate': cache_hit_rate,
            'error_rate': self.error_count / len(recent_queries) if recent_queries else 0,
            'queries_per_hour': len(recent_queries) / time_window_hours,
            'query_types': dict(self.query_types)
        }
        
        return stats
    
    def get_slow_queries(self, threshold_ms=1000):
        """Get queries that exceeded performance threshold"""
        slow_queries = [
            q for q in self.query_times 
            if q['execution_time'] > threshold_ms
        ]
        
        return sorted(slow_queries, key=lambda x: x['execution_time'], reverse=True)
    
    def export_metrics(self):
        """Export metrics for external monitoring systems"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.get_performance_stats(),
            'slow_queries': self.get_slow_queries(),
            'system_info': {
                'window_size': self.window_size,
                'total_errors': self.error_count,
                'cache_performance': {
                    'hits': self.cache_hits,
                    'misses': self.cache_misses,
                    'hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
                }
            }
        }

# Global performance monitor instance
search_monitor = SearchPerformanceMonitor()
```

## 6. IMPLEMENTATION CHECKLIST

### Phase 1: Core Search Infrastructure (Week 1)
- [ ] Implement Hebrew text analyzer
- [ ] Build inverted index system
- [ ] Set up SQLite database schema
- [ ] Create basic search API

### Phase 2: Advanced Search Features (Week 2)
- [ ] Implement fuzzy search
- [ ] Add TF-IDF semantic search
- [ ] Build autocomplete system
- [ ] Create hybrid search combination

### Phase 3: Frontend & Optimization (Week 3)
- [ ] Build Hebrew search interface
- [ ] Implement result highlighting
- [ ] Add performance monitoring
- [ ] Optimize search caching

### Success Metrics
- **Search Response Time**: < 100ms for exact search, < 500ms for fuzzy/semantic
- **Index Build Time**: < 10 seconds for 10,000 documents
- **Memory Usage**: < 200MB for 50,000 indexed documents
- **Cache Hit Rate**: > 85%
- **Autocomplete Response**: < 50ms

This comprehensive search indexing strategy provides lightning-fast Hebrew text search with advanced features while maintaining excellent performance and scalability.