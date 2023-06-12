# coding=utf-8
"""
Admin settings for webhooks.

written by:     Andrés González
                https://aulasneo.com

date:           May 2023

usage:          register the custom Django models in LMS Django Admin
"""
import logging

from django.contrib import admin

from .models import Webfilter, Webhook

logger = logging.getLogger(__name__)


class WebhooksAdmin(admin.ModelAdmin):
    list_display = [f.name for f in Webhook._meta.get_fields()]


class WebfilterAdmin(admin.ModelAdmin):
    list_display = [
        'event',
        'webhook_url',
        'enabled',
        'disable_halt',
        'disable_filtering',
        'halt_on_4xx',
        'halt_on_5xx',
        'halt_on_request_exception',
    ]


logger.debug("Registering Webhook")
admin.site.register(Webhook, WebhooksAdmin)
admin.site.register(Webfilter, WebfilterAdmin)
