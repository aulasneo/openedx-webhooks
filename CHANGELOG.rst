Change Log
##########

Version 19.0.1 (2025-05-08)
**********************************************

Fix signal argument names.

Version 19.0.0 (2025-04-28)
**********************************************

* Feat: Add new filters for Sumac:
    * ORASubmissionViewRenderStarted
    * IDVPageURLRequested
    * CourseAboutPageURLRequested
    * ScheduleQuerySetRequested
    * LMSPageURLRequested
* Feat: Add new signal receivers for Sumac:
    * IDV_ATTEMPT_CREATED
    * IDV_ATTEMPT_PENDING
    * IDV_ATTEMPT_APPROVED
    * IDV_ATTEMPT_DENIED

Version 18.0.0 (2025-04-21)
**********************************************

* Fix: Fix return value of all filters
* Feat: Add new filters and receivers for Redwood

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
