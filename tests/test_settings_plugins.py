"""
Tests for plugin settings helpers.
"""

from openedx_webhooks import receivers
from openedx_webhooks.apps import signals
from openedx_webhooks.settings import cms, common


class Settings:
    """Mutable settings stub."""

    OPEN_EDX_FILTERS_CONFIG = {}


def test_common_plugin_settings_registers_filters():
    """Common settings register Ulmo LMS filters."""
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


def test_ulmo_signal_catalog_includes_new_upstream_events():
    """Ulmo signal catalog includes the newly added upstream events."""
    assert "COURSE_RERUN_COMPLETED" in signals["content_authoring"]
    assert "LTI_PROVIDER_LAUNCH_SUCCESS" in signals["learning"]


def test_all_declared_signals_have_matching_receiver_exports():
    """Every declared signal is backed by a receiver function export."""
    for signal_group in signals.values():
        for signal_name in signal_group:
            receiver_name = f"{signal_name.lower()}_receiver"
            assert hasattr(receivers, receiver_name), receiver_name
