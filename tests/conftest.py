"""Keep configuration caches isolated across database fixtures."""

import pytest
from edx_django_utils.cache import RequestCache, TieredCache


@pytest.fixture(autouse=True)
def isolate_caches():
    """Clear the request caches and Django's backing cache around each test."""
    RequestCache.clear_all_namespaces()
    TieredCache.dangerous_clear_all_tiers()
    yield
    RequestCache.clear_all_namespaces()
    TieredCache.dangerous_clear_all_tiers()
