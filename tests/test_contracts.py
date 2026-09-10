"""Validate registration against the installed Verawood upstream contracts."""

import importlib
import inspect
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.utils.module_loading import import_string
from opaque_keys.edx.keys import CourseKey
from openedx_events.tooling import OpenEdxPublicSignal
from openedx_filters.tooling import OpenEdxPublicFilter

from openedx_webhooks import filters as handlers
from openedx_webhooks import receivers
from openedx_webhooks.apps import WebhooksConfig, signals
from openedx_webhooks.models import Webfilter
from openedx_webhooks.settings.cms import plugin_settings as studio_settings
from openedx_webhooks.settings.common import plugin_settings


def upstream_filters():
    """Find all public learning and content-authoring filter classes."""
    result = {}
    for domain in ('learning', 'content_authoring'):
        module = importlib.import_module(f'openedx_filters.{domain}.filters')
        for value in vars(module).values():
            if inspect.isclass(value) and issubclass(value, OpenEdxPublicFilter) and value is not OpenEdxPublicFilter:
                result[value.filter_type] = value
    return result


@pytest.mark.django_db
def test_all_upstream_filters_are_registered_and_noop_through_real_pipeline(settings):
    """Every public filter has a loadable step that preserves inputs without endpoints."""
    settings.OPEN_EDX_FILTERS_CONFIG = {}
    plugin_settings(settings)
    upstream = upstream_filters()
    assert set(upstream) == set(settings.OPEN_EDX_FILTERS_CONFIG)
    choices = dict(Webfilter._meta.get_field('event').choices)
    for filter_type, config in settings.OPEN_EDX_FILTERS_CONFIG.items():
        handler = import_string(config['pipeline'][0])
        event = handler.__name__.removesuffix('WebFilter')
        assert event in choices
        parameters = inspect.signature(upstream[filter_type].run_filter).parameters
        inputs = {name: None for name in parameters}
        inspect.signature(handler.run_filter).bind(None, **inputs)
        step = handler(filter_type=filter_type, running_pipeline=[])
        assert step.run_filter(**inputs) == {}
        # The runner must retain the original inputs when our step has nothing to do.
        assert upstream[filter_type].run_pipeline(**inputs) == inputs


@pytest.mark.parametrize('domain', signals)
def test_all_signals_match_upstream_payload_names(domain, monkeypatch):
    """Every receiver accepts all named payloads emitted by its actual upstream signal."""
    module = importlib.import_module(f'openedx_events.{domain}.signals')
    upstream = {name for name, value in vars(module).items() if isinstance(value, OpenEdxPublicSignal)}
    assert set(signals[domain]) == upstream
    process = Mock()
    monkeypatch.setattr(receivers, '_process_event', process)
    for name in signals[domain]:
        event = getattr(module, name)
        payload = {key: object() for key in event.init_data}
        metadata = object()
        getattr(receivers, f'{name.lower()}_receiver')(**payload, metadata=metadata)
        process.assert_called_with(name, *payload.values(), metadata=metadata)


def test_studio_includes_authoring_and_authz_receivers():
    """Studio receives authorization lifecycle events as well as authoring events."""
    registered = WebhooksConfig.plugin_app['signals_config']['cms.djangoapp']['receivers']
    assert len(registered) == len(signals['content_authoring']) + len(signals['authz'])
    for config in registered:
        assert callable(import_string(f"openedx_webhooks.receivers.{config['receiver_func_name']}"))
        assert isinstance(import_string(config['signal_path']), OpenEdxPublicSignal)


def test_studio_filter_can_be_imported_without_platform_modules():
    """The Studio entry point is usable with no LMS packages installed or mocked."""
    settings = SimpleNamespace()
    studio_settings(settings)
    for config in settings.OPEN_EDX_FILTERS_CONFIG.values():
        assert import_string(config['pipeline'][0])


@pytest.mark.django_db
@pytest.mark.parametrize('filter_type', upstream_filters())
def test_enabled_filter_executes_with_upstream_arguments(filter_type, settings, monkeypatch):
    """Exercise each enabled handler with realistic inputs and an unchanged remote response."""
    settings.OPEN_EDX_FILTERS_CONFIG = {}
    plugin_settings(settings)
    path = settings.OPEN_EDX_FILTERS_CONFIG[filter_type]['pipeline'][0]
    Webfilter.objects.create(event=import_string(path).__name__.removesuffix('WebFilter'),
                             webhook_url='https://example.com/hook')
    send = Mock(return_value=Mock(status_code=200, reason='OK', text='{"data": {}, "exception": {}}'))
    monkeypatch.setattr(handlers, 'send', send)
    user = get_user_model().objects.create(username='learner')
    user.profile = SimpleNamespace(name='Learner')
    monkeypatch.setattr(handlers, 'get_user_model', lambda: SimpleNamespace(objects=Mock(get=Mock(return_value=user))))
    monkeypatch.setattr(handlers, 'get_course_blocks_completion_summary', lambda *args: {'complete_count': 1})
    monkeypatch.setitem(sys.modules, 'common.djangoapps.student.models', SimpleNamespace(
        UserProfile=SimpleNamespace(LEVEL_OF_EDUCATION_CHOICES=[], GENDER_CHOICES=[]),
    ))
    course_key = CourseKey.from_string('course-v1:edX+DemoX+Demo')
    context = {'course_id': str(course_key), 'accomplishment_user_id': user.pk,
               'course': SimpleNamespace(id=course_key), 'course_details': SimpleNamespace(overview='course')}
    values = {
        'user': user, 'user_id': user.pk, 'course_id': str(course_key), 'course_key': course_key,
        'context': context, 'template_name': 'template.html', 'form_data': QueryDict('name=Learner'),
        'enrollment': SimpleNamespace(user=user), 'mode': 'audit', 'status': 'downloadable',
        'grade': 0.8, 'generation_mode': 'self', 'custom_template': None,
        'current_membership': SimpleNamespace(user_id=user.pk, course_id=course_key),
        'target_cohort': SimpleNamespace(course_id=course_key), 'block': SimpleNamespace(),
        'enrollments': get_user_model().objects.all(), 'schedules': get_user_model().objects.all(),
        'student_view_context': {}, 'fragment': SimpleNamespace(), 'view': 'student_view',
        'course_home_url': '/course', 'serialized_enrollment': {}, 'serialized_courserun': {},
        'tabs': [{'tab_id': 'course_info'}], 'url': '/page', 'org': 'edX', 'readonly_fields': {'username'},
    }
    upstream = upstream_filters()[filter_type]
    inputs = {name: values[name] for name in inspect.signature(upstream.run_filter).parameters}
    result = upstream.run_pipeline(**inputs)
    send.assert_called_once()
    for name, original in inputs.items():
        if name in ('schedules', 'enrollments'):
            assert list(result[name]) == list(original)
        else:
            assert result[name] == original
