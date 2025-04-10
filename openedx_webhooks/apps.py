"""
openedx_webhooks Django application initialization.
"""
import logging

from django.apps import AppConfig

# Declare all signals
signals = {
    # Authoring
    "COURSE_CATALOG_INFO_CHANGED": "org.openedx.content_authoring.course.catalog_info.changed.v1",
    "XBLOCK_CREATED": "org.openedx.content_authoring.xblock.created.v1",
    "XBLOCK_UPDATED": "org.openedx.content_authoring.xblock.updated.v1",
    "XBLOCK_PUBLISHED": "org.openedx.content_authoring.xblock.published.v1",
    "XBLOCK_DELETED": "org.openedx.content_authoring.xblock.deleted.v1",
    "XBLOCK_DUPLICATED": "org.openedx.content_authoring.xblock.duplicated.v1",
    "COURSE_CERTIFICATE_CONFIG_CHANGED": "org.openedx.content_authoring.course.certificate_config.changed.v1",
    "COURSE_CERTIFICATE_CONFIG_DELETED": "org.openedx.content_authoring.course.certificate_config.deleted.v1",
    "COURSE_CREATED": "org.openedx.content_authoring.course.created.v1",
    "CONTENT_LIBRARY_CREATED": "org.openedx.content_authoring.content_library.created.v1",
    "CONTENT_LIBRARY_UPDATED": "org.openedx.content_authoring.content_library.updated.v1",
    "CONTENT_LIBRARY_DELETED": "org.openedx.content_authoring.content_library.deleted.v1",
    "LIBRARY_BLOCK_CREATED": "org.openedx.content_authoring.library_block.created.v1",
    "LIBRARY_BLOCK_UPDATED": "org.openedx.content_authoring.library_block.updated.v1",
    "LIBRARY_BLOCK_DELETED": "org.openedx.content_authoring.library_block.deleted.v1",
    "CONTENT_OBJECT_ASSOCIATIONS_CHANGED": "org.openedx.content_authoring.content.object.associations.changed.v1",
    "CONTENT_OBJECT_TAGS_CHANGED": "org.openedx.content_authoring.content.object.tags.changed.v1",
    "LIBRARY_COLLECTION_CREATED": "org.openedx.content_authoring.content_library.collection.created.v1",
    "LIBRARY_COLLECTION_UPDATED": "org.openedx.content_authoring.content_library.collection.updated.v1",
    "LIBRARY_COLLECTION_DELETED": "org.openedx.content_authoring.content_library.collection.deleted.v1",
    "LIBRARY_CONTAINER_CREATED": "org.openedx.content_authoring.content_library.container.created.v1",
    "LIBRARY_CONTAINER_UPDATED": "org.openedx.content_authoring.content_library.container.updated.v1",
    "LIBRARY_CONTAINER_DELETED": "org.openedx.content_authoring.content_library.container.deleted.v1",
    "COURSE_IMPORT_COMPLETED": "org.openedx.content_authoring.course.import.completed.v1",
    # Learning
    "STUDENT_REGISTRATION_COMPLETED": "org.openedx.learning.student.registration.completed.v1",
    "SESSION_LOGIN_COMPLETED": "org.openedx.learning.auth.session.login.completed.v1",
    "COURSE_ENROLLMENT_CREATED": "org.openedx.learning.course.enrollment.created.v1",
    "COURSE_ENROLLMENT_CHANGED": "org.openedx.learning.course.enrollment.changed.v1",
    "COURSE_UNENROLLMENT_COMPLETED": "org.openedx.learning.course.unenrollment.completed.v1",
    "CERTIFICATE_CREATED": "org.openedx.learning.certificate.created.v1",
    "CERTIFICATE_CHANGED": "org.openedx.learning.certificate.changed.v1",
    "CERTIFICATE_REVOKED": "org.openedx.learning.certificate.revoked.v1",
    "COHORT_MEMBERSHIP_CHANGED": "org.openedx.cohort_membership.changed.v1",
    "COURSE_DISCUSSIONS_CHANGED": "org.openedx.learning.discussions.configuration.changed.v1",
    "PROGRAM_CERTIFICATE_REVOKED": "org.openedx.learning.program.certificate.revoked.v1",
    "PROGRAM_CERTIFICATE_AWARDED": "org.openedx.learning.program.certificate.awarded.v1",
    "PERSISTENT_GRADE_SUMMARY_CHANGED": "org.openedx.learning.course.persistent_grade_summary.changed.v1",
    "XBLOCK_SKILL_VERIFIED": "org.openedx.learning.xblock.skill.verified.v1",
    "USER_NOTIFICATION_REQUESTED": "org.openedx.learning.user.notification.requested.v1",
    "EXAM_ATTEMPT_SUBMITTED": "org.openedx.learning.exam.attempt.submitted.v1",
    "EXAM_ATTEMPT_REJECTED": "org.openedx.learning.exam.attempt.rejected.v1",
    "EXAM_ATTEMPT_VERIFIED": "org.openedx.learning.exam.attempt.verified.v1",
    "EXAM_ATTEMPT_ERRORED": "org.openedx.learning.exam.attempt.errored.v1",
    "EXAM_ATTEMPT_RESET": "org.openedx.learning.exam.attempt.reset.v1",
    "COURSE_ACCESS_ROLE_ADDED": "org.openedx.learning.user.course_access_role.added.v1",
    "COURSE_ACCESS_ROLE_REMOVED": "org.openedx.learning.user.course_access_role.removed.v1",
    "FORUM_THREAD_CREATED": "org.openedx.learning.forum.thread.created.v1",
    "FORUM_THREAD_RESPONSE_CREATED": "org.openedx.learning.forum.thread.response.created.v1",
    "FORUM_RESPONSE_COMMENT_CREATED": "org.openedx.learning.forum.thread.response.comment.created.v1",
    "COURSE_NOTIFICATION_REQUESTED": "org.openedx.learning.course.notification.requested.v1",
    "ORA_SUBMISSION_CREATED": "org.openedx.learning.ora.submission.created.v1",
    "COURSE_PASSING_STATUS_UPDATED": "org.openedx.learning.course.passing.status.updated.v1",
    "CCX_COURSE_PASSING_STATUS_UPDATED": "org.openedx.learning.ccx.course.passing.status.updated.v1",
    "BADGE_AWARDED": "org.openedx.learning.badge.awarded.v1",
    "BADGE_REVOKED": "org.openedx.learning.badge.revoked.v1",
    "IDV_ATTEMPT_CREATED": "org.openedx.learning.idv_attempt.created.v1",
    "IDV_ATTEMPT_PENDING": "org.openedx.learning.idv_attempt.pending.v1",
    "IDV_ATTEMPT_APPROVED": "org.openedx.learning.idv_attempt.approved.v1",
    "IDV_ATTEMPT_DENIED": "org.openedx.learning.idv_attempt.denied.v1",
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
