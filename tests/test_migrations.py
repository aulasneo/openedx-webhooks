"""Exercise upgrades of persisted Ulmo endpoint configuration."""

import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_verawood_migration_preserves_endpoints_and_corrects_aliases():
    """Historical rows retain their IDs, URLs, and controls after upgrading."""
    previous = [('openedx_webhooks', '0007_alter_webfilter_event')]
    target = [('openedx_webhooks', '0008_verawood')]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    try:
        old_model = executor.loader.project_state(previous).apps.get_model('openedx_webhooks', 'Webfilter')
        migration = importlib.import_module('openedx_webhooks.migrations.0008_verawood')
        records = []
        for old, new in migration.EVENT_ALIASES.items():
            record = old_model.objects.create(event=old, webhook_url='https://example.com/existing',
                                              disable_filtering=True, halt_on_4xx=True)
            records.append((record.pk, new))
        canonical = old_model.objects.create(
            event='AccountSettingsRenderStarted', webhook_url='https://example.com/valid',
        )
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        model = executor.loader.project_state(target).apps.get_model('openedx_webhooks', 'Webfilter')
        for pk, expected in records:
            record = model.objects.get(pk=pk)
            assert record.event == expected
            assert record.webhook_url == 'https://example.com/existing'
            assert record.disable_filtering and record.halt_on_4xx
        assert model.objects.get(pk=canonical.pk).event == 'AccountSettingsRenderStarted'
    finally:
        MigrationExecutor(connection).migrate(target)
