"""Cache ordered delivery configuration for Open edX filters and events."""

import logging
from collections import namedtuple
from contextvars import ContextVar
from uuid import uuid4

from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.db import connections, router, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Admin saves and deletes invalidate on commit. Expiry is a fallback.
_TTL = 24 * 60 * 60
_PREFIX = 'openedx_webhooks.active.v1'
_request_entries = ContextVar('openedx_webhooks_request_entries', default=None)

FilterEndpoint = namedtuple('FilterEndpoint', (
    'event webhook_url use_www_form_encoding disable_filtering disable_halt '
    'halt_on_4xx redirect_on_4xx halt_on_5xx redirect_on_5xx '
    'halt_on_request_exception redirect_on_request_exception'
))
EventEndpoint = namedtuple('EventEndpoint', 'pk webhook_url use_www_form_encoding')
_FILTER = 'openedx_webhooks.Webfilter'
_HOOK = 'openedx_webhooks.Webhook'
_ENDPOINTS = {_FILTER: FilterEndpoint, _HOOK: EventEndpoint}


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


class _PendingChange:
    """Keep reads of uncommitted configuration scoped to the writing savepoint."""

    def __init__(self, model):
        self.model = model
        self.entries = {}
        # Django uses this attribute when logging failures of robust callbacks.
        self.__qualname__ = type(self).__qualname__

    def __call__(self):
        """Invalidate both tiers after commit, including keys for renamed events."""
        entries = _request_entries.get()
        if entries is not None:
            entries.clear()
        # An overlapping reader can only refill keys under its previous generation.
        cache.delete(_generation_key(self.model))


@receiver(post_save, sender=_FILTER)
@receiver(post_delete, sender=_FILTER)
@receiver(post_save, sender=_HOOK)
@receiver(post_delete, sender=_HOOK)
def _configuration_changed(sender, using, **kwargs):
    """Invalidate committed configuration and mark pending writes for local readers."""
    entries = _request_entries.get()
    if entries is not None:
        entries.clear()
    transaction.on_commit(_PendingChange(sender), using=using, robust=True)


def _read_rows(model, event, alias):
    fields = _ENDPOINTS[model._meta.label]._fields
    return tuple(model.objects.using(alias).filter(enabled=True, event=event).order_by('pk').values_list(*fields))


def _endpoints(model, rows):
    endpoint = _ENDPOINTS[model._meta.label]
    return tuple(endpoint(*row) for row in rows)


def get_active_endpoints(model, event):
    """Read the ordered delivery fields, including caching the empty tuple on misses."""
    alias = router.db_for_read(model)
    connection = connections[alias]
    # Django drops on_commit callbacks when their savepoint rolls back. While
    # one of our invalidations is pending, only this transaction sees its writes.
    if connection.in_atomic_block:
        for _, callback, _ in reversed(connection.run_on_commit):
            if isinstance(callback, _PendingChange) and callback.model is model:
                if event not in callback.entries:
                    callback.entries[event] = _endpoints(model, _read_rows(model, event, alias))
                return callback.entries[event]

    entries = _request_entries.get()
    local_key = (alias, model, event)
    if entries is not None and local_key in entries:
        return entries[local_key]

    try:
        generation = cache.get_or_set(_generation_key(model), lambda: uuid4().hex, timeout=None)
        key = f'{_PREFIX}.{model._meta.model_name}.{alias}.{generation}.{event}'
        rows = cache.get(key)
    except Exception:  # pylint: disable=broad-except
        logger.exception('Unable to read webhook configuration cache')
        key = None
        rows = None
    if rows is None:
        rows = _read_rows(model, event, alias)
        if key is not None:
            try:
                cache.set(key, rows, timeout=_TTL)
            except Exception:  # pylint: disable=broad-except
                logger.exception('Unable to write webhook configuration cache')
    endpoints = _endpoints(model, rows)
    if entries is not None:
        entries[local_key] = endpoints
    return endpoints
