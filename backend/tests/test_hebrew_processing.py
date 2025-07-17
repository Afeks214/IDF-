#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Hebrew Processing Tests
Comprehensive testing for Hebrew text processing and RTL functionality
"""

import pytest
import unicodedata
from typing import List, Dict, Any
import time
import re

# Hebrew test data
HEBREW_TEST_SAMPLES = {
    "simple_hebrew": "שלום עולם",
    "hebrew_with_numbers": "בדיקה 123 מספרים",
    "hebrew_with_punctuation": "שלום, עולם! איך הולך?",
    "mixed_content": "Hello שלום World עולם",
    "rtl_marks": "‏שלום‏ ‏עולם‏",
    "long_text": (
        "זהו טקסט ארוך בעברית לבדיקת ביצועים ועיבוד נכון של טקסט עברי. "
        "הטקסט כולל מילים רבות ומשפטים מורכבים כדי לוודא שהמערכת "
        "מטפלת נכון בעברית בכל המצבים האפשריים. בדיקה זו חשובה מאוד "
        "להבטחת איכות המערכת ותמיכה מלאה בשפה העברית."
    ),
    "technical_terms": [
        "מערכת תקשורת",
        "בדיקת רדיו VHF", 
        "הצפנת מידע",
        "רשת תקשובת",
        "מערכת ניווט GPS",
        "אבטחת מידע",
        "פרוטוקול TCP/IP",
        "תדר UHF"
    ],
    "status_values": {
        "active": "פעיל",
        "pending": "ממתין",
        "completed": "הושלם",
        "failed": "נכשל",
        "cancelled": "מבוטל"
    }
}

class HebrewTextProcessor:
    """Helper class for Hebrew text processing during tests"""
    
    @staticmethod
    def is_hebrew_char(char: str) -> bool:
        """Check if character is Hebrew"""
        code = ord(char)
        return (0x0590 <= code <= 0x05FF or  # Hebrew block
                0xFB1D <= code <= 0xFB4F)    # Hebrew presentation forms
    
    @staticmethod
    def is_hebrew_text(text: str) -> bool:
        """Check if text contains Hebrew characters"""
        return any(HebrewTextProcessor.is_hebrew_char(char) for char in text)
    
    @staticmethod
    def normalize_hebrew(text: str) -> str:
        """Normalize Hebrew text for consistent processing"""
        # Unicode normalization
        normalized = unicodedata.normalize('NFKC', text)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    @staticmethod
    def extract_hebrew_words(text: str) -> List[str]:
        """Extract Hebrew words from mixed content"""
        words = []
        current_word = ""
        
        for char in text:
            if HebrewTextProcessor.is_hebrew_char(char) or char.isspace():
                if char.isspace() and current_word:
                    if any(HebrewTextProcessor.is_hebrew_char(c) for c in current_word):
                        words.append(current_word.strip())
                    current_word = ""
                elif not char.isspace():
                    current_word += char
        
        # Add final word
        if current_word and any(HebrewTextProcessor.is_hebrew_char(c) for c in current_word):
            words.append(current_word.strip())
        
        return words
    
    @staticmethod
    def detect_text_direction(text: str) -> str:
        """Detect text direction (RTL/LTR)"""
        hebrew_chars = sum(1 for char in text if HebrewTextProcessor.is_hebrew_char(char))
        latin_chars = sum(1 for char in text if char.isascii() and char.isalpha())
        
        if hebrew_chars > latin_chars:
            return "rtl"
        elif latin_chars > hebrew_chars:
            return "ltr"
        else:
            return "mixed"


@pytest.mark.hebrew
class TestHebrewTextDetection:
    """Test Hebrew text detection and classification"""
    
    def test_hebrew_character_detection(self):
        """Test detection of Hebrew characters"""
        processor = HebrewTextProcessor()
        
        # Test Hebrew characters
        assert processor.is_hebrew_char('א')
        assert processor.is_hebrew_char('ב')
        assert processor.is_hebrew_char('ת')
        
        # Test non-Hebrew characters
        assert not processor.is_hebrew_char('a')
        assert not processor.is_hebrew_char('1')
        assert not processor.is_hebrew_char(' ')
    
    def test_hebrew_text_detection(self):
        """Test detection of Hebrew text in strings"""
        processor = HebrewTextProcessor()
        
        # Pure Hebrew
        assert processor.is_hebrew_text(HEBREW_TEST_SAMPLES["simple_hebrew"])
        
        # Mixed content
        assert processor.is_hebrew_text(HEBREW_TEST_SAMPLES["mixed_content"])
        
        # Non-Hebrew
        assert not processor.is_hebrew_text("Hello World")
        assert not processor.is_hebrew_text("123456")
        assert not processor.is_hebrew_text("")
    
    def test_text_direction_detection(self):
        """Test RTL/LTR direction detection"""
        processor = HebrewTextProcessor()
        
        # Hebrew text should be RTL
        assert processor.detect_text_direction(HEBREW_TEST_SAMPLES["simple_hebrew"]) == "rtl"
        
        # English text should be LTR
        assert processor.detect_text_direction("Hello World") == "ltr"
        
        # Mixed content should be detected as mixed
        assert processor.detect_text_direction(HEBREW_TEST_SAMPLES["mixed_content"]) == "mixed"


@pytest.mark.hebrew
class TestHebrewTextNormalization:
    """Test Hebrew text normalization and processing"""
    
    def test_unicode_normalization(self):
        """Test Unicode normalization for Hebrew text"""
        processor = HebrewTextProcessor()
        
        # Test various Hebrew text samples
        for key, text in HEBREW_TEST_SAMPLES.items():
            if isinstance(text, str):
                normalized = processor.normalize_hebrew(text)
                
                # Normalized text should be valid Unicode
                assert isinstance(normalized, str)
                assert len(normalized) > 0 or len(text) == 0
                
                # Should handle Unicode normalization
                assert unicodedata.is_normalized('NFKC', normalized)
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization in Hebrew text"""
        processor = HebrewTextProcessor()
        
        # Text with extra spaces
        text_with_spaces = "שלום    עולם   123"
        normalized = processor.normalize_hebrew(text_with_spaces)
        
        # Should have single spaces only
        assert "  " not in normalized
        assert normalized == "שלום עולם 123"
    
    def test_hebrew_word_extraction(self):
        """Test extraction of Hebrew words from mixed content"""
        processor = HebrewTextProcessor()
        
        # Mixed content
        mixed_text = HEBREW_TEST_SAMPLES["mixed_content"]
        hebrew_words = processor.extract_hebrew_words(mixed_text)
        
        assert "שלום" in hebrew_words
        assert "עולם" in hebrew_words
        assert "Hello" not in hebrew_words
        assert "World" not in hebrew_words


@pytest.mark.hebrew
@pytest.mark.performance
class TestHebrewProcessingPerformance:
    """Test performance of Hebrew text processing"""
    
    def test_hebrew_detection_performance(self, performance_timer):
        """Test performance of Hebrew character detection"""
        processor = HebrewTextProcessor()
        
        # Large Hebrew text for performance testing
        large_text = HEBREW_TEST_SAMPLES["long_text"] * 100
        
        performance_timer.start()
        
        # Run detection multiple times
        for _ in range(1000):
            processor.is_hebrew_text(large_text)
        
        duration = performance_timer.stop()
        
        # Should complete 1000 detections quickly
        performance_timer.assert_faster_than(1.0)
    
    def test_normalization_performance(self, performance_timer):
        """Test performance of Hebrew text normalization"""
        processor = HebrewTextProcessor()
        
        # Test with various text sizes
        test_texts = [
            HEBREW_TEST_SAMPLES["simple_hebrew"] * 10,
            HEBREW_TEST_SAMPLES["long_text"] * 5,
            HEBREW_TEST_SAMPLES["mixed_content"] * 20
        ]
        
        performance_timer.start()
        
        for text in test_texts:
            for _ in range(100):
                processor.normalize_hebrew(text)
        
        duration = performance_timer.stop()
        
        # Should handle normalization efficiently
        performance_timer.assert_faster_than(2.0)
    
    def test_word_extraction_performance(self, performance_timer):
        """Test performance of Hebrew word extraction"""
        processor = HebrewTextProcessor()
        
        # Create complex mixed content
        mixed_content = " ".join([
            HEBREW_TEST_SAMPLES["mixed_content"],
            "English text here",
            HEBREW_TEST_SAMPLES["simple_hebrew"],
            "More English",
            HEBREW_TEST_SAMPLES["hebrew_with_numbers"]
        ]) * 50
        
        performance_timer.start()
        
        for _ in range(100):
            words = processor.extract_hebrew_words(mixed_content)
        
        duration = performance_timer.stop()
        
        # Should extract words efficiently
        performance_timer.assert_faster_than(3.0)


@pytest.mark.hebrew
class TestHebrewDataValidation:
    """Test validation of Hebrew data in business context"""
    
    def test_technical_terms_validation(self):
        """Test validation of Hebrew technical terms"""
        processor = HebrewTextProcessor()
        
        for term in HEBREW_TEST_SAMPLES["technical_terms"]:
            # Should be detected as Hebrew
            assert processor.is_hebrew_text(term)
            
            # Should normalize properly
            normalized = processor.normalize_hebrew(term)
            assert len(normalized) > 0
            
            # Should maintain meaning (basic length check)
            assert len(normalized) >= len(term) * 0.8  # Allow for normalization
    
    def test_status_translation_validation(self):
        """Test validation of status value translations"""
        processor = HebrewTextProcessor()
        
        for english, hebrew in HEBREW_TEST_SAMPLES["status_values"].items():
            # Hebrew status should be detected as Hebrew
            assert processor.is_hebrew_text(hebrew)
            
            # English status should not be detected as Hebrew
            assert not processor.is_hebrew_text(english)
            
            # Both should normalize without errors
            normalized_hebrew = processor.normalize_hebrew(hebrew)
            normalized_english = processor.normalize_hebrew(english)
            
            assert len(normalized_hebrew) > 0
            assert len(normalized_english) > 0
    
    def test_data_consistency_validation(self):
        """Test consistency of Hebrew data processing"""
        processor = HebrewTextProcessor()
        
        # Same text should normalize to same result
        text = HEBREW_TEST_SAMPLES["long_text"]
        
        results = [processor.normalize_hebrew(text) for _ in range(10)]
        
        # All results should be identical
        assert all(result == results[0] for result in results)


@pytest.mark.hebrew
class TestRTLTextHandling:
    """Test Right-to-Left text handling and formatting"""
    
    def test_rtl_mark_handling(self):
        """Test handling of RTL marks in text"""
        processor = HebrewTextProcessor()
        
        text_with_marks = HEBREW_TEST_SAMPLES["rtl_marks"]
        
        # Should still be detected as Hebrew
        assert processor.is_hebrew_text(text_with_marks)
        
        # Should normalize properly
        normalized = processor.normalize_hebrew(text_with_marks)
        assert len(normalized) > 0
    
    def test_mixed_direction_text(self):
        """Test handling of mixed RTL/LTR text"""
        processor = HebrewTextProcessor()
        
        mixed_text = HEBREW_TEST_SAMPLES["mixed_content"]
        
        # Should detect as mixed direction
        direction = processor.detect_text_direction(mixed_text)
        assert direction == "mixed"
        
        # Should extract Hebrew parts correctly
        hebrew_words = processor.extract_hebrew_words(mixed_text)
        assert len(hebrew_words) > 0
        assert all(processor.is_hebrew_text(word) for word in hebrew_words)
    
    def test_number_handling_in_hebrew(self):
        """Test handling of numbers within Hebrew text"""
        processor = HebrewTextProcessor()
        
        text_with_numbers = HEBREW_TEST_SAMPLES["hebrew_with_numbers"]
        
        # Should be detected as Hebrew (contains Hebrew)
        assert processor.is_hebrew_text(text_with_numbers)
        
        # Should normalize properly
        normalized = processor.normalize_hebrew(text_with_numbers)
        assert "123" in normalized
        assert processor.is_hebrew_text(normalized)


@pytest.mark.hebrew
@pytest.mark.integration
class TestHebrewIntegrationScenarios:
    """Test Hebrew processing in realistic integration scenarios"""
    
    def test_search_scenario(self):
        """Test Hebrew text in search scenarios"""
        processor = HebrewTextProcessor()
        
        # Simulate search data
        search_terms = ["תקשורת", "רדיו", "בדיקה"]
        document_texts = [
            "בדיקת מערכת תקשורת במשרד הביטחון",
            "רדיו VHF לצורכי תקשורת צבאית",
            "מערכת הצפנה מתקדמת לתקשובת"
        ]
        
        for term in search_terms:
            assert processor.is_hebrew_text(term)
            
            for doc in document_texts:
                if term in doc:
                    # Document should be properly processed
                    normalized_doc = processor.normalize_hebrew(doc)
                    assert processor.is_hebrew_text(normalized_doc)
                    assert term in normalized_doc
    
    def test_data_import_scenario(self):
        """Test Hebrew processing in data import scenarios"""
        processor = HebrewTextProcessor()
        
        # Simulate Excel data import
        excel_data = [
            {"name": "בדיקת מערכת A", "status": "פעיל", "type": "תקשורת"},
            {"name": "בדיקת מערכת B", "status": "ממתין", "type": "רדיו"},
            {"name": "System Test C", "status": "completed", "type": "security"}
        ]
        
        for row in excel_data:
            for field, value in row.items():
                if isinstance(value, str):
                    # Should process without errors
                    normalized = processor.normalize_hebrew(value)
                    assert isinstance(normalized, str)
                    
                    # Hebrew content should be preserved
                    if processor.is_hebrew_text(value):
                        assert processor.is_hebrew_text(normalized)
    
    def test_api_response_scenario(self):
        """Test Hebrew text in API response scenarios"""
        processor = HebrewTextProcessor()
        
        # Simulate API responses with Hebrew content
        api_responses = [
            {
                "id": 1,
                "test_name": "בדיקת תקשורת",
                "description": "בדיקה מקיפה של מערכת התקשורת",
                "status": "active",
                "status_hebrew": "פעיל"
            },
            {
                "id": 2,
                "test_name": "Radio VHF Test",
                "description": "Testing VHF radio communications",
                "status": "pending",
                "status_hebrew": "ממתין"
            }
        ]
        
        for response in api_responses:
            # Process all string fields
            for key, value in response.items():
                if isinstance(value, str):
                    normalized = processor.normalize_hebrew(value)
                    
                    # Ensure data integrity
                    assert len(normalized) > 0 or len(value) == 0
                    
                    # Hebrew fields should maintain their Hebrew nature
                    if "hebrew" in key.lower() or processor.is_hebrew_text(value):
                        assert processor.is_hebrew_text(normalized) or len(normalized) == 0


@pytest.mark.hebrew
class TestHebrewErrorHandling:
    """Test error handling in Hebrew text processing"""
    
    def test_empty_text_handling(self):
        """Test handling of empty or None text"""
        processor = HebrewTextProcessor()
        
        # Empty string
        assert not processor.is_hebrew_text("")
        assert processor.normalize_hebrew("") == ""
        
        # Whitespace only
        assert not processor.is_hebrew_text("   ")
        assert processor.normalize_hebrew("   ") == ""
    
    def test_invalid_unicode_handling(self):
        """Test handling of invalid Unicode sequences"""
        processor = HebrewTextProcessor()
        
        # Test with various edge cases
        edge_cases = [
            "\ufffd",  # Replacement character
            "שלום\x00עולם",  # Null character in middle
            "valid text",  # Normal text as control
        ]
        
        for text in edge_cases:
            try:
                # Should not crash
                result = processor.normalize_hebrew(text)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"Processing failed for '{text}': {e}")
    
    def test_very_long_text_handling(self):
        """Test handling of very long Hebrew text"""
        processor = HebrewTextProcessor()
        
        # Create very long Hebrew text
        very_long_text = HEBREW_TEST_SAMPLES["long_text"] * 1000
        
        # Should handle without errors or timeouts
        start_time = time.time()
        
        result = processor.normalize_hebrew(very_long_text)
        is_hebrew = processor.is_hebrew_text(very_long_text)
        words = processor.extract_hebrew_words(very_long_text)
        
        end_time = time.time()
        
        # Should complete in reasonable time (< 5 seconds)
        assert end_time - start_time < 5.0
        
        # Results should be valid
        assert isinstance(result, str)
        assert isinstance(is_hebrew, bool)
        assert isinstance(words, list)
        assert is_hebrew == True
        assert len(words) > 0


# Test utilities for Hebrew-specific testing
class HebrewTestUtils:
    """Utility class for Hebrew-specific test helpers"""
    
    @staticmethod
    def generate_hebrew_test_data(count: int = 100) -> List[Dict[str, Any]]:
        """Generate test data with Hebrew content"""
        base_names = HEBREW_TEST_SAMPLES["technical_terms"]
        statuses = list(HEBREW_TEST_SAMPLES["status_values"].values())
        
        test_data = []
        for i in range(count):
            test_data.append({
                "id": i + 1,
                "name": f"{base_names[i % len(base_names)]} {i}",
                "status": statuses[i % len(statuses)],
                "description": f"תיאור לבדיקה מספר {i + 1}",
                "created_date": f"2024-01-{(i % 28) + 1:02d}"
            })
        
        return test_data
    
    @staticmethod
    def validate_hebrew_data_integrity(data: List[Dict[str, Any]]) -> bool:
        """Validate integrity of Hebrew data"""
        processor = HebrewTextProcessor()
        
        for item in data:
            for key, value in item.items():
                if isinstance(value, str) and processor.is_hebrew_text(value):
                    # Hebrew text should normalize without data loss
                    normalized = processor.normalize_hebrew(value)
                    if len(normalized) < len(value) * 0.5:  # Significant data loss
                        return False
        
        return True


@pytest.fixture
def hebrew_test_utils():
    """Fixture providing Hebrew test utilities"""
    return HebrewTestUtils()


@pytest.fixture
def sample_hebrew_dataset(hebrew_test_utils):
    """Fixture providing sample Hebrew dataset"""
    return hebrew_test_utils.generate_hebrew_test_data(50)