"""
CMS Pluggable Django App settings.
"""


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

    if not hasattr(settings, 'OPEN_EDX_FILTERS_CONFIG'):
        return

    for key, filter_config in filters_config.items():
        if key in settings.OPEN_EDX_FILTERS_CONFIG:
            settings.OPEN_EDX_FILTERS_CONFIG[key]['pipeline'] += filter_config['pipeline']
        else:
            settings.OPEN_EDX_FILTERS_CONFIG[key] = filter_config
