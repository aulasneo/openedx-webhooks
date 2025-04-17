"""
Utilities used by Open edX Events Receivers.
"""
import json
import logging
from collections.abc import MutableMapping, dict_values
from typing import Any, Union

import requests
from opaque_keys import OpaqueKey
from xblock.fields import ScopeIds

logger = logging.getLogger(__name__)


def send(url, payload, www_form_urlencoded: bool = False):
    """
    Dispatch the payload to the webhook url, return the response and catch exceptions.
    """
    if www_form_urlencoded:
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
        payload = flatten_dict(payload)
    else:
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(url, data=json.dumps(payload, default=str), headers=headers, timeout=10)

    return r


def flatten_dict(dictionary, parent_key="", sep="_"):
    """
    Generate a flatten dictionary-like object.

    Taken from:
    https://stackoverflow.com/a/6027615/16823624
    """
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, str(value)))
    return dict(items)


def value_serializer(inst, field, value):  # pylint: disable=unused-argument
    """
    Serialize instances of CourseLocator.

    When value is anything else returns it without modification.
    """
    return object_serializer(value)

def scope_ids_serializer(o):
    return {
        "block_type": o.block_type,
        "def_id": str(o.def_id),
        "usage_id": str(o.usage_id),
        "user_id": o.user_id,
    }

def object_serializer(o, depth=0) -> Union[dict, Any]:
    if depth > 10:
        return "! Depth limit reached !"
    if isinstance(o, int) or isinstance(o, float) or isinstance(o, str) or o is None:
        return o
    elif isinstance(o, ScopeIds):
        return scope_ids_serializer(o)
    elif isinstance(o, OpaqueKey):
        return str(o)
    if isinstance(o, list):
        return [object_serializer(item, depth + 1) for item in o]
    return_value = {}
    if isinstance(o, dict):
        dict_values = o
    elif hasattr(o, "__dict__"):
        dict_values = o.__dict__
    elif hasattr(o, "__str__"):
        return str(o)
    else:
        return f"Unserializable {type(o)}"
    for key, value in dict_values.items():
        if key in ['_parent_block', '_runtime']:
            continue
        if isinstance(key, str):
            return_value[key] = object_serializer(value, depth + 1)
    return return_value
