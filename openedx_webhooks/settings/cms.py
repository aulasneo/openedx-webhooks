"""
CMS Pluggable Django App settings.
"""

from .common import merge_filters


def plugin_settings(settings):
    """
    Declare CMS-safe filters and their handlers.
    """
    filters_config = {
        "org.openedx.content_authoring.lms.page.url.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.LMSPageURLRequestedWebFilter"
            ]
        },
    }

    merge_filters(settings, filters_config)
