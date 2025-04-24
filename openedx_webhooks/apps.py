"""
openedx_webhooks Django application initialization.
"""
import logging

from django.apps import AppConfig

# Declare all signals
signals = {
    "content_authoring": [
        "COURSE_CATALOG_INFO_CHANGED",
        "XBLOCK_CREATED",
        "XBLOCK_UPDATED",
        "XBLOCK_PUBLISHED",
        "XBLOCK_DELETED",
        "XBLOCK_DUPLICATED",
        "COURSE_CERTIFICATE_CONFIG_CHANGED",
        "COURSE_CERTIFICATE_CONFIG_DELETED",
        "COURSE_CREATED",
        "CONTENT_LIBRARY_CREATED",
        "CONTENT_LIBRARY_UPDATED",
        "CONTENT_LIBRARY_DELETED",
        "LIBRARY_BLOCK_CREATED",
        "LIBRARY_BLOCK_UPDATED",
        "LIBRARY_BLOCK_DELETED",
        "CONTENT_OBJECT_TAGS_CHANGED",
        "CONTENT_OBJECT_ASSOCIATIONS_CHANGED",
        "LIBRARY_COLLECTION_CREATED",
        "LIBRARY_COLLECTION_UPDATED",
        "LIBRARY_COLLECTION_DELETED",
        # "LIBRARY_CONTAINER_CREATED",
        # "LIBRARY_CONTAINER_UPDATED",
        # "LIBRARY_CONTAINER_DELETED",
        # "COURSE_IMPORT_COMPLETED",
    ],
    "learning": [
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
        "PROGRAM_CERTIFICATE_REVOKED",
        "PROGRAM_CERTIFICATE_AWARDED",
        "PERSISTENT_GRADE_SUMMARY_CHANGED",
        "XBLOCK_SKILL_VERIFIED",
        "USER_NOTIFICATION_REQUESTED",
        "EXAM_ATTEMPT_SUBMITTED",
        "EXAM_ATTEMPT_REJECTED",
        "EXAM_ATTEMPT_VERIFIED",
        "EXAM_ATTEMPT_ERRORED",
        "EXAM_ATTEMPT_RESET",
        "COURSE_ACCESS_ROLE_ADDED",
        "COURSE_ACCESS_ROLE_REMOVED",
        "FORUM_THREAD_CREATED",
        "FORUM_THREAD_RESPONSE_CREATED",
        "FORUM_RESPONSE_COMMENT_CREATED",
        "COURSE_NOTIFICATION_REQUESTED",
        "ORA_SUBMISSION_CREATED",
        "COURSE_PASSING_STATUS_UPDATED",
        "CCX_COURSE_PASSING_STATUS_UPDATED",
        "BADGE_AWARDED",
        "BADGE_REVOKED",
        "IDV_ATTEMPT_CREATED",
        "IDV_ATTEMPT_PENDING",
        "IDV_ATTEMPT_APPROVED",
        "IDV_ATTEMPT_DENIED",
    ]
}

logger = logging.getLogger(__name__)


class WebhooksConfig(AppConfig):
    """
    Configuration for the webhooks Django application.
    """

    name = 'openedx_webhooks'

    receivers = []
    for signal_app, signal_list in signals.items():
        for signal in signal_list:
            receivers.append({
                        "receiver_func_name": signal.lower() + "_receiver",
                        "signal_path": f"openedx_events.{signal_app}.signals.{signal}",
                    })

    plugin_app = {
        "settings_config": {
            "lms.djangoapp": {
                "common": {"relative_path": "settings.common"},
                "test": {"relative_path": "settings.test"},
            },
        },
        "signals_config": {
            "lms.djangoapp": {
                "relative_path": "receivers",
                "receivers": receivers,
            }
        },
    }

    logger.info("Open edx Webhooks: signals registerd")
