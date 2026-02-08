"""
Unit tests for the narrative radar service.

Tests get_preset_narratives, preset structure, fallback behaviour,
and custom concept analysis.
"""

import pytest
from unittest.mock import patch

from app.services.narrative_service import (
    get_preset_narratives,
    analyze_narrative,
    PRESET_NARRATIVES,
    FALLBACK_DATA,
)


# ===================================================================
# test_get_preset_narratives
# ===================================================================

class TestGetPresetNarratives:
    """get_preset_narratives should return exactly 10 preset narratives."""

    def test_returns_10_presets(self):
        presets = get_preset_narratives()
        assert len(presets) == 10, f"Expected 10 presets, got {len(presets)}"

    def test_returns_dict(self):
        presets = get_preset_narratives()
        assert isinstance(presets, dict)

    def test_known_keys_present(self):
        presets = get_preset_narratives()
        expected_keys = {
            'musk', 'buffett', 'ark', 'dalio', 'burry',
            'ai_chips', 'glp1', 'quantum', 'robotics', 'ev_battery',
        }
        assert set(presets.keys()) == expected_keys


# ===================================================================
# test_preset_has_person_and_theme
# ===================================================================

class TestPresetHasPersonAndTheme:
    """Preset narratives should contain both 'person'/'institution' and 'theme' types."""

    def test_has_person_or_institution_type(self):
        presets = get_preset_narratives()
        person_types = {k for k, v in presets.items() if v['type'] in ('person', 'institution')}
        assert len(person_types) > 0, "No person/institution type found"

    def test_has_theme_type(self):
        presets = get_preset_narratives()
        theme_types = {k for k, v in presets.items() if v['type'] == 'theme'}
        assert len(theme_types) > 0, "No theme type found"

    def test_each_preset_has_required_fields(self):
        presets = get_preset_narratives()
        required = {'name_zh', 'name_en', 'type', 'description_zh', 'description_en'}
        for key, preset in presets.items():
            missing = required - set(preset.keys())
            assert not missing, f"Preset '{key}' missing fields: {missing}"


# ===================================================================
# test_analyze_with_fallback
# ===================================================================

class TestAnalyzeWithFallback:
    """When GOOGLE_API_KEY is not set, analyze_narrative uses fallback data."""

    @patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=False)
    def test_returns_fallback_for_known_narrative(self):
        result = analyze_narrative(
            concept='',
            narrative_key='musk',
            lang='zh',
        )
        assert result.get('_source') == 'fallback'
        assert 'stocks' in result
        assert len(result['stocks']) > 0

    @patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=False)
    def test_fallback_english(self):
        result = analyze_narrative(
            concept='',
            narrative_key='buffett',
            lang='en',
        )
        assert result.get('_source') == 'fallback'
        assert result['narrative']['name'] == 'Buffett Portfolio'

    @patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=False)
    def test_returns_error_for_unknown_narrative(self):
        result = analyze_narrative(
            concept='SomeUnknownConcept',
            narrative_key='nonexistent',
            lang='zh',
        )
        assert 'error' in result
        assert result['stocks'] == []


# ===================================================================
# test_analyze_custom_concept
# ===================================================================

class TestAnalyzeCustomConcept:
    """Custom concept analysis when no narrative_key and no API key."""

    @patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=False)
    def test_custom_concept_no_api_key(self):
        result = analyze_narrative(
            concept='Autonomous Driving',
            narrative_key=None,
            lang='en',
        )
        # Without API key and no matching fallback, expect error
        assert 'error' in result
        assert result['narrative']['name'] == 'Autonomous Driving'
        assert result['narrative']['type'] == 'custom'

    @patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=False)
    def test_custom_concept_chinese(self):
        result = analyze_narrative(
            concept='自动驾驶',
            narrative_key=None,
            lang='zh',
        )
        assert result['narrative']['name'] == '自动驾驶'
