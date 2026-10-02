"""
Tests for the `openedx_webhooks.utils` module.
"""

import json
from unittest.mock import Mock

import pytest
from opaque_keys.edx.keys import CourseKey

from openedx_webhooks.utils import flatten_dict, object_serializer, send


def test_flatten_dict_uses_joined_keys():
    """Nested dictionaries are flattened using underscore-separated keys."""
    assert flatten_dict({"user": {"name": "andres", "active": True}}) == {
        "user_name": "andres",
        "user_active": "True",
    }


def test_send_uses_form_encoded_payload_when_requested(monkeypatch):
    """Form-encoded requests send flattened dictionaries instead of a JSON string."""
    captured = {}

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["timeout"] = timeout
        return object()

    monkeypatch.setattr("openedx_webhooks.utils.requests.post", fake_post)

    send(
        "https://example.com/webhook",
        {"user": {"name": "andres"}},
        www_form_urlencoded=True,
    )

    assert captured["url"] == "https://example.com/webhook"
    assert captured["data"] == {"user_name": "andres"}
    assert captured["headers"]["Content-type"] == "application/x-www-form-urlencoded"
    assert captured["timeout"] == 10


def test_serializer_handles_cycles_and_non_string_dictionary_keys():
    """Recursive contexts are bounded and opaque keys are preserved as strings."""
    key = CourseKey.from_string('course-v1:edX+DemoX+Demo')
    context = {key: {'value': 1}}
    context['cycle'] = context
    serialized = object_serializer(context)
    assert serialized[str(key)] == {'value': 1}
    assert '! Depth limit reached !' in str(serialized)


def test_json_transport_redacts_nested_credentials(monkeypatch):
    """The shared transport strips credentials even from already serialized data."""
    post = Mock()
    monkeypatch.setattr('openedx_webhooks.utils.requests.post', post)
    payload = {'user': {'password': 'hash', 'username': 'learner'}, 'items': [{'access_token': 'secret'}]}
    send('https://example.com/hook', payload)
    assert json.loads(post.call_args.kwargs['data']) == {'user': {'username': 'learner'}, 'items': [{}]}
    assert payload['user']['password'] == 'hash'


@pytest.mark.parametrize('key', ['token', 'id_token', 'Token', 'ID_TOKEN'])
@pytest.mark.parametrize('form_encoded', [False, True])
def test_transport_and_serializer_redact_common_tokens(monkeypatch, key, form_encoded):
    """Token keys are removed at every nesting level in JSON and form payloads."""
    post = Mock()
    monkeypatch.setattr('openedx_webhooks.utils.requests.post', post)
    payload = {key: 'root-secret', 'user': {key: 'nested-secret', 'name': 'learner'},
               'items': [{key: 'list-secret'}]}
    expected = {'user': {'name': 'learner'}, 'items': [{}]}
    assert object_serializer(payload) == expected
    send('https://example.com/hook', payload, www_form_urlencoded=form_encoded)
    body = post.call_args.kwargs['data']
    assert body == flatten_dict(expected) if form_encoded else json.loads(body) == expected
    assert payload[key] == 'root-secret'
    assert payload['user'][key] == 'nested-secret'
    assert payload['items'][0][key] == 'list-secret'
