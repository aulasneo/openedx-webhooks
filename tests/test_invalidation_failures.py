"""Configuration saves remain successful when cache invalidation fails."""

from unittest.mock import Mock, patch

import pytest
from django.db import transaction

from openedx_webhooks.models import Webfilter, Webhook


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('model', [Webfilter, Webhook])
@pytest.mark.parametrize('atomic', [False, True])
def test_failed_invalidation_preserves_committed_write(model, atomic, caplog):
    """Cache failure is logged and does not prevent other commit callbacks."""
    after_commit = Mock()
    with patch('openedx_webhooks.lookups.cache.delete', side_effect=ConnectionError('cache unavailable')):
        if atomic:
            with transaction.atomic():
                config = model.objects.create(event='event', webhook_url='https://example.com/hook')
                transaction.on_commit(after_commit)
        else:
            config = model.objects.create(event='event', webhook_url='https://example.com/hook')
            transaction.on_commit(after_commit)
    assert model.objects.filter(pk=config.pk).exists()
    after_commit.assert_called_once()
    assert 'cache unavailable' in caplog.text
