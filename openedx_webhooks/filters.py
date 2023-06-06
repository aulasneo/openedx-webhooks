import logging

from openedx_filters import PipelineStep
from openedx_filters.learning.filters import (
    AccountSettingsRenderStarted,
    CertificateCreationRequested,
    CertificateRenderStarted,
    CohortAssignmentRequested,
    CohortChangeRequested,
    CourseAboutRenderStarted,
    CourseEnrollmentStarted,
    CourseUnenrollmentStarted,
    DashboardRenderStarted,
    StudentLoginRequested,
    StudentRegistrationRequested,
)

logger = logging.getLogger(__name__)


class StudentLoginRequested(PipelineStep):
    """
    Process StudentLoginRequested filter.
    """

    def run_filter(self, user, *args, **kwargs):
        logger.info(f"Webfilter for StudentLoginRequested event for user {user}")
        return {"user": user}
