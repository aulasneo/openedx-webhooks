"""
Utilities used by Open edX Events Receivers.
"""
import json
import logging
from collections.abc import MutableMapping

import requests
from opaque_keys.edx.locator import CourseLocator

logger = logging.getLogger(__name__)


def send(url, payload, www_form_urlencoded: bool = False):
    """
    Dispatch the payload to the webhook url, return the response and catch exceptions.
    """
    try:
        if www_form_urlencoded:
            headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
            payload = flatten_dict(payload)
        else:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        # pylint: disable=unnecessary-lambda
        r = requests.post(url, data=json.dumps(payload, default=lambda o: str(o)), headers=headers, timeout=10)

        r.raise_for_status()
    except requests.ConnectionError as e:
        logger.error(f"Connection error {str(e)} calling webhook {url}")
    except requests.Timeout:
        logger.error(f"Timeout calling webhook {url}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {str(e)} calling webhook {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error {str(e)} calling webhook {url}")

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


def serialize_course_key(inst, field, value):  # pylint: disable=unused-argument
    """
    Serialize instances of CourseLocator.

    When value is anything else returns it without modification.
    """
    if isinstance(value, CourseLocator):
        return str(value)
    return value
