"""
Models for Webhooks.

written by:     Andrés González
                https://aulasneo.com

date:           May 2023

usage:          Django models for Open edX signals webhooks
"""

from django.db import models
from django.utils.translation import gettext as _
from model_utils.models import TimeStampedModel

from .apps import signals
from .settings.common import plugin_settings


# From https://github.com/openedx/edx-platform/blob/master/docs/guides/hooks/filters.rst#index-of-filters
class Fake_settings:
    OPEN_EDX_FILTERS_CONFIG = {}


fake_settings = Fake_settings()

plugin_settings(fake_settings)

filters = fake_settings.OPEN_EDX_FILTERS_CONFIG


class Webhook(TimeStampedModel):
    """
    Configuration model to set the webhook url for each event.

    .. no_pii:
    """

    signal_list = []
    for signal_app, signal_app_list in signals.items():
        signal_list += signal_app_list

    # Create a set of pairs like ("COURSE_ENROLLMENT_CREATED", "Course enrollment created")...
    event_list = (
        (signal,
         signal.capitalize().replace("_", " ")) for signal in signal_list
    )

    event = models.CharField(
        max_length=50,
        blank=False,
        primary_key=False,
        choices=event_list,
        default='',
        unique=False,
        help_text=_("Event type"),
    )

    webhook_url = models.URLField(
        max_length=255,
        blank=False,
        help_text=_("URL to call when the event is triggered")
    )

    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled")
    )

    use_www_form_encoding = models.BooleanField(
        default=False,
        verbose_name=_("Use WWW form encoding"),
        help_text=_("When enabled, data will be sent in form format, instead of JSON")
    )

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return f'Webhook for {self.event} to {self.webhook_url}'


class Webfilter(TimeStampedModel):
    """
    Configuration model to set the filter url for each event.

    .. no_pii:
    """

    filter_list = [
        (''.join(list(map(str.capitalize, filter.replace('_', '.').split('.')[3:-1]))),
         ' '.join(list(map(str.capitalize, filter.replace('_', '.').split('.')[3:-1]))),)
        for filter in filters
    ]

    description = models.TextField(
        help_text="Description",
        blank=True,
        default='',
    )

    event = models.CharField(
        max_length=50,
        blank=False,
        primary_key=False,
        choices=filter_list,
        default='',
        unique=False,
        help_text=_("Event type"),
    )

    webhook_url = models.URLField(
        max_length=255,
        blank=False,
        help_text=_("URL to call when the event is triggered")
    )

    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled")
    )

    disable_filtering = models.BooleanField(
        default=False,
        verbose_name=_("Disable Filtering"),
        help_text=_("Do not update the data with the response of the webhook call.")
    )

    disable_halt = models.BooleanField(
        default=False,
        verbose_name=_("Disable halting"),
        help_text=_("Don't stop the process even if the response includes exception data.")
    )

    halt_on_4xx = models.BooleanField(
        default=False,
        verbose_name=_("Halt on 4xx"),
        help_text=_("Halt the process if the server returns a status response of 4xx (client error).")
    )

    redirect_on_4xx = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("URL to redirect on result code 4xx (client error)")
    )

    halt_on_5xx = models.BooleanField(
        default=False,
        verbose_name=_("Halt on 5xx"),
        help_text=_("Halt the process if the server returns a status response of 5xx (server error).")
    )

    redirect_on_5xx = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("URL to redirect on result code 5XX (server error)")
    )

    halt_on_request_exception = models.BooleanField(
        default=False,
        verbose_name=_("Halt on request exception"),
        help_text=_("Halt the process if the server doesn't response or there is an exception sending the request.")
    )

    redirect_on_request_exception = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("URL to redirect on request exception")
    )

    use_www_form_encoding = models.BooleanField(
        default=False,
        verbose_name=_("Use WWW form encoding"),
        help_text=_("When enabled, data will be sent in form format, instead of JSON")
    )

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return f'Webhook filter for {self.event} to {self.webhook_url}'
