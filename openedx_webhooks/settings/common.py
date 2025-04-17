# coding=utf-8
"""
Common Pluggable Django App settings.

"""


def plugin_settings(settings):
    """
    Declare all filters and their handlers.
    """

    filters_config = {
        "org.openedx.learning.student.login.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.StudentLoginRequestedWebFilter"
            ]
        },
        "org.openedx.learning.student.registration.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.StudentRegistrationRequestedWebFilter"
            ]
        },
        "org.openedx.learning.course.enrollment.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseEnrollmentStartedWebFilter"
            ]
        },
        "org.openedx.learning.course.unenrollment.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseUnenrollmentStartedWebFilter"
            ]
        },
        "org.openedx.learning.certificate.creation.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CertificateCreationRequestedWebFilter"
            ]
        },
        "org.openedx.learning.certificate.render.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CertificateRenderStartedWebFilter"
            ]
        },
        "org.openedx.learning.cohort.change.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CohortChangeRequestedWebFilter"
            ]
        },
        "org.openedx.learning.cohort.assignment.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CohortAssignmentRequestedWebFilter"
            ]
        },
        "org.openedx.learning.course_about.render.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseAboutRenderStartedWebFilter"
            ]
        },
        "org.openedx.learning.dashboard.render.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.DashboardRenderStartedWebFilter"
            ]
        },

        "org.openedx.learning.vertical_block_child.render.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.VerticalBlockChildRenderStartedWebFilter"
            ]
        },
        "org.openedx.learning.course_enrollment_queryset.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseEnrollmentQuerysetRequestedWebFilter"
            ]
        },
        # "org.openedx.learning.xblock.render.started.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.RenderXBlockStartedWebFilter"
        #     ]
        # },
        "org.openedx.learning.vertical_block.render.completed.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.VerticalBlockRenderCompletedWebFilter"
            ]
        },
        "org.openedx.learning.course.homepage.url.creation.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseHomeUrlCreationStartedWebFilter"
            ]
        },
        "org.openedx.learning.home.enrollment.api.rendered.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseEnrollmentAPIRenderStartedWebFilter"
            ]
        },
        "org.openedx.learning.home.courserun.api.rendered.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.CourseRunAPIRenderStartedWebFilter"
            ]
        },
        "org.openedx.learning.instructor.dashboard.render.started.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_webhooks.filters.InstructorDashboardRenderStartedWebFilter"
            ]
        },
        # "org.openedx.learning.ora.submission_view.render.started.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.ORASubmissionViewRenderStartedWebFilter"
        #     ]
        # },
        # "org.openedx.learning.idv.page.url.requested.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.IDVPageURLRequestedWebFilter"
        #     ]
        # },
        # "org.openedx.learning.course_about.page.url.requested.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.CourseAboutPageURLRequestedWebFilter"
        #     ]
        # },
        # "org.openedx.learning.schedule.queryset.requested.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.ScheduleQuerySetRequestedWebFilter"
        #     ]
        # },
        # "org.openedx.content_authoring.lms.page.url.requested.v1": {
        #     "fail_silently": False,
        #     "pipeline": [
        #         "openedx_webhooks.filters.LMSPageURLRequestedWebFilter"
        #     ]
        # },

    }

    for key, filter_config in filters_config.items():
        if hasattr(settings, 'OPEN_EDX_FILTERS_CONFIG'):    # Avoid errors during build time
            if key in settings.OPEN_EDX_FILTERS_CONFIG:     # Allow other modules in the pipeline
                settings.OPEN_EDX_FILTERS_CONFIG[key]['pipeline'] += filter_config['pipeline']
            else:
                settings.OPEN_EDX_FILTERS_CONFIG[key] = filter_config
