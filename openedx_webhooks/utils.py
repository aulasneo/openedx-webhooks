"""
Utilities used by Open edX Events Receivers.
"""
from collections.abc import MutableMapping

from opaque_keys.edx.locator import CourseLocator


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
