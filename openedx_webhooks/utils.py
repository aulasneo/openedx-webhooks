"""
Utilities used by Open edX Events Receivers.
"""
import json
import logging
from collections.abc import Mapping, MutableMapping
from dataclasses import fields as dataclass_fields, is_dataclass
from typing import Any, Union

import requests
from attrs import fields, has
from django.db import models
from django.db.models.fields.files import FieldFile
from opaque_keys import OpaqueKey
from xblock.fields import ScopeIds

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = frozenset({
    'password', 'password1', 'password2', 'old_password', 'new_password',
    'token', 'id_token', 'access_token', 'refresh_token',
    'client_secret', 'authorization', 'cookie', 'csrfmiddlewaretoken',
})
_MAX_SERIALIZATION_DEPTH = 15
_MAX_SERIALIZATION_NODES = 10000
_DEPTH_LIMIT_MARKER = "! Depth limit reached !"
_NODE_LIMIT_MARKER = "! Node limit reached !"


def redact_sensitive_fields(value):
    """Remove credentials recursively without changing the caller's objects."""
    if isinstance(value, dict):
        return {
            key: redact_sensitive_fields(item) for key, item in value.items()
            if not isinstance(key, str) or key.lower() not in SENSITIVE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_fields(item) for item in value]
    return value


def send(url, payload, www_form_urlencoded: bool = False):
    """
    Dispatch the payload to the webhook url, return the response and catch exceptions.
    """
    payload = redact_sensitive_fields(payload)
    if www_form_urlencoded:
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
        payload = flatten_dict(payload)
        data = payload
    else:
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = json.dumps(payload, default=str)

    r = requests.post(url, data=data, headers=headers, timeout=10)

    return r


def flatten_dict(dictionary, parent_key="", sep="_"):
    """
    Generate a flatten dictionary-like object.

    Taken from:
    https://stackoverflow.com/a/6027615/16823624
    """
    items = []
    for key, value in dictionary.items():
        key = str(key)
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, str(value)))
    return dict(items)


def value_serializer(inst, field, value):  # pylint: disable=unused-argument
    """
    Serialize values for attr function.
    """
    return object_serializer(value)


def scope_ids_serializer(o):
    """
    Serialize instances of ScopeId.
    """
    return {
        "block_type": o.block_type,
        "def_id": str(o.def_id),
        "usage_id": str(o.usage_id),
        "user_id": o.user_id,
    }


def _mark_serialization_limit(state):
    """Mark one serialization as truncated and log the limit once."""
    state["exhausted"] = True
    if not state["warned"]:
        logger.warning(
            "Webhook payload serialization stopped at the %s-node limit",
            _MAX_SERIALIZATION_NODES,
        )
        state["warned"] = True


def object_serializer(o, depth=0, _state=None) -> Union[dict, Any]:
    """
    Serialize supported values without walking arbitrary object attributes.

    Supported structured values are mappings, sequences, Django models,
    attrs classes, and dataclasses. Unknown objects are represented as strings.
    A shared node budget bounds work across the complete value being serialized.
    """
    if _state is None:
        _state = {"nodes": 0, "active": set(), "exhausted": False, "warned": False}

    if depth > _MAX_SERIALIZATION_DEPTH:
        return _DEPTH_LIMIT_MARKER
    if _state["exhausted"]:
        return _NODE_LIMIT_MARKER
    if _state["nodes"] >= _MAX_SERIALIZATION_NODES:
        _mark_serialization_limit(_state)
        return _NODE_LIMIT_MARKER
    _state["nodes"] += 1

    if isinstance(o, (int, float,  str)) or o is None:
        return o
    if isinstance(o, ScopeIds):
        return scope_ids_serializer(o)
    if isinstance(o, FieldFile):
        return o.name or ""
    if isinstance(o, OpaqueKey):
        return str(o)

    is_sequence = isinstance(o, (list, tuple, set))
    is_mapping = isinstance(o, Mapping)
    is_model = isinstance(o, models.Model)
    is_attrs = has(type(o))
    is_dataclass_instance = is_dataclass(o) and not isinstance(o, type)

    if not (is_sequence or is_mapping or is_model or is_attrs or is_dataclass_instance):
        try:
            return str(o)
        except Exception:  # pylint: disable=broad-except
            return f"Unserializable {type(o).__module__}.{type(o).__qualname__}"

    object_id = id(o)
    if object_id in _state["active"]:
        return _DEPTH_LIMIT_MARKER

    _state["active"].add(object_id)
    try:
        if is_sequence:
            serialized = []
            for item in o:
                serialized.append(object_serializer(item, depth + 1, _state))
                if _state["exhausted"]:
                    break
            return serialized

        if is_mapping:
            entries = o.items()
        elif is_model:
            # Use loaded concrete values only: avoid related-object traversal
            # and database queries for deferred fields.
            entries = (
                (field.name, o.__dict__[field.attname])
                for field in o._meta.concrete_fields
                if field.attname in o.__dict__
            )
        elif is_attrs:
            entries = ((field.name, getattr(o, field.name)) for field in fields(type(o)))
        else:
            entries = ((field.name, getattr(o, field.name)) for field in dataclass_fields(o))

        serialized = {}
        for key, value in entries:
            key = str(key)
            if _state["nodes"] >= _MAX_SERIALIZATION_NODES:
                _mark_serialization_limit(_state)
                if not key.startswith("_") and key.lower() not in SENSITIVE_FIELDS:
                    serialized[key] = _NODE_LIMIT_MARKER
                break
            _state["nodes"] += 1
            # Hide private fields and credentials, including on nested objects.
            if not key.startswith("_") and key.lower() not in SENSITIVE_FIELDS:
                serialized[key] = object_serializer(value, depth + 1, _state)
            if _state["exhausted"]:
                break
        return serialized
    finally:
        _state["active"].remove(object_id)
