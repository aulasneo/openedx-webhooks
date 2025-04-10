"""
openedx_webhooks Django application initialization.
"""
import logging

from django.apps import AppConfig

# Declare all signals
signals = {
    # Authoring
    "COURSE_CATALOG_INFO_CHANGED": "openedx_events.content_authoring.course.catalog_info.changed.v1",
    "XBLOCK_CREATED": "openedx_events.content_authoring.xblock.created.v1",
    "XBLOCK_UPDATED": "openedx_events.content_authoring.xblock.updated.v1",
    "XBLOCK_PUBLISHED": "openedx_events.content_authoring.xblock.published.v1",
    "XBLOCK_DELETED": "openedx_events.content_authoring.xblock.deleted.v1",
    "XBLOCK_DUPLICATED": "openedx_events.content_authoring.xblock.duplicated.v1",
    "COURSE_CERTIFICATE_CONFIG_CHANGED": "openedx_events.content_authoring.course.certificate_config.changed.v1",
    "COURSE_CERTIFICATE_CONFIG_DELETED": "openedx_events.content_authoring.course.certificate_config.deleted.v1",
    "COURSE_CREATED": "openedx_events.content_authoring.course.created.v1",
    "CONTENT_LIBRARY_CREATED": "openedx_events.content_authoring.content_library.created.v1",
    "CONTENT_LIBRARY_UPDATED": "openedx_events.content_authoring.content_library.updated.v1",
    "CONTENT_LIBRARY_DELETED": "openedx_events.content_authoring.content_library.deleted.v1",
    "LIBRARY_BLOCK_CREATED": "openedx_events.content_authoring.library_block.created.v1",
    "LIBRARY_BLOCK_UPDATED": "openedx_events.content_authoring.library_block.updated.v1",
    "LIBRARY_BLOCK_DELETED": "openedx_events.content_authoring.library_block.deleted.v1",
    "CONTENT_OBJECT_ASSOCIATIONS_CHANGED": "openedx_events.content_authoring.content.object.associations.changed.v1",
    "CONTENT_OBJECT_TAGS_CHANGED": "openedx_events.content_authoring.content.object.tags.changed.v1",
    "LIBRARY_COLLECTION_CREATED": "openedx_events.content_authoring.content_library.collection.created.v1",
    "LIBRARY_COLLECTION_UPDATED": "openedx_events.content_authoring.content_library.collection.updated.v1",
    "LIBRARY_COLLECTION_DELETED": "openedx_events.content_authoring.content_library.collection.deleted.v1",
    "LIBRARY_CONTAINER_CREATED": "openedx_events.content_authoring.content_library.container.created.v1",
    "LIBRARY_CONTAINER_UPDATED": "openedx_events.content_authoring.content_library.container.updated.v1",
    "LIBRARY_CONTAINER_DELETED": "openedx_events.content_authoring.content_library.container.deleted.v1",
    "COURSE_IMPORT_COMPLETED": "openedx_events.content_authoring.course.import.completed.v1",
    # Learning
    "STUDENT_REGISTRATION_COMPLETED": "openedx_events.learning.student.registration.completed.v1",
    "SESSION_LOGIN_COMPLETED": "openedx_events.learning.auth.session.login.completed.v1",
    "COURSE_ENROLLMENT_CREATED": "openedx_events.learning.course.enrollment.created.v1",
    "COURSE_ENROLLMENT_CHANGED": "openedx_events.learning.course.enrollment.changed.v1",
    "COURSE_UNENROLLMENT_COMPLETED": "openedx_events.learning.course.unenrollment.completed.v1",
    "CERTIFICATE_CREATED": "openedx_events.learning.certificate.created.v1",
    "CERTIFICATE_CHANGED": "openedx_events.learning.certificate.changed.v1",
    "CERTIFICATE_REVOKED": "openedx_events.learning.certificate.revoked.v1",
    "COHORT_MEMBERSHIP_CHANGED": "openedx_events.cohort_membership.changed.v1",
    "COURSE_DISCUSSIONS_CHANGED": "openedx_events.learning.discussions.configuration.changed.v1",
    "PROGRAM_CERTIFICATE_REVOKED": "openedx_events.learning.program.certificate.revoked.v1",
    "PROGRAM_CERTIFICATE_AWARDED": "openedx_events.learning.program.certificate.awarded.v1",
    "PERSISTENT_GRADE_SUMMARY_CHANGED": "openedx_events.learning.course.persistent_grade_summary.changed.v1",
    "XBLOCK_SKILL_VERIFIED": "openedx_events.learning.xblock.skill.verified.v1",
    "USER_NOTIFICATION_REQUESTED": "openedx_events.learning.user.notification.requested.v1",
    "EXAM_ATTEMPT_SUBMITTED": "openedx_events.learning.exam.attempt.submitted.v1",
    "EXAM_ATTEMPT_REJECTED": "openedx_events.learning.exam.attempt.rejected.v1",
    "EXAM_ATTEMPT_VERIFIED": "openedx_events.learning.exam.attempt.verified.v1",
    "EXAM_ATTEMPT_ERRORED": "openedx_events.learning.exam.attempt.errored.v1",
    "EXAM_ATTEMPT_RESET": "openedx_events.learning.exam.attempt.reset.v1",
    "COURSE_ACCESS_ROLE_ADDED": "openedx_events.learning.user.course_access_role.added.v1",
    "COURSE_ACCESS_ROLE_REMOVED": "openedx_events.learning.user.course_access_role.removed.v1",
    "FORUM_THREAD_CREATED": "openedx_events.learning.forum.thread.created.v1",
    "FORUM_THREAD_RESPONSE_CREATED": "openedx_events.learning.forum.thread.response.created.v1",
    "FORUM_RESPONSE_COMMENT_CREATED": "openedx_events.learning.forum.thread.response.comment.created.v1",
    "COURSE_NOTIFICATION_REQUESTED": "openedx_events.learning.course.notification.requested.v1",
    "ORA_SUBMISSION_CREATED": "openedx_events.learning.ora.submission.created.v1",
    "COURSE_PASSING_STATUS_UPDATED": "openedx_events.learning.course.passing.status.updated.v1",
    "CCX_COURSE_PASSING_STATUS_UPDATED": "openedx_events.learning.ccx.course.passing.status.updated.v1",
    "BADGE_AWARDED": "openedx_events.learning.badge.awarded.v1",
    "BADGE_REVOKED": "openedx_events.learning.badge.revoked.v1",
    "IDV_ATTEMPT_CREATED": "openedx_events.learning.idv_attempt.created.v1",
    "IDV_ATTEMPT_PENDING": "openedx_events.learning.idv_attempt.pending.v1",
    "IDV_ATTEMPT_APPROVED": "openedx_events.learning.idv_attempt.approved.v1",
    "IDV_ATTEMPT_DENIED": "openedx_events.learning.idv_attempt.denied.v1",
}

logger = logging.getLogger(__name__)


class WebhooksConfig(AppConfig):
    """
    Configuration for the webhooks Django application.
    """

    name = 'openedx_webhooks'

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
                "receivers": [
                    {
                        "receiver_func_name": signal.lower() + "_receiver",
                        "signal_path": signal_path
                    } for signal, signal_path in signals.items()
                ],
            }
        },
    }

    logger.info("Signals registerd")


logger.info("Calling webhooks app")
