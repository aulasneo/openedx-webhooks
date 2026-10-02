"""Exercise real Open edX signal dispatch and evolving event payloads."""

import json
from unittest.mock import Mock

import pytest
import requests
from opaque_keys.edx.keys import CourseKey
from openedx_events.authz import signals
from openedx_events.authz.data import RoleAssignmentData
from openedx_events.data import EventsMetadata
from openedx_events.learning.data import (
    CourseDiscussionConfigurationData,
    DiscussionThreadData,
    UserData,
    UserPersonalData,
)

from openedx_webhooks import receivers
from openedx_webhooks.models import Webhook

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('name', ['ROLE_ASSIGNMENT_CREATED', 'ROLE_ASSIGNMENT_DELETED'])
@pytest.mark.parametrize('form_encoded', [False, True])
def test_authz_signal_dispatch(name, form_encoded, monkeypatch, caplog):
    """Actual upstream events reach configured URLs in the established payload envelope."""
    Webhook.objects.create(event=name, webhook_url='https://example.com/hook', use_www_form_encoding=form_encoded)
    post = Mock(return_value=Mock())
    monkeypatch.setattr('openedx_webhooks.utils.requests.post', post)
    signal = getattr(signals, name)
    receiver = getattr(receivers, f'{name.lower()}_receiver')
    operation = name.rsplit('_', 1)[1].lower()
    assignment = RoleAssignmentData(operation=operation, subject='user^learner', role='course_admin',
                                    scope='course-v1:edX+DemoX+Demo', actor_id=4)
    signal.connect(receiver)
    try:
        with caplog.at_level('INFO'):
            signal.send_event(send_robust=False, role_assignment=assignment)
    finally:
        signal.disconnect(receiver)
    post.assert_called_once()
    body = post.call_args.kwargs['data']
    if form_encoded:
        assert body['openedx_events.authz.data.RoleAssignmentData_subject'] == 'user^learner'
        assert body['openedx_events.authz.data.RoleAssignmentData_operation'] == operation
        assert body['event_metadata_event_type'] == signal.event_type
    else:
        payload = json.loads(body)
        assert payload['openedx_events.authz.data.RoleAssignmentData']['actor_id'] == 4
        assert payload['openedx_events.authz.data.RoleAssignmentData']['operation'] == operation
        assert payload['event_metadata']['event_type'] == signal.event_type
        assert isinstance(payload['event_metadata']['id'], str)
    assert 'user^learner' not in caplog.text


@pytest.mark.parametrize('failure', [
    requests.Timeout('read timed out'),
    requests.ConnectionError('connection refused'),
    requests.HTTPError('503 Service Unavailable'),
])
def test_delivery_failure_does_not_skip_other_subscribers(monkeypatch, failure, caplog):
    """A failed delivery neither raises into the caller nor skips later configured URLs."""
    webhooks = [
        Webhook.objects.create(event='ROLE_ASSIGNMENT_CREATED', webhook_url=f'https://example.com/{suffix}')
        for suffix in ('first', 'second')
    ]
    if isinstance(failure, requests.HTTPError):
        send = Mock(side_effect=[Mock(raise_for_status=Mock(side_effect=failure)), Mock()])
    else:
        send = Mock(side_effect=[failure, Mock()])
    monkeypatch.setattr(receivers, 'send', send)
    receivers.role_assignment_created_receiver(RoleAssignmentData('created', 'user^1', 'admin', 'course'))
    assert send.call_count == 2
    assert send.call_args.args[0] == 'https://example.com/second'
    assert f'configuration {webhooks[0].pk}' in caplog.text
    assert type(failure).__name__ in caplog.text
    assert str(failure) in caplog.text
    assert 'user^1' not in caplog.text


def test_disabled_webhooks_do_not_send(monkeypatch):
    """Disabled configurations produce no HTTP requests."""
    Webhook.objects.create(event='ROLE_ASSIGNMENT_CREATED', webhook_url='https://example.com/hook', enabled=False)
    send = Mock()
    monkeypatch.setattr(receivers, 'send', send)
    receivers.role_assignment_created_receiver(RoleAssignmentData('created', 'user^1', 'admin', 'course'))
    send.assert_not_called()


def test_discussion_enabled_and_nested_context_are_preserved(monkeypatch):
    """The new enabled field is forwarded without altering the existing wire format."""
    Webhook.objects.create(event='COURSE_DISCUSSIONS_CHANGED', webhook_url='https://example.com/hook')
    send = Mock(return_value=Mock())
    monkeypatch.setattr(receivers, 'send', send)
    data = CourseDiscussionConfigurationData(
        course_key=CourseKey.from_string('course-v1:edX+DemoX+Demo'), provider_type='openedx',
        enabled=False, plugin_configuration={'allow_anonymous': False},
    )
    receivers.course_discussions_changed_receiver(data, metadata=EventsMetadata('discussion.changed'))
    payload = send.call_args.args[1]['openedx_events.learning.data.CourseDiscussionConfigurationData']
    assert payload['enabled'] is False
    assert payload['plugin_configuration'] == {'allow_anonymous': False}
    assert payload['course_key'] == 'course-v1:edX+DemoX+Demo'


def test_forum_string_id_nullable_fields_and_nested_user(monkeypatch):
    """Verawood string IDs and optional forum fields survive serialization."""
    Webhook.objects.create(event='FORUM_THREAD_CREATED', webhook_url='https://example.com/hook')
    send = Mock(return_value=Mock())
    monkeypatch.setattr(receivers, 'send', send)
    user = UserData(id=1, is_active=True, pii=UserPersonalData(username='learner', email='learner@example.com'))
    thread = DiscussionThreadData(
        body='post', commentable_id='discussion', id='thread-1', truncated=False,
        url='/discussion/thread-1', user=user,
        course_id=CourseKey.from_string('course-v1:edX+DemoX+Demo'),
    )
    receivers.forum_thread_created_receiver(thread)
    payload = send.call_args.args[1]['openedx_events.learning.data.DiscussionThreadData']
    assert payload['id'] == 'thread-1'
    assert payload['discussion'] is None
    assert payload['user']['pii']['email'] == 'learner@example.com'
