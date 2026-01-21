"""Tests for setup wizard functionality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
import json
from unittest.mock import patch, MagicMock
from setup import load_sources, save_sources, get_default_sources


def test_load_sources_missing_file(tmp_path, monkeypatch):
    """Test loading non-existent sources returns defaults."""
    sources_file = tmp_path / "sources.json"
    monkeypatch.setattr("setup.Path", lambda *args: sources_file)
    
    # get_default_sources should be called
    sources = get_default_sources()
    
    assert isinstance(sources, dict)
    assert len(sources) > 0  # Should have some default sources


def test_save_sources(tmp_path, monkeypatch):
    """Test saving sources to JSON."""
    sources_file = tmp_path / "sources.json"
    
    sources = {
        "yahoo": {"enabled": True, "rss": "https://example.com/rss"},
        "cnbc": {"enabled": False}
    }
    
    with patch("setup.Path", return_value=sources_file):
        save_sources(sources)
    
    assert sources_file.exists()
    with open(sources_file) as f:
        saved = json.load(f)
    
    assert saved["yahoo"]["enabled"] is True
    assert saved["cnbc"]["enabled"] is False


def test_get_default_sources():
    """Test default sources structure."""
    sources = get_default_sources()
    
    assert isinstance(sources, dict)
    # Should have common sources
    assert any("yahoo" in k.lower() or "cnbc" in k.lower() or "marketwatch" in k.lower() 
               for k in sources.keys())


@patch("setup.prompt", side_effect=["en"])
@patch("setup.save_sources")
def test_setup_language(mock_save, mock_prompt):
    """Test language setup function."""
    from setup import setup_language
    
    sources = {"config": {}}
    setup_language(sources)
    
    # Should have called prompt
    mock_prompt.assert_called()
    # Should have saved
    mock_save.assert_called_once()


@patch("setup.prompt_bool", return_value=True)
@patch("setup.save_sources")
def test_setup_markets(mock_save, mock_prompt):
    """Test markets setup function."""
    from setup import setup_markets
    
    sources = {
        "us_source": {"enabled": False},
        "eu_source": {"enabled": False}
    }
    setup_markets(sources)
    
    # Should have prompted
    assert mock_prompt.called
    # Should have saved
    mock_save.assert_called_once()
