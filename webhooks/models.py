"""
Models for Webhooks.

written by:     Andrés González
                https://aulasneo.com

date:           May 2023

usage:          Django models for Open edX signals webhooks
"""

from django.db import models
from django.utils.translation import gettext as _
from model_utils.models import TimeStampedModel

signals = [
    "STUDENT_REGISTRATION_COMPLETED",
    "SESSION_LOGIN_COMPLETED",
    "COURSE_ENROLLMENT_CREATED",
    "COURSE_ENROLLMENT_CHANGED",
    "COURSE_UNENROLLMENT_COMPLETED",
    "CERTIFICATE_CREATED",
    "CERTIFICATE_CHANGED",
    "CERTIFICATE_REVOKED",
    "COHORT_MEMBERSHIP_CHANGED",
    "COURSE_DISCUSSIONS_CHANGED",
    # "PERSISTENT_GRADE_SUMMARY_CHANGED",
]


class Webhook(TimeStampedModel):
    """
    Configuration model to set the webhook url for each event.

    .. no_pii:
    """

    # Create a set of pairs like ("COURSE_ENROLLMENT_CREATED", "Course enrollment created")...
    event_list = (
        (signal,
         signal[0] + signal[1:].lower().replace("_", " ")) for signal in signals
    )

    event = models.CharField(
        max_length=50,
        blank=False,
        primary_key=False,
        choices=event_list,
        default='',
        unique=False,
        help_text=_("Event type"),
    )

    webhook_url = models.URLField(
        max_length=255,
        blank=False,
        help_text=_("URL to call when the event is triggered")
    )

    enabled = models.BooleanField(
        default=True,
        verbose_name="Enabled"
    )

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return f'Webhook for {self.event} to {self.webhook_url}'
