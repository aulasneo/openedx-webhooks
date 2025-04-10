"""
Utilities used by Open edX Events Receivers.
"""
import json
import logging
from collections.abc import MutableMapping
from typing import Any, Union

import requests
from opaque_keys import OpaqueKey
from xblock.fields import ScopeIds  # pylint: disable=import-error

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


def object_serializer(o, depth=0) -> Union[dict, Any]:
    """
    Serialize an arbitrary object as a json-serializable dict.
    """
    if depth > 15:
        return "! Depth limit reached !"
    # First serialize scalar objects
    if isinstance(o, (int, float,  str)) or o is None:
        return o
    # ScopeIds is a class present in block structures
    elif isinstance(o, ScopeIds):
        return scope_ids_serializer(o)
    elif isinstance(o, OpaqueKey):
        return str(o)
    if isinstance(o, (list, tuple, set)):
        return [object_serializer(item, depth + 1) for item in o]
    # Now serialize dict-like objects
    return_value = {}
    if isinstance(o, dict):
        dict_values = o.copy()
    elif hasattr(o, "__dict__"):
        dict_values = o.__dict__.copy()
    # if it is not a dict and cannot be converted to a dict, try to stringify it.
    elif hasattr(o, "__str__"):
        return str(o)
    else:
        return f"Unserializable {type(o)}"
    for key, value in dict_values.items():
        if isinstance(key, str):
            # Hide the private fields
            if not key.startswith("_"):
                return_value[key] = object_serializer(value, depth + 1)
    return return_value
