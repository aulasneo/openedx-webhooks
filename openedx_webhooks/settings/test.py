"""
Test Pluggable Django App settings.
"""

from .common import plugin_settings as common_plugin_settings


def plugin_settings(settings):
    """Apply test settings using the common plugin configuration."""
    common_plugin_settings(settings)
