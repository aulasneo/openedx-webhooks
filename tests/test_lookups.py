"""Query budgets and transactional invalidation for delivery configuration."""

from unittest.mock import Mock, patch

from django.core.signals import request_finished, request_started
from django.db import transaction
from django.test import TestCase, TransactionTestCase

from openedx_webhooks.filters import CourseAboutPageURLRequestedWebFilter
from openedx_webhooks.lookups import get_active_endpoints
from openedx_webhooks.models import Webfilter, Webhook

EVENT = 'CourseAboutPageURLRequested'
URL = 'https://example.com/hook'


class DashboardLookupTests(TestCase):
    """Measure the whole pipeline step within and across requests."""

    def check_budget(self, enabled):
        """One cold SQL lookup supplies every enrollment and the next request."""
        if enabled:
            # Seed a committed-equivalent fixture without pending save callbacks
            # inside TestCase's wrapping transaction.
            Webfilter.objects.bulk_create([Webfilter(event=EVENT, webhook_url=URL)])
        step = CourseAboutPageURLRequestedWebFilter('', [])
        with patch('openedx_webhooks.filters.send', return_value=Mock(
            status_code=200, reason='OK', text='{"data":{"url":"/new"},"exception":{}}',
        )) as send:
            for budget in (1, 0):
                request_started.send(sender=type(self))
                try:
                    with self.assertNumQueries(budget):
                        result = step.run_filter(url='/old')
                    self.assertEqual(result, {'url': '/new'} if enabled else {})
                    with self.assertNumQueries(0), patch('openedx_webhooks.lookups.cache') as backend:
                        for _ in range(49):
                            self.assertEqual(step.run_filter(url='/old'), result)
                        self.assertFalse(backend.mock_calls)
                finally:
                    request_finished.send(sender=type(self))
        self.assertEqual(send.call_count, 100 if enabled else 0)

    def test_no_match(self):
        """Empty endpoint lists are cacheable."""
        self.check_budget(False)

    def test_match(self):
        """Delivery still happens for every enrollment."""
        self.check_budget(True)


class ConfigurationChangeTests(TransactionTestCase):
    """Use real commits and savepoints for both configuration models."""

    def test_edits(self):
        """Create, retarget, rename, disable, enable and delete within one request."""
        request_started.send(sender=type(self))
        self.addCleanup(request_finished.send, sender=type(self))
        for model in (Webfilter, Webhook):
            with self.subTest(model=model):
                self.assertFalse(get_active_endpoints(model, EVENT))
                config = model.objects.create(event=EVENT, webhook_url=URL)
                self.assertEqual(get_active_endpoints(model, EVENT)[0].webhook_url, URL)
                config.webhook_url += '/new'
                config.save()
                self.assertEqual(get_active_endpoints(model, EVENT)[0].webhook_url, config.webhook_url)
                config.event = 'other'
                config.save()
                self.assertFalse(get_active_endpoints(model, EVENT))
                self.assertTrue(get_active_endpoints(model, 'other'))
                config.enabled = False
                config.save()
                self.assertFalse(get_active_endpoints(model, 'other'))
                config.enabled = True
                config.save()
                self.assertTrue(get_active_endpoints(model, 'other'))
                config.delete()
                self.assertFalse(get_active_endpoints(model, 'other'))

    def test_savepoint_rollback(self):
        """Uncommitted writes are visible locally and never outlive rollback."""
        request_started.send(sender=type(self))
        self.addCleanup(request_finished.send, sender=type(self))
        with transaction.atomic():
            self.assertFalse(get_active_endpoints(Webfilter, EVENT))
            with transaction.atomic():
                Webfilter.objects.create(event=EVENT, webhook_url=URL)
                self.assertTrue(get_active_endpoints(Webfilter, EVENT))
                transaction.set_rollback(True)
            self.assertFalse(get_active_endpoints(Webfilter, EVENT))
        self.assertFalse(get_active_endpoints(Webfilter, EVENT))
