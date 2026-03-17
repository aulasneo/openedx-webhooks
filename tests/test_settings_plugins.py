"""
Tests for plugin settings helpers.
"""

from openedx_webhooks.settings import cms, common


class Settings:
    """Mutable settings stub."""

    OPEN_EDX_FILTERS_CONFIG = {}


def test_common_plugin_settings_registers_filters():
    """Common settings register Teak LMS filters."""
    settings = Settings()

    common.plugin_settings(settings)

    assert "org.openedx.learning.student.login.requested.v1" in settings.OPEN_EDX_FILTERS_CONFIG
    assert "org.openedx.learning.student.settings.render.started.v1" in settings.OPEN_EDX_FILTERS_CONFIG
    assert "org.openedx.learning.schedule.queryset.requested.v1" in settings.OPEN_EDX_FILTERS_CONFIG


def test_cms_plugin_settings_merges_existing_pipeline():
    """CMS settings append to an existing LMS page URL pipeline."""
    settings = Settings()
    settings.OPEN_EDX_FILTERS_CONFIG = {
        "org.openedx.content_authoring.lms.page.url.requested.v1": {
            "pipeline": ["existing.pipeline.Step"],
        },
    }

    cms.plugin_settings(settings)

    assert settings.OPEN_EDX_FILTERS_CONFIG["org.openedx.content_authoring.lms.page.url.requested.v1"][
        "pipeline"
    ] == [
        "existing.pipeline.Step",
        "openedx_webhooks.filters.LMSPageURLRequestedWebFilter",
    ]
