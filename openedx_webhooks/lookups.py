"""Cache ordered delivery configuration for Open edX filters and events."""

from collections import namedtuple
from contextvars import ContextVar
from functools import partial
from uuid import uuid4

from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.db import connections, router, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Webfilter, Webhook

_TTL = 60
_PREFIX = 'openedx_webhooks.active.v1'
_request_entries = ContextVar('openedx_webhooks_request_entries', default=None)

FilterEndpoint = namedtuple('FilterEndpoint', (
    'event webhook_url use_www_form_encoding disable_filtering disable_halt '
    'halt_on_4xx redirect_on_4xx halt_on_5xx redirect_on_5xx '
    'halt_on_request_exception redirect_on_request_exception'
))
EventEndpoint = namedtuple('EventEndpoint', 'pk webhook_url use_www_form_encoding')
_ENDPOINTS = {Webfilter: FilterEndpoint, Webhook: EventEndpoint}


@receiver(request_started)
def _start_request(**kwargs):
    """Allocate a local tier only during an HTTP request."""
    _request_entries.set({})


@receiver(request_finished)
def _finish_request(**kwargs):
    """Release entries even on workers without the Open edX cache middleware."""
    _request_entries.set(None)


def _generation_key(model):
    return f'{_PREFIX}.{model._meta.model_name}.generation'


def _invalidate(model):
    entries = _request_entries.get()
    if entries is not None:
        entries.clear()
    # Rotate the whole model namespace so event renames cover the old key too.
    # An overlapping reader can only refill keys under its previous generation.
    cache.delete(_generation_key(model))


@receiver(post_save, sender=Webfilter)
@receiver(post_delete, sender=Webfilter)
@receiver(post_save, sender=Webhook)
@receiver(post_delete, sender=Webhook)
def _configuration_changed(sender, using, **kwargs):
    """Invalidate committed configuration and mark pending writes for local readers."""
    entries = _request_entries.get()
    if entries is not None:
        entries.clear()
    transaction.on_commit(partial(_invalidate, sender), using=using)


def _read_endpoints(model, event, alias):
    endpoint = _ENDPOINTS[model]
    rows = model.objects.using(alias).filter(enabled=True, event=event).order_by('pk').values_list(*endpoint._fields)
    return tuple(endpoint(*row) for row in rows)


def get_active_endpoints(model, event):
    """Read the ordered delivery fields, including caching the empty tuple on misses."""
    alias = router.db_for_read(model)
    connection = connections[alias]
    # Django drops on_commit callbacks when their savepoint rolls back. While
    # one of our invalidations is pending, only this transaction sees its writes.
    if connection.in_atomic_block and any(
        isinstance(callback, partial) and callback.func is _invalidate and callback.args == (model,)
        for _, callback, _ in connection.run_on_commit
    ):
        return _read_endpoints(model, event, alias)

    entries = _request_entries.get()
    local_key = (alias, model, event)
    if entries is not None and local_key in entries:
        return entries[local_key]

    generation = cache.get_or_set(_generation_key(model), uuid4, timeout=None)
    key = f'{_PREFIX}.{model._meta.model_name}.{alias}.{generation}.{event}'
    endpoints = cache.get(key)
    if endpoints is None:
        endpoints = _read_endpoints(model, event, alias)
        cache.set(key, endpoints, timeout=_TTL)
    if entries is not None:
        entries[local_key] = endpoints
    return endpoints
