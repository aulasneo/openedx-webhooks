"""
Handlers for Open edX filters.
"""
import logging

from openedx_filters import PipelineStep

logger = logging.getLogger(__name__)


class StudentLoginRequested(PipelineStep):
    """
    Process StudentLoginRequested filter.
    """

    def run_filter(self, user):  # pylint: disable=arguments-differ
        """Execute the filter."""
        logger.info(f"Webfilter for StudentLoginRequested event for user {user}")
        return {"user": user}
