"""
Tests for Shomei Light/Dark Theme Switcher Implementation
Verifies:
- Theme manager module (theme.js)
- Anti-FOUC script and controls in index.html and dashboard.html
- CSS tokens and dark mode overrides in style.css
- Fastapi endpoints render theme toggle markup
- Dark logo asset exists and conforms to specifications
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "code"))

import server
from server import app

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def client():
    return TestClient(app)


def test_theme_js_exists_and_implements_requirements():
    theme_js_path = BASE_DIR / "web" / "static" / "js" / "theme.js"
    assert theme_js_path.exists(), "web/static/js/theme.js must exist"

    content = theme_js_path.read_text(encoding="utf-8")
    # Must use localStorage key 'shomei_theme'
    assert "shomei_theme" in content
    # Must inspect system preference (prefers-color-scheme: dark)
    assert "prefers-color-scheme: dark" in content
    # Must set/toggle 'data-theme' attribute
    assert "data-theme" in content
    # Accessible naming
    assert "Switch to dark mode" in content
    assert "Switch to light mode" in content
    # Must expose global ShomeiTheme API
    assert "window.ShomeiTheme" in content
    # Must handle logo images
    assert "shomei_logo_dark.png" in content


def test_style_css_defines_centralized_theme_tokens():
    css_path = BASE_DIR / "web" / "static" / "css" / "style.css"
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")

    # Centralized tokens in :root
    assert "--bg-warm:" in content
    assert "--bg-card:" in content
    assert "--border-subtle:" in content
    assert "--text-primary:" in content
    assert "--green-primary:" in content
    assert "--header-bg:" in content

    # Centralized tokens in [data-theme="dark"]
    assert '[data-theme="dark"]' in content
    assert "--bg-warm: #121211;" in content
    assert "--bg-card: #1C1C1A;" in content
    assert "--text-primary: #F5F5F3;" in content

    # Toggle button styles and icons
    assert ".theme-toggle-btn" in content
    assert ".theme-icon-sun" in content
    assert ".theme-icon-moon" in content

    # Accessible keyboard focus
    assert ".theme-toggle-btn:focus-visible" in content


def test_dark_logo_asset_exists():
    dark_logo = BASE_DIR / "web" / "static" / "images" / "shomei_logo_dark.png"
    assert dark_logo.exists(), "Dark mode logo asset must exist"
    assert dark_logo.stat().st_size > 1000


def test_landing_page_renders_theme_toggle_and_anti_fouc(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Anti-FOUC script
    assert "localStorage.getItem('shomei_theme')" in html
    assert "data-theme" in html

    # Theme toggle button
    assert 'class="theme-toggle-btn"' in html
    assert 'id="theme-toggle"' in html
    assert 'aria-label="Switch to dark mode"' in html
    assert 'theme-icon-sun' in html
    assert 'theme-icon-moon' in html

    # Scripts
    assert '/static/js/theme.js' in html


def test_dashboard_renders_theme_toggle_and_anti_fouc(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    html = response.text

    # Anti-FOUC script
    assert "localStorage.getItem('shomei_theme')" in html
    assert "data-theme" in html

    # Theme toggle button
    assert 'class="theme-toggle-btn"' in html
    assert 'id="theme-toggle"' in html
    assert 'aria-label="Switch to dark mode"' in html
    assert 'theme-icon-sun' in html
    assert 'theme-icon-moon' in html

    # Scripts
    assert '/static/js/theme.js' in html


def test_system_graph_js_adapts_to_theme():
    graph_js = BASE_DIR / "web" / "static" / "js" / "system_graph.js"
    assert graph_js.exists()
    content = graph_js.read_text(encoding="utf-8")
    assert "data-theme" in content
    assert "isDark" in content
