# coding=utf-8
"""
Common Pluggable Django App settings.

"""


def plugin_settings(settings):
    """
    Inject local settings into django settings.
    """

    settings.OPEN_EDX_FILTERS_CONFIG = {
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
    }
