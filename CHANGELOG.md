# Change Log

## Version 22.0.0 (2026-09-10)

- Target Open edX Verawood: Python 3.12, Django 5.2, openedx-events 11.2.0,
  and openedx-filters 3.4.1. Refresh dependency locks and CI/documentation runtimes.
- Add `InstructorDashboardTabsRequested`, `AccountSettingsReadOnlyFieldsRequested`,
  and `GradeEventContextRequested` webfilters. Retain the legacy dashboard filter.
- Add `ROLE_ASSIGNMENT_CREATED` and `ROLE_ASSIGNMENT_DELETED` webhooks in LMS and Studio.
- Validate all learning/authoring/authz signal receiver arguments and all public
  learning/authoring filter registrations against the release-pinned libraries.
- Correct admin filter choices and migrate ten previously mismatched event names
  without changing endpoint configuration. Corrected enabled endpoints can now fire.
- Make settings initialization idempotent and Studio imports independent of LMS code.
- Fix queryset serialization, keyword lookups, and returned filtered querysets.
- Fix transport halting for upstream exception signatures, non-object JSON responses,
  custom HTTP responses, boolean updates, and partial course-about context updates.
- Omit credentials from outgoing payloads and logs, and protect model identity,
  relationships, credentials, and account privilege flags from remote updates.
- Honor login/enrollment/certificate/cohort denial responses before applying updates.
- Isolate failed signal deliveries, preserve later subscribers, and define endpoint
  ordering by configuration ID. Add regression and data migration tests.

## Version 21.0.0 (2026-04-02)

- Add Open edX Ulmo compatibility.
- Align runtime and packaging metadata with Ulmo and Tutor 21:
  - Python 3.11
  - Django 5.2
  - `openedx-filters` 2.1.0
  - `openedx-events` 10.5.0
- Add Ulmo-era missing signal receivers:
  - `LTI_PROVIDER_LAUNCH_SUCCESS`
  - `COURSE_RERUN_COMPLETED`
- Review Ulmo filter coverage against the current Open edX Filters reference:
  - no new filter types were found beyond the ones already registered here
  - no existing registered filter types were found renamed or deprecated

## 20.0.0 - 2026-03-17

- Add Open edX Teak compatibility.
- Align runtime and packaging metadata with Teak and Tutor 20:
  - Python 3.11
  - Django 4.2
  - `openedx-filters` 2.0.1
  - `openedx-events` 10.2.0
  - `edx-opaque-keys` 3.0.0
- Fix non-halting webfilter request failures so they no longer crash the caller.
- Fix `Use WWW form encoding` to send actual form-encoded payloads and honor
  the setting in both webhooks and webfilters.
- Register the plugin for both LMS and CMS, including the Studio
  `LMSPageURLRequested` filter.
- Add Teak-era missing filter support:
  - `AccountSettingsRenderStarted`
- Add Teak-era missing signal receivers:
  - `EXTERNAL_GRADER_SCORE_SUBMITTED`
  - `LIBRARY_BLOCK_PUBLISHED`
  - `LIBRARY_CONTAINER_CREATED`
  - `LIBRARY_CONTAINER_UPDATED`
  - `LIBRARY_CONTAINER_DELETED`
  - `LIBRARY_CONTAINER_PUBLISHED`
  - `COURSE_IMPORT_COMPLETED`
- Update PyPI publishing workflow to use PyPI trusted publishing.

## 19.0.1 - 2025-05-08

- Fix signal argument names.

## 19.0.0 - 2025-04-28

- Add new filters for Sumac:
  - `ORASubmissionViewRenderStarted`
  - `IDVPageURLRequested`
  - `CourseAboutPageURLRequested`
  - `ScheduleQuerySetRequested`
  - `LMSPageURLRequested`
- Add new signal receivers for Sumac:
  - `IDV_ATTEMPT_CREATED`
  - `IDV_ATTEMPT_PENDING`
  - `IDV_ATTEMPT_APPROVED`
  - `IDV_ATTEMPT_DENIED`

## 18.0.0 - 2025-04-21

- Fix return value of all filters.
- Add new filters and receivers for Redwood.

## 1.0.2 - 2025-04-07

- Return `{}` in `run_filter`.

## 1.0.1 - 2023-08-15

- Remove non-implemented filters.

## 1.0.0 - 2023-08-15

- Added webfilters:
  - `CertificateCreationRequested`
  - `CertificateRenderStarted`
  - `CohortAssignmentRequested`
  - `CohortChangeRequested`
  - `CourseAboutRenderStarted`
  - `CourseEnrollmentStarted`
  - `CourseUnenrollmentStarted`
  - `DashboardRenderStarted`
  - `StudentLoginRequested`
  - `StudentRegistrationRequested`
- Available webhooks:
  - `SESSION_LOGIN_COMPLETED`
  - `STUDENT_REGISTRATION_COMPLETED`
  - `COURSE_ENROLLMENT_CREATED`
  - `COURSE_ENROLLMENT_CHANGED`
  - `COURSE_UNENROLLMENT_COMPLETED`
  - `CERTIFICATE_CREATED`
  - `CERTIFICATE_CHANGED`
  - `CERTIFICATE_REVOKED`
  - `COHORT_MEMBERSHIP_CHANGED`
  - `COURSE_DISCUSSIONS_CHANGED`

## 0.2.1 - 2023-06-06

- Renamed package to `openedx_webhooks`. Upload to PyPI.

## 0.1.1 - 2023-06-05

- Improve documentation.

## 0.1.0 - 2023-05-31

- First release on PyPI.
