"""Measure dashboard filter lookups for a learner with 50 enrollments."""

from statistics import median
from time import perf_counter

import pytest
from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.db import connection
from django.test.utils import CaptureQueriesContext
from edx_django_utils.cache import RequestCache

from openedx_webhooks import filters


@pytest.mark.django_db(transaction=True)
def test_dashboard_lookup_benchmark():
    """Print median elapsed milliseconds and query counts over seven independent requests."""
    cases = (
        (filters.CourseAboutPageURLRequestedWebFilter, {'url': '/about'}),
        (filters.CourseHomeUrlCreationStartedWebFilter, {'course_home_url': '/home'}),
        (filters.CourseRunAPIRenderStartedWebFilter, {'serialized_courserun': {}}),
        (filters.CourseEnrollmentAPIRenderStartedWebFilter, {'serialized_enrollment': {}}),
    )
    for handler, data in cases:
        step = handler('', [])
        inputs = [dict(data, course_key=f'course-v1:org+course+{i}') for i in range(50)]
        for warm in (False, True):
            times = []
            counts = []
            for _ in range(7):
                cache.clear()
                RequestCache.clear_all_namespaces()
                if warm:
                    step.run_filter(**inputs[0])
                    RequestCache.clear_all_namespaces()
                request_started.send(sender=handler)
                with CaptureQueriesContext(connection) as queries:
                    start = perf_counter()
                    for entry in inputs:
                        step.run_filter(**entry)
                    times.append((perf_counter() - start) * 1000)
                request_finished.send(sender=handler)
                counts.append(len(queries))
            print(handler.__name__, 'warm' if warm else 'cold', counts, f'{median(times):.3f} ms')
