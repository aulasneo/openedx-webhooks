Change Log
##########

Unreleased
**********************************************

* Fix: Fix return value of all filters
* Feat: Add new filters:
    * VerticalBlockChildRenderStarted,
    * CourseEnrollmentQuerysetRequested,
    * RenderXBlockStarted
    * VerticalBlockRenderCompleted
    * CourseHomeUrlCreationStarted
    * CourseEnrollmentAPIRenderStarted
    * CourseRunAPIRenderStarted
    * InstructorDashboardRenderStarted
    * ORASubmissionViewRenderStarted
    * IDVPageURLRequested
    * CourseAboutPageURLRequested
    * ScheduleQuerySetRequested
* Feat: Add new event receivers:
    * PERSISTENT_GRADE_SUMMARY_CHANGED
    * XBLOCK_SKILL_VERIFIED
    * USER_NOTIFICATION_REQUESTED
    * EXAM_ATTEMPT_SUBMITTED
    * EXAM_ATTEMPT_REJECTED
    * EXAM_ATTEMPT_VERIFIED
    * EXAM_ATTEMPT_ERRORED
    * EXAM_ATTEMPT_RESET
    * COURSE_ACCESS_ROLE_ADDED
    * COURSE_ACCESS_ROLE_REMOVED
    * FORUM_THREAD_CREATED
    * FORUM_THREAD_RESPONSE_CREATED
    * FORUM_RESPONSE_COMMENT_CREATED
    * COURSE_NOTIFICATION_REQUESTED
    * ORA_SUBMISSION_CREATED
    * COURSE_PASSING_STATUS_UPDATED
    * CCX_COURSE_PASSING_STATUS_UPDATED
    * BADGE_AWARDED
    * BADGE_REVOKED
    * IDV_ATTEMPT_CREATED
    * IDV_ATTEMPT_PENDING
    * IDV_ATTEMPT_APPROVED
    * IDV_ATTEMPT_DENIED
    * COURSE_CATALOG_INFO_CHANGED
    * XBLOCK_CREATED
    * XBLOCK_UPDATED
    * XBLOCK_PUBLISHED
    * XBLOCK_DELETED
    * XBLOCK_DUPLICATED
    * COURSE_CERTIFICATE_CONFIG_CHANGED
    * COURSE_CERTIFICATE_CONFIG_DELETED
    * COURSE_CREATED
    * CONTENT_LIBRARY_CREATED
    * CONTENT_LIBRARY_UPDATED
    * CONTENT_LIBRARY_DELETED
    * LIBRARY_BLOCK_CREATED
    * LIBRARY_BLOCK_UPDATED
    * LIBRARY_BLOCK_DELETED
    * CONTENT_OBJECT_ASSOCIATIONS_CHANGED
    * CONTENT_OBJECT_TAGS_CHANGED
    * LIBRARY_COLLECTION_CREATED
    * LIBRARY_COLLECTION_UPDATED
    * LIBRARY_COLLECTION_DELETED
    * LIBRARY_CONTAINER_CREATED
    * LIBRARY_CONTAINER_UPDATED
    * LIBRARY_CONTAINER_DELETED
    * COURSE_IMPORT_COMPLETED


Version 1.0.2 (2025-04-07)
**********************************************

* Fix: return {} in run_filter

Version 1.0.1 (2023-08-15)
**********************************************

* Fix: remove non implemented filters

Version 1.0.0 (2023-08-15)
**********************************************

* Added webfilters:
    * CertificateCreationRequested,
    * CertificateRenderStarted,
    * CohortAssignmentRequested,
    * CohortChangeRequested,
    * CourseAboutRenderStarted,
    * CourseEnrollmentStarted,
    * CourseUnenrollmentStarted,
    * DashboardRenderStarted,
    * StudentLoginRequested,
    * StudentRegistrationRequested,

* Available webhooks:
    * SESSION_LOGIN_COMPLETED
    * STUDENT_REGISTRATION_COMPLETED
    * COURSE_ENROLLMENT_CREATED
    * COURSE_ENROLLMENT_CHANGED
    * COURSE_UNENROLLMENT_COMPLETED
    * CERTIFICATE_CREATED
    * CERTIFICATE_CHANGED
    * CERTIFICATE_REVOKED
    * COHORT_MEMBERSHIP_CHANGED
    * COURSE_DISCUSSIONS_CHANGED


Version 0.2.1 (2023-06-06)
**********************************************

* Renamed package to openedx_webhooks. Upload to PyPI.

Version 0.1.1 (2023-06-05)
**********************************************

* Improve documentation

0.1.0 – 2023-05-31
**********************************************

Added
=====

* First release on PyPI.
