"""Check dashboard query budgets and optionally measure lookup timing.

Run the timing benchmark with:
OPENEDX_WEBHOOKS_BENCHMARK=1 pytest -s -o addopts= tests/test_dashboard_benchmark.py
"""

import os
from statistics import median
from time import perf_counter

import pytest
from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.db import connection
from django.test.utils import CaptureQueriesContext
from edx_django_utils.cache import RequestCache

from openedx_webhooks import filters


def dashboard_cases():
    """Supply representative inputs for 50 course enrollments."""
    keys = [f'course-v1:org+course+{i}' for i in range(50)]
    return (
        (filters.CourseAboutPageURLRequestedWebFilter, [{'url': f'/{key}/about', 'org': 'org'} for key in keys]),
        (filters.CourseHomeUrlCreationStartedWebFilter,
         [{'course_key': key, 'course_home_url': '/home'} for key in keys]),
        (filters.CourseRunAPIRenderStartedWebFilter, [{'serialized_courserun': {'key': key}} for key in keys]),
        (filters.CourseEnrollmentAPIRenderStartedWebFilter,
         [{'course_key': key, 'serialized_enrollment': {}} for key in keys]),
    )


def measure_request(handler, inputs, warm):
    """Return the database query count and elapsed milliseconds for one request."""
    step = handler('', [])
    cache.clear()
    RequestCache.clear_all_namespaces()
    if warm:
        step.run_filter(**inputs[0])
        RequestCache.clear_all_namespaces()
    request_started.send(sender=handler)
    try:
        with CaptureQueriesContext(connection) as queries:
            start = perf_counter()
            for entry in inputs:
                step.run_filter(**entry)
            elapsed = (perf_counter() - start) * 1000
    finally:
        request_finished.send(sender=handler)
    return len(queries), elapsed


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(('handler', 'inputs'), dashboard_cases())
@pytest.mark.parametrize('warm', [False, True])
def test_dashboard_lookup_query_budget(handler, inputs, warm):
    """Enforce one cold lookup and no warm lookups for 50 enrollments."""
    count, _ = measure_request(handler, inputs, warm)
    assert count == (0 if warm else 1)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not os.environ.get('OPENEDX_WEBHOOKS_BENCHMARK'), reason='Run timing explicitly')
def test_dashboard_lookup_timing():
    """Report median elapsed time over seven independent requests."""
    for handler, inputs in dashboard_cases():
        for warm in (False, True):
            results = [measure_request(handler, inputs, warm) for _ in range(7)]
            counts = [count for count, _ in results]
            times = [elapsed for _, elapsed in results]
            print(handler.__name__, 'warm' if warm else 'cold', counts, f'{median(times):.3f} ms')
