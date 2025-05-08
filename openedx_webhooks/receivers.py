"""
Open edX signal events handler functions.
"""
import logging

from attrs import asdict

from .models import Webhook
from .utils import send, value_serializer

logger = logging.getLogger(__name__)


def _process_event(event_name, data, **kwargs):
    """
    Process all events with user data.
    """
    logger.debug(f"Processing event: {event_name}")
    webhooks = Webhook.objects.filter(enabled=True, event=event_name)

    # Get the name of the data type
    data_type = str(type(data)).split("'")[1]

    for webhook in webhooks:
        logger.info(f"{event_name} webhook triggered to {webhook.webhook_url}")

        payload = {
            data_type: asdict(data, value_serializer=value_serializer),
            'event_metadata': asdict(kwargs.get("metadata")),
        }
        logger.warning(payload)
        send(webhook.webhook_url, payload, www_form_urlencoded=False)


def session_login_completed_receiver(user, **kwargs):
    """
    Handle SESSION_LOGIN_COMPLETED signal.

    Example of data sent:
        user_id:    	                4
        user_is_active:	                True
        user_pii_username:	            andres
        user_pii_email:	                andres@aulasneo.com
        user_pii_name:	                (empty)
        event_metadata_id:	            457f0c26-a1a5-11ed-afe6-0242ac140007
        event_metadata_event_type:	    org.openedx.learning.auth.session.login.completed.v1
        event_metadata_minorversion:	0
        event_metadata_source:	        openedx/lms/web
        event_metadata_sourcehost:	    8616aa50f067
        event_metadata_time:	        2023-01-31 20:24:32.598387
        event_metadata_sourcelib:   	(0, 8, 1)
    """
    _process_event("SESSION_LOGIN_COMPLETED", user, **kwargs)


def student_registration_completed_receiver(user, **kwargs):
    """
    Handle STUDENT_REGISTRATION_COMPLETED signal.
    """
    _process_event("STUDENT_REGISTRATION_COMPLETED", user, **kwargs)


def course_enrollment_created_receiver(enrollment, **kwargs):
    """
    Handle COURSE_ENROLLMENT_CREATED signal.

    Example of data sent:
        enrollment_user_id:	            4
        enrollment_user_is_active:	    True
        enrollment_user_pii_username:	andres
        enrollment_user_pii_email:	    andres@aulasneo.com
        enrollment_user_pii_name:	    (empty)
        enrollment_course_course_key:	course-v1:edX+DemoX+Demo_Course
        enrollment_course_display_name:	Demonstration Course
        enrollment_course_start:	    None
        enrollment_course_end;	        None
        enrollment_mode:	            honor
        enrollment_is_active:	        True
        enrollment_creation_date:	    2023-01-31 20:28:10.976084+00:00
        enrollment_created_by:	        None
        event_metadata_id:	            c8bee32c-a1a5-11ed-baf0-0242ac140007
        event_metadata_event_type:	    org.openedx.learning.course.enrollment.created.v1
        event_metadata_minorversio:	    0
        event_metadata_source:	        openedx/lms/web
        event_metadata_sourcehost:	    8616aa50f067
        event_metadata_time:	        2023-01-31 20:28:12.798285
        event_metadata_sourcelib:	    (0, 8, 1)
    """
    _process_event("COURSE_ENROLLMENT_CREATED", enrollment, **kwargs)


def course_enrollment_changed_receiver(enrollment, **kwargs):
    """
    Handle COURSE_ENROLLMENT_CHANGED signal.
    """
    _process_event("COURSE_ENROLLMENT_CHANGED", enrollment, **kwargs)


def course_unenrollment_completed_receiver(enrollment, **kwargs):
    """
    Handle COURSE_UNENROLLMENT_COMPLETED signal.
    """
    _process_event("COURSE_UNENROLLMENT_COMPLETED", enrollment, **kwargs)


def certificate_created_receiver(certificate, **kwargs):
    """
    Handle CERTIFICATE_CREATED signal.
    """
    _process_event("CERTIFICATE_CREATED", certificate, **kwargs)


def certificate_changed_receiver(certificate, **kwargs):
    """
    Handle CERTIFICATE_CHANGED signal.
    """
    _process_event("CERTIFICATE_CHANGED", certificate, **kwargs)


def certificate_revoked_receiver(certificate, **kwargs):
    """
    Handle CERTIFICATE_REVOKED signal.
    """
    _process_event("CERTIFICATE_REVOKED", certificate, **kwargs)


def cohort_membership_changed_receiver(cohort, **kwargs):
    """
    Handle COHORT_MEMBERSHIP_CHANGED signal.
    """
    _process_event("COHORT_MEMBERSHIP_CHANGED", cohort, **kwargs)


def course_discussions_changed_receiver(configuration, **kwargs):
    """
    Handle COURSE_DISCUSSIONS_CHANGED signal.
    """
    _process_event("COURSE_DISCUSSIONS_CHANGED", configuration, **kwargs)


def program_certificate_awarded_receiver(program_certificate, **kwargs):
    """Handle PROGRAM_CERTIFICATE_AWARDED signal."""
    _process_event("PROGRAM_CERTIFICATE_AWARDED", program_certificate, **kwargs)


def program_certificate_revoked_receiver(program_certificate, **kwargs):
    """Handle PROGRAM_CERTIFICATE_REVOKED signal."""
    _process_event("PROGRAM_CERTIFICATE_REVOKED", program_certificate, **kwargs)


def persistent_grade_summary_changed_receiver(grade, **kwargs):
    """Handle PERSISTENT_GRADE_SUMMARY_CHANGED signal."""
    _process_event("PERSISTENT_GRADE_SUMMARY_CHANGED", grade, **kwargs)


def xblock_skill_verified_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_SKILL_VERIFIED signal."""
    _process_event("XBLOCK_SKILL_VERIFIED", xblock_info, **kwargs)


def user_notification_requested_receiver(notification_data, **kwargs):
    """Handle USER_NOTIFICATION_REQUESTED signal."""
    _process_event("USER_NOTIFICATION_REQUESTED", notification_data, **kwargs)


def exam_attempt_submitted_receiver(exam_attempt, **kwargs):
    """Handle EXAM_ATTEMPT_SUBMITTED signal."""
    _process_event("EXAM_ATTEMPT_SUBMITTED", exam_attempt, **kwargs)


def exam_attempt_rejected_receiver(exam_attempt, **kwargs):
    """Handle EXAM_ATTEMPT_REJECTED signal."""
    _process_event("EXAM_ATTEMPT_REJECTED", exam_attempt, **kwargs)


def exam_attempt_verified_receiver(exam_attempt, **kwargs):
    """Handle EXAM_ATTEMPT_VERIFIED signal."""
    _process_event("EXAM_ATTEMPT_VERIFIED", exam_attempt, **kwargs)


def exam_attempt_errored_receiver(exam_attempt, **kwargs):
    """Handle EXAM_ATTEMPT_ERRORED signal."""
    _process_event("EXAM_ATTEMPT_ERRORED", exam_attempt, **kwargs)


def exam_attempt_reset_receiver(exam_attempt, **kwargs):
    """Handle EXAM_ATTEMPT_RESET signal."""
    _process_event("EXAM_ATTEMPT_RESET", exam_attempt, **kwargs)


def course_access_role_added_receiver(course_access_role_data, **kwargs):
    """Handle COURSE_ACCESS_ROLE_ADDED signal."""
    _process_event("COURSE_ACCESS_ROLE_ADDED", course_access_role_data, **kwargs)


def course_access_role_removed_receiver(course_access_role_data, **kwargs):
    """Handle COURSE_ACCESS_ROLE_REMOVED signal."""
    _process_event("COURSE_ACCESS_ROLE_REMOVED", course_access_role_data, **kwargs)


def forum_thread_created_receiver(thread, **kwargs):
    """Handle FORUM_THREAD_CREATED signal."""
    _process_event("FORUM_THREAD_CREATED", thread, **kwargs)


def forum_thread_response_created_receiver(thread, **kwargs):
    """Handle FORUM_THREAD_RESPONSE_CREATED signal."""
    _process_event("FORUM_THREAD_RESPONSE_CREATED", thread, **kwargs)


def forum_response_comment_created_receiver(thread, **kwargs):
    """Handle FORUM_RESPONSE_COMMENT_CREATED signal."""
    _process_event("FORUM_RESPONSE_COMMENT_CREATED", thread, **kwargs)


def course_notification_requested_receiver(course_notification_data, **kwargs):
    """Handle COURSE_NOTIFICATION_REQUESTED signal."""
    _process_event("COURSE_NOTIFICATION_REQUESTED", course_notification_data, **kwargs)


def ora_submission_created_receiver(submission, **kwargs):
    """Handle ORA_SUBMISSION_CREATED signal."""
    _process_event("ORA_SUBMISSION_CREATED", submission, **kwargs)


def course_passing_status_updated_receiver(course_passing_status, **kwargs):
    """Handle COURSE_PASSING_STATUS_UPDATED signal."""
    _process_event("COURSE_PASSING_STATUS_UPDATED", course_passing_status, **kwargs)


def ccx_course_passing_status_updated_receiver(course_passing_status, **kwargs):
    """Handle CCX_COURSE_PASSING_STATUS_UPDATED signal."""
    _process_event("CCX_COURSE_PASSING_STATUS_UPDATED", course_passing_status, **kwargs)


def badge_awarded_receiver(badge, **kwargs):
    """Handle BADGE_AWARDED signal."""
    _process_event("BADGE_AWARDED", badge, **kwargs)


def badge_revoked_receiver(badge, **kwargs):
    """Handle BADGE_REVOKED signal."""
    _process_event("BADGE_REVOKED", badge, **kwargs)


def idv_attempt_created_receiver(idv_attempt, **kwargs):
    """Handle IDV_ATTEMPT_CREATED signal."""
    _process_event("IDV_ATTEMPT_CREATED", idv_attempt, **kwargs)


def idv_attempt_pending_receiver(idv_attempt, **kwargs):
    """Handle IDV_ATTEMPT_PENDING signal."""
    _process_event("IDV_ATTEMPT_PENDING", idv_attempt, **kwargs)


def idv_attempt_approved_receiver(idv_attempt, **kwargs):
    """Handle IDV_ATTEMPT_APPROVED signal."""
    _process_event("IDV_ATTEMPT_APPROVED", idv_attempt, **kwargs)


def idv_attempt_denied_receiver(idv_attempt, **kwargs):
    """Handle IDV_ATTEMPT_DENIED signal."""
    _process_event("IDV_ATTEMPT_DENIED", idv_attempt, **kwargs)


#
# Course authoring
def course_catalog_info_changed_receiver(catalog_info, **kwargs):
    """Handle COURSE_CATALOG_INFO_CHANGED signal."""
    _process_event("COURSE_CATALOG_INFO_CHANGED", catalog_info, **kwargs)


def xblock_created_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_CREATED signal."""
    _process_event("XBLOCK_CREATED", xblock_info, **kwargs)


def xblock_updated_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_UPDATED signal."""
    _process_event("XBLOCK_UPDATED", xblock_info, **kwargs)


def xblock_published_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_PUBLISHED signal."""
    _process_event("XBLOCK_PUBLISHED", xblock_info, **kwargs)


def xblock_deleted_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_DELETED signal."""
    _process_event("XBLOCK_DELETED", xblock_info, **kwargs)


def xblock_duplicated_receiver(xblock_info, **kwargs):
    """Handle XBLOCK_DUPLICATED signal."""
    _process_event("XBLOCK_DUPLICATED", xblock_info, **kwargs)


def course_certificate_config_changed_receiver(certificate_config, **kwargs):
    """Handle COURSE_CERTIFICATE_CONFIG_CHANGED signal."""
    _process_event("COURSE_CERTIFICATE_CONFIG_CHANGED", certificate_config, **kwargs)


def course_certificate_config_deleted_receiver(certificate_config, **kwargs):
    """Handle COURSE_CERTIFICATE_CONFIG_DELETED signal."""
    _process_event("COURSE_CERTIFICATE_CONFIG_DELETED", certificate_config, **kwargs)


def course_created_receiver(course, **kwargs):
    """Handle COURSE_CREATED signal."""
    _process_event("COURSE_CREATED", course, **kwargs)


def content_library_created_receiver(content_library, **kwargs):
    """Handle CONTENT_LIBRARY_CREATED signal."""
    _process_event("CONTENT_LIBRARY_CREATED", content_library, **kwargs)


def content_library_updated_receiver(content_library, **kwargs):
    """Handle CONTENT_LIBRARY_UPDATED signal."""
    _process_event("CONTENT_LIBRARY_UPDATED", content_library, **kwargs)


def content_library_deleted_receiver(content_library, **kwargs):
    """Handle CONTENT_LIBRARY_DELETED signal."""
    _process_event("CONTENT_LIBRARY_DELETED", content_library, **kwargs)


def library_block_created_receiver(library_block, **kwargs):
    """Handle LIBRARY_BLOCK_CREATED signal."""
    _process_event("LIBRARY_BLOCK_CREATED", library_block, **kwargs)


def library_block_updated_receiver(library_block, **kwargs):
    """Handle LIBRARY_BLOCK_UPDATED signal."""
    _process_event("LIBRARY_BLOCK_UPDATED", library_block, **kwargs)


def library_block_deleted_receiver(library_block, **kwargs):
    """Handle LIBRARY_BLOCK_DELETED signal."""
    _process_event("LIBRARY_BLOCK_DELETED", library_block, **kwargs)


def content_object_associations_changed_receiver(content_object, **kwargs):
    """Handle CONTENT_OBJECT_ASSOCIATIONS_CHANGED signal."""
    _process_event("CONTENT_OBJECT_ASSOCIATIONS_CHANGED", content_object, **kwargs)


def content_object_tags_changed_receiver(content_object, **kwargs):
    """Handle CONTENT_OBJECT_TAGS_CHANGED signal."""
    _process_event("CONTENT_OBJECT_TAGS_CHANGED", content_object, **kwargs)


def library_collection_created_receiver(library_collection, **kwargs):
    """Handle LIBRARY_COLLECTION_CREATED signal."""
    _process_event("LIBRARY_COLLECTION_CREATED", library_collection, **kwargs)


def library_collection_updated_receiver(library_collection, **kwargs):
    """Handle LIBRARY_COLLECTION_UPDATED signal."""
    _process_event("LIBRARY_COLLECTION_UPDATED", library_collection, **kwargs)


def library_collection_deleted_receiver(library_collection, **kwargs):
    """Handle LIBRARY_COLLECTION_DELETED signal."""
    _process_event("LIBRARY_COLLECTION_DELETED", library_collection, **kwargs)


# def library_container_created_receiver(data, **kwargs):
#     """Handle LIBRARY_CONTAINER_CREATED signal."""
#     _process_event("LIBRARY_CONTAINER_CREATED", data, **kwargs)
#
#
# def library_container_updated_receiver(data, **kwargs):
#     """Handle LIBRARY_CONTAINER_UPDATED signal."""
#     _process_event("LIBRARY_CONTAINER_UPDATED", data, **kwargs)
#
#
# def library_container_deleted_receiver(data, **kwargs):
#     """Handle LIBRARY_CONTAINER_DELETED signal."""
#     _process_event("LIBRARY_CONTAINER_DELETED", data, **kwargs)
#
#
# def course_import_completed_receiver(data, **kwargs):
#     """Handle COURSE_IMPORT_COMPLETED signal."""
#     _process_event("COURSE_IMPORT_COMPLETED", data, **kwargs)
