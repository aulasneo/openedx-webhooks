"""Exercise webhook delivery when the shared cache is unavailable."""

from unittest.mock import Mock, patch

import pytest
from django.core.signals import request_finished, request_started

from openedx_webhooks import filters, receivers
from openedx_webhooks.models import Webfilter, Webhook


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('operation', ['get_or_set', 'get', 'set'])
@pytest.mark.parametrize('configured', [False, True])
def test_cache_failure_falls_back_to_database(operation, configured):
    """Cache failures preserve both filter and signal delivery decisions."""
    if configured:
        Webfilter.objects.create(event='CourseAboutPageURLRequested', webhook_url='https://example.com/filter')
        Webhook.objects.create(event='ROLE_ASSIGNMENT_CREATED', webhook_url='https://example.com/event')
    step = filters.CourseAboutPageURLRequestedWebFilter('', [])
    response = Mock(status_code=200, reason='OK', text='{"data": {}, "exception": {}}')
    with patch(f'openedx_webhooks.lookups.cache.{operation}', side_effect=ConnectionError('cache unavailable')):
        with patch('openedx_webhooks.filters.send', return_value=response) as send_filter:
            with patch('openedx_webhooks.receivers.send', return_value=Mock()) as send_event:
                request_started.send(sender=test_cache_failure_falls_back_to_database)
                try:
                    step.run_filter(url='/about')
                    receivers.role_assignment_created_receiver('assignment')
                finally:
                    request_finished.send(sender=test_cache_failure_falls_back_to_database)
    assert send_filter.call_count == int(configured)
    assert send_event.call_count == int(configured)
