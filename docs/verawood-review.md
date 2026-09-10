# Verawood upgrade and code review

Reviewed on 2026-09-10. Scope: all runtime modules, plugin registration/settings,
models and migrations, packaging/dependency locks, CI/release workflows,
documentation configuration, and tests. Generated artifacts and the existing local
SQLite database were not used as migration targets. No deployment or publication
was performed.

## Upstream baseline

The comparison uses the platform's pinned dependencies, not the latest development
versions of the hooks libraries:

| Component | Ulmo | Verawood |
| --- | --- | --- |
| Platform revision inspected | `e66e4ebbf7fa831c306ef2e45b8b36766b6500ed` | `259473c5dfd1c82eac5e6c4d14bf6095cb25824d` |
| openedx-events | 10.5.0 | 11.2.0 |
| openedx-filters | 2.1.0 | 3.4.1 |
| Django | 5.2.11 | 5.2.13 |
| Extension Python baseline | 3.11 | 3.12 (required by openedx-events 11.2.0) |

Runtime locks also match Verawood's direct dependency versions for attrs (26.1.0),
edx-opaque-keys (4.0.0), XBlock (6.1.0), django-model-utils (5.0.0), and requests
(2.33.1), with urllib3 2.6.3. The package metadata permits compatible versions so
it can coexist with the platform's own dependency resolution.

Sources: [Ulmo requirements](https://github.com/openedx/edx-platform/blob/e66e4ebbf7fa831c306ef2e45b8b36766b6500ed/requirements/edx/base.txt),
[Verawood requirements](https://github.com/openedx/edx-platform/blob/259473c5dfd1c82eac5e6c4d14bf6095cb25824d/requirements/edx/base.txt),
[event package metadata](https://github.com/openedx/openedx-events/blob/v11.2.0/setup.py).

### Filter comparison

All 24 previously registered learning/content-authoring filter types remain in
openedx-filters 3.4.1. Their callable arguments are unchanged. Three filters were
added; the extension now registers all 27 public filters in these two domains.

| New handler | Exact upstream filter type | Supported response behavior |
| --- | --- | --- |
| `InstructorDashboardTabsRequested` | `org.openedx.learning.instructor.dashboard.tabs.requested.v1` | Replace `tabs`, including with an empty list; support `PreventTabsGeneration` with optional custom tabs. Preserve user and course objects. |
| `AccountSettingsReadOnlyFieldsRequested` | `org.openedx.learning.account.settings.read_only_fields.requested.v1` | Add JSON field names to the existing Python set; preserve the user object. |
| `GradeEventContextRequested` | `org.openedx.learning.grade.context.requested.v1` | Merge `context`; preserve `user_id` and `course_id`. |

Source: [versioned filter definitions](https://github.com/openedx/openedx-filters/blob/v3.4.1/openedx_filters/learning/filters.py).

`InstructorDashboardRenderStarted` is retained upstream with a deprecation note
and only serves the legacy instructor dashboard. The new MFE does not execute it.
Existing customizations need a new tabs endpoint configuration and, for custom
content rendered inside the MFE, frontend plugin configuration. Automatically
renaming old dashboard configurations would give existing endpoints incompatible
payloads, so the migration deliberately retains them.

The [release notes](https://docs.openedx.org/en/latest/community/release_notes/verawood/dev_op_release_notes.html)
mention `tabs.generated.v1`, but both the pinned package and
[platform serializer](https://github.com/openedx/edx-platform/blob/259473c5dfd1c82eac5e6c4d14bf6095cb25824d/lms/djangoapps/instructor/views/serializers_v2.py)
use `InstructorDashboardTabsRequested` / `tabs.requested.v1`. The implementation
follows executable source. The new account restrictions filter is also invoked in
the pinned [account API](https://github.com/openedx/edx-platform/blob/259473c5dfd1c82eac5e6c4d14bf6095cb25824d/openedx/core/djangoapps/user_api/accounts/api.py).

A search of the full pinned platform source found no caller for
`GradeEventContextRequested`, `CourseEnrollmentQuerysetRequested`, or
`AccountSettingsRenderStarted`. These remain available in the filter library and
are supported here, but registering them does not cause stock Verawood to execute
them. In particular, grade enrichment needs an upstream/custom caller before it
will send requests. The legacy ORA submission-view filter is supplied by the
separate `edx-ora2` component rather than the platform tree. Hook availability and
actual invocation are distinct; do not treat the registration count as a guarantee
that every filter fires in every deployment.

The ORA caller is confirmed in the pinned
[ora2 7.1.0 legacy submission view](https://github.com/openedx/edx-ora2/blob/v7.1.0/openassessment/xblock/ui_mixins/legacy/views/submission.py).
The absent legacy account-render caller is not a new removal introduced by this
upgrade: its documented `accounts/settings_views.py` path is also absent at the
inspected Ulmo revision.

### Event comparison

Learning and content-authoring signal definitions and receiver argument names are
unchanged between openedx-events 10.5.0 and 11.2.0. The new `authz` domain adds
`ROLE_ASSIGNMENT_CREATED` and `ROLE_ASSIGNMENT_DELETED`; both accept
`role_assignment: RoleAssignmentData` and are registered in LMS and Studio.
The extension covers all 66 signals in learning, content_authoring, and authz.
Enterprise and analytics domains remain outside this extension's existing scope.

Sources: [learning signals](https://github.com/openedx/openedx-events/blob/v11.2.0/openedx_events/learning/signals.py),
[authoring signals](https://github.com/openedx/openedx-events/blob/v11.2.0/openedx_events/content_authoring/signals.py),
[authorization signals](https://github.com/openedx/openedx-events/blob/v11.2.0/openedx_events/authz/signals.py).

Payload changes in [learning data](https://github.com/openedx/openedx-events/blob/v11.2.0/openedx_events/learning/data.py):

- `CourseDiscussionConfigurationData` adds `enabled`; it is forwarded unchanged.
- `DiscussionThreadData.id` is now a string. Several fields are optional and
  default to `None`, including `discussion`, which formerly defaulted to `{}`.
- Notification/discussion/ORA dictionaries and lists have more specific nested
  type annotations. Their JSON shapes remain compatible with generic serialization.
- Content-authoring data definitions are unchanged.

Existing event payloads keep the fully qualified data-class key and
`event_metadata`. Consumers should accept the additional discussion field,
string forum IDs, and null optional fields.

## Review findings and fixes

| Priority | Finding | Resolution |
| --- | --- | --- |
| High | Python 3.11 cannot install Verawood's event package. Locked development dependencies still selected Django 4.2 and Ulmo hook libraries. | Require Python 3.12 and Django 5.2; bound hook dependencies to tested major versions and refresh locks, CI, and documentation runtime. |
| High | Ten admin choice values differed from the event names queried by handlers, silently disabling their delivery. | Derive choices from handler names and migrate existing aliases while preserving primary keys, URLs, and controls. |
| High | Importing the Studio URL filter imported LMS courseware and student models immediately. | Defer platform-only imports until the relevant LMS filter executes; test importability without LMS packages. |
| High | User model serialization sent password hashes. Registration logged whole forms; event delivery logged full PII payloads. | Recursively omit credential keys, remove full-payload/form logging, and remove hashes from examples. |
| High | Remote model updates could overwrite credentials, privileges, primary-key aliases, and relationships. | Restrict writes to concrete non-relational, non-primary-key fields, excluding credential and privilege fields. Keep intended profile updates. |
| High | Login/enrollment/certificate/cohort filters applied returned updates before checking a requested denial. | Check prevention exceptions before changing user or cohort objects. A denied login now leaves the stored user unchanged. |
| High | HTTP-error and timeout halting passed unsupported arguments to upstream exceptions; timeout messages used `strerror`. | Match actual constructor signatures and use the request exception's string message. |
| Medium | Queryset hooks passed the unspecialized queryset to the endpoint, called `.filter(dict)` instead of `.filter(**dict)`, and enrollment filtering discarded its return value. | Send serialized rows, apply keyword lookups to the original queryset, and return the filtered queryset. Avoid evaluation when no endpoint exists. |
| Medium | JSON `null`, lists, and scalars could crash response processing. | Validate the response envelope before reading its keys. |
| Medium | Account and instructor custom-response exceptions received incorrect response objects. | Construct Django `HttpResponse` consistently for all supported custom-response exceptions. |
| Medium | One failed signal delivery skipped subsequent configured subscribers. HTTP error statuses were ignored. | Catch request/HTTP failures per endpoint, log failure without the payload, and continue. |
| Medium | Repeated settings initialization duplicated pipeline steps and silently skipped registration if the setting was absent. | Initialize missing configuration and merge each step once while preserving other plugins and settings. |
| Medium | JSON booleans caused `.lower()` errors; returned form values could append incorrectly. | Accept real booleans and boolean strings, replace QueryDict values, and support list values. |
| Medium | Partial course-about responses replaced the entire context; nested object serialization could lose structure or recurse indefinitely. | Merge context while retaining course objects, serialize nested objects/attrs with a depth limit, and stringify dictionary keys. |
| Low | Course IDs were reconstructed as `course-v1`, which corrupted legacy/CCX keys. | Use the opaque key's canonical string representation. |
| Low | Multiple endpoint order was unspecified; filter timestamps lacked an explicit timezone. | Order configurations by primary key and use aware UTC metadata timestamps. |
| Low | Documentation build dependencies were installed at runtime; wheel metadata advertised a universal Python 2/3 wheel. | Move the theme to documentation requirements, exclude test utility packages, and produce a Python 3 wheel. |

## Migration and deployment

`0008_verawood` updates choices, sets filter ordering, and normalizes these existing
aliases:

| Previous stored event | Correct handler event |
| --- | --- |
| StudentSettingsRenderStarted | AccountSettingsRenderStarted |
| XblockRenderStarted | RenderXBlockStarted |
| CourseHomepageUrlCreationStarted | CourseHomeUrlCreationStarted |
| HomeEnrollmentApiRendered | CourseEnrollmentAPIRenderStarted |
| HomeCourserunApiRenderedStarted | CourseRunAPIRenderStarted |
| OraSubmissionViewRenderStarted | ORASubmissionViewRenderStarted |
| IdvPageUrlRequested | IDVPageURLRequested |
| CourseAboutPageUrlRequested | CourseAboutPageURLRequested |
| ScheduleQuerysetRequested | ScheduleQuerySetRequested |
| AuthoringLmsPageUrlRequested | LMSPageURLRequested |

Already canonical rows are untouched. A reverse migration intentionally does not
restore broken aliases: their provenance cannot be distinguished from rows that
already used the canonical names. As with any release upgrade, preserve a database
backup for rollback. The new migration has only been executed against temporary
test databases during this review.

Before rollout, review enabled endpoints for the corrected aliases: configurations
that were inert will now execute. Install version 22 in the Verawood image, migrate
the shared database, and restart LMS, Studio, and workers. Keep version 21 on Ulmo.
Review consumers that depended on credential fields or remote privilege changes,
which this release intentionally removes.

## Verification and remaining limits

Completed checks: 90 tests passing with 93% reported coverage; Django system checks;
no missing migrations; pylint, pycodestyle, pydocstyle and import-order checks;
documentation lint and a Sphinx build with warnings treated as errors; 100% model
PII annotation coverage; source distribution and Python 3 wheel builds and Twine
metadata checks. The legacy pylint configuration emits a non-failing warning about
its `overgeneral-exceptions` option. Packaging also emits existing setuptools
license-classifier and empty-asset-pattern warnings.

Regression tests exercise real upstream filter runners, signal dispatch, receiver
signatures, queryset filtering with Django models, error controls, privacy handling,
new event data, and historical migration state. Platform-specific profile constants
and completion lookup are stubbed in standalone enabled-filter tests; the filters
library, event library, Django models, and migration executor are real.

This is package-level compatibility validation, not a deployed Open edX acceptance
test. Staging should verify LMS login/registration/enrollment/certificates, Studio
URL filtering and role assignments, account API restrictions, and new instructor
dashboard tabs with the actual configured external endpoints.

Existing architectural constraints remain: delivery is synchronous and has no
durable retries or delivery history. Each endpoint uses a ten-second connect/read
timeout (not a total workflow deadline), so slow endpoints add latency. URLs and
responses are administrator-trusted; there is no destination allowlist, request
signature, or general schema validation for every legacy response. The ten-second
timeout and per-subscriber isolation do not make delivery durable. Filters with no
upstream exception cannot use transport-error controls to halt. Local event
registration also does not enable event-bus publication or subscription by itself.
