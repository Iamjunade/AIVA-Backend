"""
Tests for AIVA Recognition Engine + IDENTIFY Intent
=======================================================
Tests category detection, prompt selection, intent classification,
and fallback behavior.
"""

import pytest
from unittest.mock import MagicMock, patch

from server.recognition_engine import (
    RecognitionEngine,
    RecognitionCategory,
    detect_category,
    PROMPTS,
)
from server.intent_classifier import IntentClassifier, Intent


# =============================================================================
# CATEGORY DETECTION
# =============================================================================

class TestCategoryDetection:
    """Test automatic category detection from user queries."""

    def test_currency_keywords(self):
        assert detect_category("what currency is this") == RecognitionCategory.CURRENCY
        assert detect_category("how much money is this") == RecognitionCategory.CURRENCY
        assert detect_category("identify this rupee note") == RecognitionCategory.CURRENCY
        assert detect_category("what dollar bill is this") == RecognitionCategory.CURRENCY
        assert detect_category("is this a coin") == RecognitionCategory.CURRENCY

    def test_document_keywords(self):
        assert detect_category("what document is this") == RecognitionCategory.DOCUMENT
        assert detect_category("read this id card") == RecognitionCategory.DOCUMENT
        assert detect_category("is this my passport") == RecognitionCategory.DOCUMENT
        assert detect_category("what's on this certificate") == RecognitionCategory.DOCUMENT
        assert detect_category("identify this license") == RecognitionCategory.DOCUMENT

    def test_product_keywords(self):
        assert detect_category("what product is this") == RecognitionCategory.PRODUCT
        assert detect_category("identify this bottle") == RecognitionCategory.PRODUCT
        assert detect_category("what brand is this") == RecognitionCategory.PRODUCT
        assert detect_category("what's in this box") == RecognitionCategory.PRODUCT
        assert detect_category("is this a medicine") == RecognitionCategory.PRODUCT

    def test_general_fallback(self):
        assert detect_category("what is this") == RecognitionCategory.GENERAL
        assert detect_category("identify this") == RecognitionCategory.GENERAL
        assert detect_category("what am I holding") == RecognitionCategory.GENERAL
        assert detect_category("") == RecognitionCategory.GENERAL


# =============================================================================
# PROMPTS
# =============================================================================

class TestPrompts:
    """Test that prompts exist for all categories and follow rules."""

    def test_all_categories_have_prompts(self):
        for cat in [RecognitionCategory.CURRENCY, RecognitionCategory.DOCUMENT,
                     RecognitionCategory.PRODUCT, RecognitionCategory.GENERAL]:
            assert cat in PROMPTS
            assert len(PROMPTS[cat]) > 50  # Not empty

    def test_prompts_contain_anti_hallucination(self):
        for cat, prompt in PROMPTS.items():
            assert "SOLELY" in prompt or "solely" in prompt, \
                f"Prompt for {cat} missing anti-hallucination rule"

    def test_prompts_mention_blind_user(self):
        for cat, prompt in PROMPTS.items():
            assert "blind" in prompt.lower(), \
                f"Prompt for {cat} should mention blind user context"


# =============================================================================
# RECOGNITION ENGINE
# =============================================================================

class TestRecognitionEngine:
    """Test the RecognitionEngine class."""

    def _make_engine(self):
        """Create an engine with Gemini mocked out."""
        with patch.object(RecognitionEngine, '_initialize_gemini'):
            engine = RecognitionEngine()
        engine._model = None
        return engine

    def test_unavailable_without_model(self):
        engine = self._make_engine()
        assert engine.is_available is False

    def test_unavailable_returns_message(self):
        engine = self._make_engine()
        result = engine.identify(b"fake_jpeg", "what is this")
        assert "not available" in result.lower()

    def test_identify_with_mock_gemini(self):
        engine = self._make_engine()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a 500 Indian rupee note."
        mock_model.generate_content.return_value = mock_response
        engine._model = mock_model

        # Create a minimal valid JPEG
        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        jpeg_bytes = buf.getvalue()

        result = engine.identify(jpeg_bytes, "what currency is this")
        assert "500" in result
        assert "rupee" in result.lower()
        mock_model.generate_content.assert_called_once()

    def test_identify_truncates_long_response(self):
        engine = self._make_engine()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "A" * 200  # Very long response
        mock_model.generate_content.return_value = mock_response
        engine._model = mock_model

        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')

        result = engine.identify(buf.getvalue(), "identify")
        assert len(result) <= 150

    def test_identify_handles_gemini_error(self):
        engine = self._make_engine()
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        engine._model = mock_model

        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')

        result = engine.identify(buf.getvalue(), "what is this")
        assert "trouble" in result.lower() or "try again" in result.lower()


# =============================================================================
# INTENT CLASSIFIER — IDENTIFY PATTERNS
# =============================================================================

class TestIdentifyIntent:
    """Test that the IDENTIFY intent is correctly classified."""

    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_what_is_this(self):
        assert self.classifier.classify("what is this") == Intent.IDENTIFY

    def test_identify(self):
        assert self.classifier.classify("identify this") == Intent.IDENTIFY

    def test_what_am_i_holding(self):
        assert self.classifier.classify("what am I holding") == Intent.IDENTIFY

    def test_currency_queries(self):
        assert self.classifier.classify("what currency is this") == Intent.IDENTIFY
        assert self.classifier.classify("how much money") == Intent.IDENTIFY
        assert self.classifier.classify("is this a rupee note") == Intent.IDENTIFY

    def test_document_queries(self):
        assert self.classifier.classify("what document is this") == Intent.IDENTIFY
        assert self.classifier.classify("is this my passport") == Intent.IDENTIFY
        assert self.classifier.classify("read my id card") == Intent.IDENTIFY

    def test_product_queries(self):
        assert self.classifier.classify("what brand is this") == Intent.IDENTIFY
        assert self.classifier.classify("identify this bottle") == Intent.IDENTIFY
        assert self.classifier.classify("what product is this") == Intent.IDENTIFY

    def test_existing_intents_still_work(self):
        """Regression: ensure existing intents are not broken."""
        assert self.classifier.classify("help me") == Intent.EMERGENCY
        assert self.classifier.classify("where am I") == Intent.LOCATION
        assert self.classifier.classify("what's around me") == Intent.SURROUNDINGS
        assert self.classifier.classify("describe the scene") == Intent.DESCRIBE
        assert self.classifier.classify("check battery") == Intent.BATTERY
