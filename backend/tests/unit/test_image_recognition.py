"""
Unit tests for the image recognition service.

Tests recognize_option_from_image, _extract_json, and error handling
for missing API keys.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.image_recognition_service import ImageRecognitionService


# ---------------------------------------------------------------------------
# Sample responses
# ---------------------------------------------------------------------------

VALID_GEMINI_RESPONSE = {
    "candidates": [{
        "content": {
            "parts": [{
                "text": json.dumps({
                    "symbol": "AAPL",
                    "option_type": "CALL",
                    "strike": 230,
                    "expiry_date": "2025-02-21",
                    "option_price": 5.50,
                    "implied_volatility": 0.28,
                    "confidence": "high",
                    "notes": "Clearly visible"
                })
            }]
        }
    }]
}


# ===================================================================
# test_recognize_success
# ===================================================================

class TestRecognizeSuccess:
    """Mock Gemini API returning a valid result."""

    @patch('app.services.image_recognition_service.Config')
    @patch('app.services.image_recognition_service.requests.post')
    def test_valid_recognition(self, mock_post, mock_config):
        mock_config.GOOGLE_API_KEY = 'test-key-123'

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = VALID_GEMINI_RESPONSE
        mock_post.return_value = mock_resp

        result = ImageRecognitionService.recognize_option_from_image(
            image_data=b'\x89PNG\r\n\x1a\n' + b'\x00' * 100,
            mime_type='image/png',
        )

        assert result['success'] is True
        assert result['data']['symbol'] == 'AAPL'
        assert result['data']['option_type'] == 'CALL'
        assert result['data']['strike'] == 230.0
        assert result['data']['expiry_date'] == '2025-02-21'
        assert result['data']['option_price'] == 5.50
        assert result['data']['implied_volatility'] == 0.28

    @patch('app.services.image_recognition_service.Config')
    @patch('app.services.image_recognition_service.requests.post')
    def test_symbol_uppercase(self, mock_post, mock_config):
        """Symbol should be uppercased even if API returns lowercase."""
        mock_config.GOOGLE_API_KEY = 'test-key'
        response_data = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "symbol": "aapl",
                            "option_type": "CALL",
                            "strike": 230,
                            "expiry_date": "2025-02-21",
                            "option_price": 5.50,
                        })
                    }]
                }
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response_data
        mock_post.return_value = mock_resp

        result = ImageRecognitionService.recognize_option_from_image(b'\x00' * 10)
        assert result['success'] is True
        assert result['data']['symbol'] == 'AAPL'


# ===================================================================
# test_recognize_no_api_key
# ===================================================================

class TestRecognizeNoApiKey:
    """When no API key is configured, return an error."""

    @patch('app.services.image_recognition_service.Config')
    def test_returns_error_without_key(self, mock_config):
        mock_config.GOOGLE_API_KEY = ''

        result = ImageRecognitionService.recognize_option_from_image(b'\x00' * 10)

        assert result['success'] is False
        assert 'not configured' in result['error'].lower() or 'api key' in result['error'].lower()

    @patch('app.services.image_recognition_service.Config')
    def test_returns_error_none_key(self, mock_config):
        mock_config.GOOGLE_API_KEY = None

        result = ImageRecognitionService.recognize_option_from_image(b'\x00' * 10)

        assert result['success'] is False


# ===================================================================
# test_extract_json_from_markdown
# ===================================================================

class TestExtractJsonFromMarkdown:
    """_extract_json should extract JSON from a markdown code block."""

    def test_code_block_json(self):
        text = '```json\n{"symbol": "TSLA", "strike": 300}\n```'
        result = ImageRecognitionService._extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed['symbol'] == 'TSLA'
        assert parsed['strike'] == 300

    def test_code_block_no_language(self):
        text = '```\n{"symbol": "NVDA", "strike": 120}\n```'
        result = ImageRecognitionService._extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed['symbol'] == 'NVDA'

    def test_surrounded_by_text(self):
        text = 'Here is the result:\n{"symbol": "AMD", "strike": 150}\nDone.'
        result = ImageRecognitionService._extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed['symbol'] == 'AMD'


# ===================================================================
# test_extract_json_direct
# ===================================================================

class TestExtractJsonDirect:
    """_extract_json should directly parse clean JSON strings."""

    def test_direct_json(self):
        text = '{"symbol": "GOOGL", "strike": 180}'
        result = ImageRecognitionService._extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed['symbol'] == 'GOOGL'

    def test_direct_json_with_whitespace(self):
        text = '  {"symbol": "META", "strike": 500}  '
        result = ImageRecognitionService._extract_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed['symbol'] == 'META'

    def test_returns_none_for_no_json(self):
        text = 'This text has no JSON at all.'
        result = ImageRecognitionService._extract_json(text)
        assert result is None
