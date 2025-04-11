"""
Open edX signal events handler functions.
"""
import logging

from attrs import asdict

from .models import Webhook
from .utils import send

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
            data_type: asdict(data, value_serializer=str),
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


def program_certificate_awareded_receiver(data, **kwargs):
    _process_event("PROGRAM_CERTIFICATE_AWARDED", data, **kwargs)

def program_certificate_revoked_receiver(data, **kwargs):
    _process_event("PROGRAM_CERTIFICATE_REVOKED", data, **kwargs)

def persistent_grade_summary_changed_receiver(data, **kwargs):
    _process_event("PERSISTENT_GRADE_SUMMARY_CHANGED", data, **kwargs)

def xblock_skill_verified_receiver(data, **kwargs):
    _process_event("XBLOCK_SKILL_VERIFIED", data, **kwargs)

def user_notification_requested_receiver(data, **kwargs):
    _process_event("USER_NOTIFICATION_REQUESTED", data, **kwargs)

def exam_attempt_submitted_receiver(data, **kwargs):
    _process_event("EXAM_ATTEMPT_SUBMITTED", data, **kwargs)

def exam_attempt_rejected_receiver(data, **kwargs):
    _process_event("EXAM_ATTEMPT_REJECTED", data, **kwargs)

def exam_attempt_verified_receiver(data, **kwargs):
    _process_event("EXAM_ATTEMPT_VERIFIED", data, **kwargs)

def exam_attempt_errored_receiver(data, **kwargs):
    _process_event("EXAM_ATTEMPT_ERRORED", data, **kwargs)

def exam_attempt_reset_receiver(data, **kwargs):
    _process_event("EXAM_ATTEMPT_RESET", data, **kwargs)

def course_access_role_added_receiver(data, **kwargs):
    _process_event("COURSE_ACCESS_ROLE_ADDED", data, **kwargs)

def course_access_role_removed_receiver(data, **kwargs):
    _process_event("COURSE_ACCESS_ROLE_REMOVED", data, **kwargs)

def forum_thread_created_receiver(data, **kwargs):
    _process_event("FORUM_THREAD_CREATED", data, **kwargs)

def forum_thread_response_created_receiver(data, **kwargs):
    _process_event("FORUM_THREAD_RESPONSE_CREATED", data, **kwargs)

def forum_response_comment_created_receiver(data, **kwargs):
    _process_event("FORUM_RESPONSE_COMMENT_CREATED", data, **kwargs)

def course_notification_requested_receiver(data, **kwargs):
    _process_event("COURSE_NOTIFICATION_REQUESTED", data, **kwargs)

def ora_submission_created_receiver(data, **kwargs):
    _process_event("ORA_SUBMISSION_CREATED", data, **kwargs)

def course_passing_status_updated_receiver(data, **kwargs):
    _process_event("COURSE_PASSING_STATUS_UPDATED", data, **kwargs)

def ccx_course_passing_status_updated_receiver(data, **kwargs):
    _process_event("CCX_COURSE_PASSING_STATUS_UPDATED", data, **kwargs)

def badge_awarded_receiver(data, **kwargs):
    _process_event("BADGE_AWARDED", data, **kwargs)

def badge_revoked_receiver(data, **kwargs):
    _process_event("BADGE_REVOKED", data, **kwargs)

# def idv_attempt_created_receiver(data, **kwargs):
#     _process_event("IDV_ATTEMPT_CREATED", data, **kwargs)
#
# def idv_attempt_pending_receiver(data, **kwargs):
#     _process_event("IDV_ATTEMPT_PENDING", data, **kwargs)
#
# def idv_attempt_approved_receiver(data, **kwargs):
#     _process_event("IDV_ATTEMPT_APPROVED", data, **kwargs)
#
# def idv_attempt_denied_receiver(data, **kwargs):
#     _process_event("IDV_ATTEMPT_DENIED", data, **kwargs)

#
# Course authoring

def course_catalog_info_changed_receiver(data, **kwargs):
    _process_event("COURSE_CATALOG_INFO_CHANGED", data, **kwargs)

def xblock_created_receiver(data, **kwargs):
    _process_event("XBLOCK_CREATED", data, **kwargs)

def xblock_updated_receiver(data, **kwargs):
    _process_event("XBLOCK_UPDATED", data, **kwargs)

def xblock_published_receiver(data, **kwargs):
    _process_event("XBLOCK_PUBLISHED", data, **kwargs)

def xblock_deleted_receiver(data, **kwargs):
    _process_event("XBLOCK_DELETED", data, **kwargs)

def xblock_duplicated_receiver(data, **kwargs):
    _process_event("XBLOCK_DUPLICATED", data, **kwargs)

def course_certificate_config_changed_receiver(data, **kwargs):
    _process_event("COURSE_CERTIFICATE_CONFIG_CHANGED", data, **kwargs)

def course_certificate_config_deleted_receiver(data, **kwargs):
    _process_event("COURSE_CERTIFICATE_CONFIG_DELETED", data, **kwargs)

def course_created_receiver(data, **kwargs):
    _process_event("COURSE_CREATED", data, **kwargs)

def content_library_created_receiver(data, **kwargs):
    _process_event("CONTENT_LIBRARY_CREATED", data, **kwargs)

def content_library_updated_receiver(data, **kwargs):
    _process_event("CONTENT_LIBRARY_UPDATED", data, **kwargs)

def content_library_deleted_receiver(data, **kwargs):
    _process_event("CONTENT_LIBRARY_DELETED", data, **kwargs)

def library_block_created_receiver(data, **kwargs):
    _process_event("LIBRARY_BLOCK_CREATED", data, **kwargs)

def library_block_updated_receiver(data, **kwargs):
    _process_event("LIBRARY_BLOCK_UPDATED", data, **kwargs)

def library_block_deleted_receiver(data, **kwargs):
    _process_event("LIBRARY_BLOCK_DELETED", data, **kwargs)

def content_object_associations_changed_receiver(data, **kwargs):
    _process_event("CONTENT_OBJECT_ASSOCIATIONS_CHANGED", data, **kwargs)

def content_object_tags_changed_receiver(data, **kwargs):
    _process_event("CONTENT_OBJECT_TAGS_CHANGED", data, **kwargs)

def library_collection_created_receiver(data, **kwargs):
    _process_event("LIBRARY_COLLECTION_CREATED", data, **kwargs)

def library_collection_updated_receiver(data, **kwargs):
    _process_event("LIBRARY_COLLECTION_UPDATED", data, **kwargs)

def library_collection_deleted_receiver(data, **kwargs):
    _process_event("LIBRARY_COLLECTION_DELETED", data, **kwargs)

def library_container_created_receiver(data, **kwargs):
    _process_event("LIBRARY_CONTAINER_CREATED", data, **kwargs)

def library_container_updated_receiver(data, **kwargs):
    _process_event("LIBRARY_CONTAINER_UPDATED", data, **kwargs)

def library_container_deleted_receiver(data, **kwargs): _process_event("LIBRARY_CONTAINER_DELETED", data, **kwargs)

def course_import_completed_receiver(data, **kwargs):
    _process_event("COURSE_IMPORT_COMPLETED", data, **kwargs)
