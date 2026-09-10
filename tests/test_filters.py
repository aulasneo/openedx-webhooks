"""Exercise filter pipelines, remote response handling, and model protection."""
# Pytest injects fixtures by name; helper tests intentionally cover private functions.
# pylint: disable=redefined-outer-name,protected-access

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.utils import timezone
from opaque_keys.edx.keys import CourseKey
from openedx_filters.learning.filters import (
    AccountSettingsReadOnlyFieldsRequested,
    AccountSettingsRenderStarted,
    CourseEnrollmentStarted,
    GradeEventContextRequested,
    InstructorDashboardRenderStarted,
    InstructorDashboardTabsRequested,
    StudentLoginRequested,
    StudentRegistrationRequested,
)

from openedx_webhooks import filters
from openedx_webhooks.models import Webfilter
from openedx_webhooks.settings.common import plugin_settings

pytestmark = pytest.mark.django_db


@pytest.fixture
def endpoint():
    """Create a real enabled filter configuration."""
    return Webfilter.objects.create(event='InstructorDashboardTabsRequested', webhook_url='https://example.com/hook')


@pytest.fixture
def response(monkeypatch):
    """Mock the network boundary while exercising serialization and pipeline behavior."""
    result = Mock(status_code=200, reason='OK', text='{}')
    send = Mock(return_value=result)
    monkeypatch.setattr(filters, 'send', send)
    return result, send


@pytest.fixture
def configured(settings):
    """Enable the actual upstream runner with our registered steps."""
    settings.OPEN_EDX_FILTERS_CONFIG = {}
    plugin_settings(settings)


@pytest.mark.usefixtures('configured', 'endpoint')
def test_tabs_preserve_objects_and_allow_empty_list(response):
    """JSON may replace tabs but cannot replace the Django user or opaque course key."""
    result, send = response
    result.text = json.dumps({'data': {'tabs': [], 'user': {'id': 9}, 'course_key': 'invalid'}})
    user = get_user_model()(username='teacher', password='secret hash')
    key = CourseKey.from_string('course-v1:edX+DemoX+Demo')
    tabs, actual_user, actual_key = InstructorDashboardTabsRequested.run_filter(
        tabs=[{'tab_id': 'course_info'}], user=user, course_key=key,
    )
    assert tabs == []
    assert actual_user is user
    assert actual_key is key
    assert 'password' not in send.call_args.args[1]['user']


@pytest.mark.usefixtures('configured', 'endpoint')
def test_tabs_exception(response):
    """The new upstream exception carries a custom tabs list."""
    response[0].text = json.dumps({'exception': {'PreventTabsGeneration': {'message': 'hidden', 'tabs': []}}})
    with pytest.raises(InstructorDashboardTabsRequested.PreventTabsGeneration) as caught:
        InstructorDashboardTabsRequested.run_filter(tabs=[], user=None, course_key=None)
    assert caught.value.tabs == []


@pytest.mark.usefixtures('configured')
def test_readonly_fields_remain_a_set_and_cannot_be_removed(endpoint, response):
    """A remote response only adds restrictions and preserves the original user."""
    endpoint.event = 'AccountSettingsReadOnlyFieldsRequested'
    endpoint.save()
    response[0].text = json.dumps({'data': {'readonly_fields': ['name', 'email'], 'user': {}}})
    user = object()
    original = {'username'}
    fields, actual_user = AccountSettingsReadOnlyFieldsRequested.run_filter(readonly_fields=original, user=user)
    assert fields == {'username', 'name', 'email'}
    assert original == {'username'}
    assert actual_user is user


@pytest.mark.usefixtures('configured')
def test_grade_context_merges_without_replacing_identity(endpoint, response):
    """Enrichment retains existing context and the platform's identifiers."""
    endpoint.event = 'GradeEventContextRequested'
    endpoint.save()
    response[0].text = json.dumps({'data': {'context': {'source': 'crm'}, 'user_id': 99}})
    context = {'grade': 0.8}
    assert GradeEventContextRequested.run_filter(context=context, user_id=1, course_id='course') == (
        {'grade': 0.8, 'source': 'crm'}, 1, 'course',
    )
    assert context == {'grade': 0.8}


@pytest.mark.parametrize('body', ['null', '[]', 'true', '123', '"text"', '<html>Error</html>'])
def test_non_object_responses_are_ignored(endpoint, response, body):
    """Malformed or scalar responses cannot crash a platform request."""
    response[0].text = body
    assert filters._process_filter([endpoint], {}) == ({}, {})


@pytest.mark.parametrize('exception_class', [
    CourseEnrollmentStarted.PreventEnrollment,
    AccountSettingsRenderStarted.RedirectToPage,
    InstructorDashboardTabsRequested.PreventTabsGeneration,
    StudentRegistrationRequested.PreventRegistration,
])
@pytest.mark.parametrize('failure', ['timeout', '4xx', '5xx'])
def test_transport_halting_uses_actual_exception_signatures(endpoint, response, exception_class, failure):
    """Halting never fails with TypeError from unsupported redirect/status arguments."""
    if failure == 'timeout':
        endpoint.halt_on_request_exception = True
        response[1].side_effect = requests.Timeout('connection timed out')
    else:
        setattr(endpoint, f'halt_on_{failure}', True)
        response[0].status_code = 403 if failure == '4xx' else 503
    with pytest.raises(exception_class) as caught:
        filters._process_filter([endpoint], {}, exception=exception_class)
    assert str(caught.value)


def test_non_halting_timeout_continues_to_next_endpoint(endpoint, response):
    """One failing endpoint does not discard successful subsequent results."""
    response[0].text = '{"data": {"tabs": []}}'
    response[1].side_effect = [requests.Timeout('down'), response[0]]
    assert filters._process_filter([endpoint, endpoint], {}) == ({'tabs': []}, {})


def test_disable_flags_and_response_merging(endpoint, response):
    """Data and exception controls are independent and later endpoint values win."""
    response[0].text = '{"data": {"value": 1}, "exception": {"PreventLogin": "blocked"}}'
    endpoint.disable_filtering = True
    endpoint.disable_halt = True
    assert filters._process_filter([endpoint], {}) == ({}, {})
    endpoint.disable_filtering = False
    endpoint.disable_halt = False
    response[1].side_effect = [response[0], Mock(status_code=200, reason='OK', text='{"data": {"value": 2}}')]
    assert filters._process_filter([endpoint, endpoint], {}) == ({'value': 2}, {'PreventLogin': 'blocked'})


@pytest.mark.parametrize('upstream', [AccountSettingsRenderStarted, InstructorDashboardRenderStarted])
def test_custom_response_is_an_http_response(upstream):
    """Legacy account and instructor hooks receive an HttpResponse, not a dict."""
    with pytest.raises(upstream.RenderCustomResponse) as caught:
        filters._check_for_exception({'RenderCustomResponse': {'content': 'custom', 'status': 202}},
                                     upstream.RenderCustomResponse)
    assert caught.value.response.content == b'custom'
    assert caught.value.response.status_code == 202


@pytest.mark.parametrize(('handler', 'key'), [
    (filters.CourseEnrollmentQuerysetRequestedWebFilter, 'enrollments'),
    (filters.ScheduleQuerySetRequestedWebFilter, 'schedules'),
])
def test_queryset_filter_serializes_rows_and_returns_filtered_queryset(endpoint, response, handler, key):
    """Remote lookup mappings must be unpacked and applied to the original QuerySet."""
    endpoint.event = handler.__name__.removesuffix('WebFilter')
    endpoint.save()
    selected = get_user_model().objects.create(username='selected')
    get_user_model().objects.create(username='other')
    response[0].text = '{"data": {"filter": {"username": "selected"}}}'
    step = handler(filter_type='', running_pipeline=[])
    output = step.run_filter(**{key: get_user_model().objects.all()})
    assert list(output[key]) == [selected]
    assert isinstance(response[1].call_args.args[1][key], list)


def test_model_updates_cannot_change_identity_privileges_or_credentials():
    """Remote updates may change profile fields but cannot grant account privileges."""
    user = get_user_model().objects.create(username='original', password='original hash')
    original_id = user.pk
    filters.update_model(user, {
        'id': 900, 'pk': 900, 'password': 'replacement', 'is_superuser': True,
        'is_staff': True, 'first_name': 'Changed', 'unknown': 'ignored', 'date_joined': None,
    })
    user.refresh_from_db()
    assert user.pk == original_id
    assert user.password == 'original hash'
    assert not user.is_staff and not user.is_superuser
    assert user.first_name == 'Changed'
    assert user.date_joined is not None


def test_generic_model_updates_preserve_protected_fields():
    """In-memory cohort/user updates obey the same model protections as saved updates."""
    user = get_user_model()(id=1, username='learner', password='hash', is_active=True)
    filters.update_object(user, {'id': 9, 'password': 'new', 'is_active': False, 'first_name': 'Changed'})
    assert user.id == 1 and user.password == 'hash' and user.is_active
    assert user.first_name == 'Changed'


def test_prevent_login_does_not_persist_remote_updates(endpoint, response):
    """A response that denies login cannot first modify the stored user."""
    endpoint.event = 'StudentLoginRequested'
    endpoint.save()
    user = get_user_model().objects.create(username='learner', first_name='Original')
    user.profile = SimpleNamespace(name='Learner')
    response[0].text = json.dumps({
        'data': {'user': {'first_name': 'Changed'}}, 'exception': {'PreventLogin': 'denied'},
    })
    with pytest.raises(StudentLoginRequested.PreventLogin):
        filters.StudentLoginRequestedWebFilter('', []).run_filter(user=user)
    user.refresh_from_db()
    assert user.first_name == 'Original'


def test_query_dict_replaces_values_and_preserves_password():
    """Response edits replace form fields without modifying credential fields."""
    original = QueryDict('name=old&password=secret')
    result = filters.update_query_dict(original, {'name': 'new', 'password': 'changed'})
    assert result.getlist('name') == ['new']
    assert result['password'] == 'secret'
    assert original['name'] == 'old'


@pytest.mark.parametrize('value', [True, False, 'true', 'false'])
def test_object_updates_accept_json_booleans(value):
    """JSON booleans need no string-only lower() call."""
    instance = SimpleNamespace(active=False)
    filters.update_object(instance, {'active': value})
    assert instance.active is (str(value).lower() == 'true')


def test_nested_serialization_redacts_credentials(endpoint, response):
    """Nested models serialize structurally without leaking password hashes."""
    user = get_user_model()(username='learner', password='sensitive')
    filters._process_filter([endpoint], {'context': {'user': user, 'password': 'secret'}})
    payload = response[1].call_args.args[1]
    assert payload['context']['user']['username'] == 'learner'
    assert 'password' not in payload['context']['user']
    assert 'password' not in payload['context']
    assert timezone.is_aware(timezone.datetime.fromisoformat(payload['event_metadata']['time']))


def test_registration_never_logs_or_sends_password(endpoint, response, monkeypatch, caplog):
    """Only the platform profile choice constants are stubbed for standalone tests."""
    module = SimpleNamespace(UserProfile=SimpleNamespace(LEVEL_OF_EDUCATION_CHOICES=[], GENDER_CHOICES=[]))
    monkeypatch.setitem(sys.modules, 'common.djangoapps.student.models', module)
    endpoint.event = 'StudentRegistrationRequested'
    endpoint.save()
    response[0].text = '{"data": {"form_data": {"name": "changed", "password": "injected"}}}'
    form = QueryDict('name=old&password=super-secret-password')
    with caplog.at_level('INFO'):
        output = filters.StudentRegistrationRequestedWebFilter('', []).run_filter(form_data=form)
    assert output['form_data']['password'] == 'super-secret-password'
    assert output['form_data']['name'] == 'changed'
    assert 'password' not in response[1].call_args.args[1]
    assert 'super-secret-password' not in caplog.text
