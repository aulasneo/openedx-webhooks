"""
Handlers for Open edX filters.

Signals:
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
"""
import json
import logging
from datetime import datetime

import requests.exceptions
from common.djangoapps.student.models import UserProfile  # pylint: disable=import-error
from django.contrib.auth import get_user_model
from django.db import models
from django.http import HttpResponse
from lms.djangoapps.courseware.courses import get_course_blocks_completion_summary  # pylint: disable=import-error
from opaque_keys.edx.keys import CourseKey
from openedx_filters import PipelineStep
from openedx_filters.learning.filters import (
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
    VerticalBlockChildRenderStarted,
    CourseEnrollmentQuerysetRequested,
    RenderXBlockStarted,
    VerticalBlockRenderCompleted,
    CourseHomeUrlCreationStarted,
    CourseEnrollmentAPIRenderStarted,
    CourseRunAPIRenderStarted,
    InstructorDashboardRenderStarted,
    ORASubmissionViewRenderStarted,
    IDVPageURLRequested,
    CourseAboutPageURLRequested,
    ScheduleQuerySetRequested,
)

from .models import Webfilter
from .utils import send

logger = logging.getLogger(__name__)


def fix_dict_keys(d: dict):
    """
    Remove dict keys from a dict.

    This fixes a problem with course objects, for which vars(course) or course.__dict__ return a dict
    which contains dicts as keys, and are therefore not json serializable.
    We convert these dicts in place of keys, to their str representation.
    """
    # Initialize the response
    r = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = fix_dict_keys(v)
        if type(k) not in [str, int, float]:
            r[str(k)] = v
        else:
            r[k] = v
    return r


def _process_filter(webfilters, data, exception=None):
    """
    Process all events with user data.
    """
    response_data = {}
    response_exceptions = {}

    # Convert model objects to dicts, and remove '_state'
    payload = {}
    for key, value in data.items():

        if isinstance(value, models.Model):
            payload[key] = value.__dict__.copy()
            payload[key].pop('_state', None)
        elif isinstance(value, dict):
            payload[key] = fix_dict_keys(value)
        else:
            payload[key] = value

    for webfilter in webfilters:
        logger.info(f"{webfilter.event} webhook filter triggered to {webfilter.webhook_url}")

        # Add event metadata
        payload['event_metadata'] = {
            'event_type': webfilter.event,
            'time': str(datetime.now())
        }

        try:
            # Send the request to the webhook URL
            response = send(webfilter.webhook_url, payload)

        except requests.exceptions.RequestException as e:
            if webfilter.halt_on_request_exception and exception:
                logger.info(f"Halting on request exception '{e.strerror}'. "
                            f"{webfilter.event} webhook filter triggered to {webfilter.webhook_url}")
                raise exception(
                    message=e.strerror,
                    redirect_to=webfilter.redirect_on_request_exception,
                ) from e
            logger.info(f"Not halting on request exception '{e}'."
                        f"{webfilter.event} webhook filter triggered to {webfilter.webhook_url}")
            return None, None

        if 400 <= response.status_code <= 499 and webfilter.halt_on_4xx and exception:
            logger.info(f"Request to {webfilter.webhook_url} after webhook event {webfilter.event} returned status "
                        f"code {response.status_code} ({response.reason}). Redirecting to {webfilter.redirect_on_4xx}")
            raise exception(
                message=f"Request to {webfilter.webhook_url} after webhook event {webfilter.event} returned status "
                        f"code {response.status_code} ({response.reason})",
                redirect_to=webfilter.redirect_on_4xx,
                status_code=response.status_code
            )

        if 500 <= response.status_code <= 599 and webfilter.halt_on_5xx and exception:
            logger.info(f"Request to {webfilter.webhook_url} after webhook event {webfilter.event} returned status "
                        f"code {response.status_code} ({response.reason}). Redirecting to {webfilter.redirect_on_5xx}")
            raise exception(
                message=f"Request to {webfilter.webhook_url} after webhook event {webfilter.event} returned status "
                        f"code {response.status_code} ({response.reason})",
                redirect_to=webfilter.redirect_on_5xx,
                status_code=response.status_code
            )

        logger.info(f"Request to {webfilter.webhook_url} after webhook event {webfilter.event} returned status code "
                    f"{response.status_code} ({response.reason}).")

        try:
            response = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            logger.warning(f"Non JSON response received from {webfilter.webhook_url}: '{response.text}' ({e})")
            response = {}

        if not webfilter.disable_filtering:
            # We need to accumulate the responses in case there are many webhook filters
            if 'data' in response:
                r = response.get('data')
                if isinstance(r, dict):
                    response_data.update(r)
                else:
                    logger.error(f"Web filter {webfilter.event} enabled but "
                                 f"call to {webfilter.webhook_url} returned non dict 'data' key: {r}")
            else:
                logger.warning(f"Web filter {webfilter.event} enabled but "
                               f"call to {webfilter.webhook_url} returned no 'data' key.")

        if not webfilter.disable_halt:
            # We accumulate the exceptions requested when enabled. Only one will work
            if 'exception' in response:
                r = response.get('exception')
                if isinstance(r, dict):
                    response_exceptions.update(r)
                else:
                    logger.error(f"Web filter {webfilter.event} exceptions enabled but "
                                 f"call to {webfilter.webhook_url} returned non dict 'exception' key: {r}")
            else:
                logger.warning(f"Web filter {webfilter.event} exceptions enabled but "
                               f"call to {webfilter.webhook_url} returned no 'exception' key.")

    return response_data, response_exceptions


def update_model(instance, data):
    """Update a model with data."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key != "id":  # Prevent changing the id of the object
                logger.info(f"Updating {instance} with {key}={value}")
                if isinstance(getattr(instance, key), datetime):
                    # Handle date time data
                    setattr(instance, key, datetime.fromisoformat(value))
                else:
                    setattr(instance, key, value)
        instance.save()


def update_query_dict(query_dict, data):
    """
    Update a QueryDict object with dict with data.

    We need a special function to update a query dict because the update method will append the new data
    instead of replacing it.
    See https://docs.djangoproject.com/en/4.2/ref/request-response/#django.http.QueryDict.update.
    """
    result = query_dict.copy()

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(query_dict.get(key), datetime):
                # Handle date time data
                result[key] = datetime.fromisoformat(value)
            else:
                result[key] = value

    return result


def update_object(o, data):
    """
    Update a generic object with dict with data.

    """
    try:
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(getattr(o, key), datetime):
                    # Handle date time data
                    setattr(o, key, datetime.fromisoformat(value))
                elif isinstance(getattr(o, key), bool):
                    setattr(o, key, value.lower() == 'true')
                else:
                    setattr(o, key, value)
    except AttributeError as e:
        logger.error(f"Error '{e} updating {o} with {data}")


def _check_for_exception(exceptions, exception_class):
    """
    Check if an exception configuration exists and then raises the exception.
    """
    if exception_class and exception_class.__name__ in exceptions:
        exception_settings = exceptions.get(exception_class.__name__)

        # In the special case of CertificateRenderStarted.RenderCustomResponse the exception must include a
        # response object
        if exception_class in [
            CertificateRenderStarted.RenderCustomResponse,
            CourseAboutRenderStarted.RenderCustomResponse,
            DashboardRenderStarted.RenderCustomResponse
        ]:
            raise exception_class(
                message="Render Custom Response",
                response=HttpResponse(**exception_settings))

        if isinstance(exception_settings, str):
            raise exception_class(exception_settings)
        if isinstance(exception_settings, dict):
            if 'message' not in exception_settings:
                exception_settings['message'] = ''
            raise exception_class(**exception_settings)
        raise exception_class("Reason not specified")


class StudentLoginRequestedWebFilter(PipelineStep):
    """
    Process StudentLoginRequested filter.

    This filter is triggered when a user attempts to log in.

    I will POST a json to the webhook url with the user and profile information

    EXAMPLE::

        {
            "user": {
                "id": 4,
                "password": "pbkdf2_sha256$260000$W2SQQzln5u3i20SYeShEWx$4Y/Th225xS25wvWG1GyHpRAj2f3Ick4/a4jbAFvsudY=",
                "last_login": "2023-06-07 20:26:39.890251+00:00",
                "is_superuser": true,
                "username": "myuser",
                "first_name": "",
                "last_name": "",
                "email": "myemail@aulasneo.com",
                "is_staff": true,
                "is_active": true,
                "date_joined": "2023-01-26 16:22:57.939766+00:00"
            },
            "profile": {
                "id": 2,
                "user_id": 4,
                "name": "Andrés González",
                "meta": "",
                "courseware": "course.xml",
                "language": "",
                "location": "",
                "year_of_birth": null,
                "gender": null,
                "level_of_education": null,
                "mailing_address": null,
                "city": null,
                "country": null,
                "state": null,
                "goals": null,
                "bio": null,
                "profile_image_uploaded_at": null,
                "phone_number": null
            }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "user": {
                    <key>:<value>,...
                },
                "profile": {
                    <key>:<value>,...
                },
            },
            "exception": {
                "PreventLogin": {
                    "message":<message>,
                    "redirect_to": <redirect URL>,
                    "error_code": <error code>,
                    "context": {
                        <context key>: <context value>,...
                    }
                }
            }
        }

    "user" and "profile" keys are optionals, as well as the keys inside each.

    "PreventLogin" can be a json as in the example or a string value with the message text,
    leaving the other keys empty.

    EXAMPLE::

        ...
        "exception": {
            "PreventLogin": <message>
        }
        ...

    PreventLogin exception accepts message, redirect_to, error_code and context.
    """

    def run_filter(self, user):  # pylint: disable=arguments-differ
        """Execute the filter."""
        event = "StudentLoginRequested"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event for user {user}")

            if user:
                # If the log in attempt is unsuccessfull, the user object will be None
                content, exceptions = _process_filter(webfilters=webfilters,
                                                      data={
                                                          "user": user,
                                                          "profile": user.profile,
                                                      },
                                                      exception=StudentLoginRequested.PreventLogin)

                update_model(user, content.get('user'))
                update_model(user.profile, content.get('profile'))
            else:
                content, exceptions = _process_filter(webfilters=webfilters,
                                                      data={},
                                                      exception=StudentLoginRequested.PreventLogin)

            _check_for_exception(exceptions, StudentLoginRequested.PreventLogin)

        return {"user": user}


class StudentRegistrationRequestedWebFilter(PipelineStep):
    """
    Process StudentRegistrationRequested filter.

    This filter is triggered when a new user submits the registration form.

    It will POST a json to the webhook url with the user and profile information.

    EXAMPLE::

        {
            "next": "/",
            "email": "test@aulasneo.com",
            "name": "Full Name",
            "username": "public_name",
            "level_of_education": "",
            "gender": "",
            "year_of_birth": "",
            "mailing_address": "",
            "goals": "",
            "terms_of_service": "true"
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "form_data": {
                    <key>:<value>,...
                },
            },
            "exception": {
                "PreventRegistration": {
                    "message":<message>,
                    "redirect_to": <redirect URL>,
                    "error_code": <error code>,
                    "context": {
                        <context key>: <context value>,...
                    }
                }
            }
        }

    "user" and "profile" keys are optionals, as well as the keys inside each.

    "PreventRegistration" can be a json as in the example or a string value with the message text,
    leaving the other keys empty.

    EXAMPLE::

        ...
        "exception": {
            "PreventRegistration": <message>
        }
        ...

    PreventRegistration accepts message and status_code. If status_code==200 then the registration is accepted.

    Notes:
        - level_of_education must be one of
            p: Doctorate,
            m: Master's or professional degree,
            b: Bachelor's degree,
            a: Associate degree,
            hs: Secondary/high school,
            jhs: Junior secondary/junior high/middle school,
            el: Elementary/primary school,
            none: No formal education,
            other: Other education
        - gender must be one of:
            m: male
            f: female
            o: other
        - terms_of_service must be true or false

        Due to privacy control, the password cannot be seen nor modified.
    """

    def run_filter(self, form_data):  # pylint: disable=arguments-differ
        """Execute the filter."""
        event = "StudentRegistrationRequested"
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event. Form data: {form_data}.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=form_data,
                                                  exception=StudentRegistrationRequested.PreventRegistration)

            form_data_response = content.get('form_data')

            # Validate form data response
            if 'level_of_education' in form_data_response \
                and form_data_response.get('level_of_education') not in \
                    [choice[0] for choice in UserProfile.LEVEL_OF_EDUCATION_CHOICES]:
                raise ValueError(f"'{form_data_response.get('level_of_education')}' is not a valid level of education."
                                 f"Valid options are: " +
                                 ", ".join([f"{c[0]}: {c[1]}" for c in UserProfile.LEVEL_OF_EDUCATION_CHOICES]))

            if 'gender' in form_data_response \
                and form_data_response.get('gender') not in \
                    [choice[0] for choice in UserProfile.GENDER_CHOICES]:
                raise ValueError(f"'{form_data_response.get('gender')}' is not a valid gender."
                                 f"Valid options are: " +
                                 ", ".join([f"{c[0]}: {c[1]}" for c in UserProfile.GENDER_CHOICES]))

            if 'terms_of_service' in form_data_response \
                    and form_data_response.get('terms_of_service').lower() not in ["true", "false"]:
                raise ValueError(f"'{form_data_response.get('terms_of_service')}' is not a boolean value."
                                 f"Valid options are: " +
                                 ", ".join(["true", "false"]))

            updated_form_data = update_query_dict(form_data, form_data_response)

            _check_for_exception(exceptions, StudentRegistrationRequested.PreventRegistration)

            return {"form_data": updated_form_data}

        return {"form_data": form_data}


class CourseEnrollmentStartedWebFilter(PipelineStep):
    """
    Process CourseEnrollmentStarted filter.

    This filter is triggered when a user is enrolled in a course.

    It will POST a json to the webhook url with information about the user, the profile, the course id and mode.

    EXAMPLE::

        {
          "user": {
            "id": 4,
            "password": "pbkdf2_sha256$260000$W2SQQzln5u3i20SYeShEWx$4Y/Th225xS25wvWG1GyHpRAj2f3Ick4/a4jbAFvsudY=",
            "last_login": "2023-06-13 15:04:10.629206+00:00",
            "is_superuser": true,
            "username": "andres",
            "first_name": "",
            "last_name": "",
            "email": "andres@aulasneo.com",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2023-01-26 16:22:57.939766+00:00"
          },
          "profile": {
            "id": 2,
            "user_id": 4,
            "name": "Andrés González",
            "meta": "",
            "courseware": "course.xml",
            "language": "",
            "location": "",
            "year_of_birth": null,
            "gender": null,
            "level_of_education": null,
            "mailing_address": null,
            "city": null,
            "country": null,
            "state": null,
            "goals": null,
            "bio": null,
            "profile_image_uploaded_at": null,
            "phone_number": null
          },
          "course_key": "course-v1:test+test+test",
          "mode": "honor",
          "event_metadata": {
            "event_type": "CourseEnrollmentStarted",
            "time": "2023-06-13 20:59:26.093379"
          }
        }

    The webhook processor can return a json with any data to modify.

    EXAMPLE::

        {
            "data": {
                "mode": "audit"
            },
            "exception": {
                "PreventEnrollment": "Enrollment not allowed"
            }
        }

    All keys are optional, as well as the keys inside each.

    "PreventEnrollment" can have a message to be logged.

    EXAMPLE::

        ...
        "exception": {
            "PreventEnrollment": <message>
        }
        ...

    PreventEnrollment accepts a message.

    """

    def run_filter(self, user, course_key, mode):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            user (User): is a Django User object.
            course_key (CourseKey): course key associated with the enrollment.
            mode (str): is a string specifying what kind of enrollment.

        """
        event = "CourseEnrollmentStarted"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event. User: {user}, course: {course_key}, mode: {mode}.")

            data = {
                'user': user,
                'profile': user.profile,
                'course_key': course_key,
                'mode': mode,
            }
            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CourseEnrollmentStarted.PreventEnrollment)

            update_model(user, content.get('user'))
            update_model(user.profile, content.get('profile'))

            if 'course_key' in content:
                course_key = CourseKey.from_string(content.get('course_key'))

            if 'mode' in content:
                mode = content.get('mode')

            _check_for_exception(exceptions, CourseEnrollmentStarted.PreventEnrollment)

        return {
            "user": user,
            "course_key": course_key,
            "mode": mode,
        }


class CourseUnenrollmentStartedWebFilter(PipelineStep):
    """
    Process CourseUnenrollmentStarted filter.

    This filter is triggered when a user is unenrolled from a course.

    It will POST a json to the webhook url with the enrollment object.

    EXAMPLE::

        {
          "user": {
            "id": 4,
            "password": "pbkdf2_sha256$260000$W2SQQzln5u3i20SYeShEWx$4Y/Th225xS25wvWG1GyHpRAj2f3Ick4/a4jbAFvsudY=",
            "last_login": "2023-06-13 15:04:10.629206+00:00",
            "is_superuser": true,
            "username": "andres",
            "first_name": "hola",
            "last_name": "",
            "email": "andres@aulasneo.com",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2023-01-26 16:22:57.939766+00:00"
          },
          "profile": {
            "id": 2,
            "user_id": 4,
            "name": "Andrés González",
            "meta": "",
            "courseware": "course.xml",
            "language": "",
            "location": "",
            "year_of_birth": null,
            "gender": null,
            "level_of_education": null,
            "mailing_address": null,
            "city": null,
            "country": null,
            "state": null,
            "goals": null,
            "bio": null,
            "profile_image_uploaded_at": null,
            "phone_number": null
          },
          "course_key": "course-v1:test+test+test",
          "mode": "honor",
          "event_metadata": {
            "event_type": "CourseEnrollmentStarted",
            "time": "2023-06-13 21:02:50.375064"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "user": {
                    <key>:<value>,...
                },
                "profile": {
                    <key>:<value>,...
                },
            },
            "exception": {
                "PreventUnenrollment": <message>
                }
            }
        }

    "user" and "profile" keys are optionals, as well as the keys inside each.

    """

    def run_filter(self, enrollment):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            enrollment (User): is an enrollment object.

        """
        event = "CourseUnenrollmentStarted"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event. Enrollment: {enrollment}")

            user = enrollment.user

            data = {
                'user': user,
                'profile': user.profile,
                'enrollment': enrollment,
            }
            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CourseUnenrollmentStarted.PreventUnenrollment)

            update_model(user, content.get('user'))
            update_model(user.profile, content.get('profile'))

            _check_for_exception(exceptions, CourseUnenrollmentStarted.PreventUnenrollment)

        return {
            "enrollment": enrollment,
        }


class CertificateCreationRequestedWebFilter(PipelineStep):
    """
    Process CertificateCreationRequested filter.

    This filter is triggered when a certificate creation is requested.

    It will POST a json to the webhook url with the enrollment object.

    EXAMPLE::

        {
          "user": {
            "id": 17,
            "password": "pbkdf2_sha256***=",
            "last_login": "2023-06-14 16:11:08.341205+00:00",
            "is_superuser": false,
            "username": "test1",
            "first_name": "",
            "last_name": "",
            "email": "test1@aulasneo.com",
            "is_staff": false,
            "is_active": true,
            "date_joined": "2023-06-12 20:29:37.756206+00:00"
          },
          "profile": {
            "id": 13,
            "user_id": 17,
            "name": "test1",
            "meta": "",
            "courseware": "course.xml",
            "language": "",
            "location": "",
            "year_of_birth": null,
            "gender": "",
            "level_of_education": "",
            "mailing_address": "",
            "city": "",
            "country": "",
            "state": null,
            "goals": "",
            "bio": null,
            "profile_image_uploaded_at": null,
            "phone_number": null
          },
          "course_key": "course-v1:test+test+test",
          "mode": "honor",
          "status": null,
          "grade": {
            "user": "test1",
            "course_data": "Course: course_key: course-v1:test+test+test",
            "percent": 1,
            "passed": true,
            "letter_grade": "Pass",
            "force_update_subsections": false,
            "_subsection_grade_factory": "<lms.djangoapps.grades.subsection_grade_factory.SubsectionGradeFactory >"
          },
          "generation_mode": "self",
          "event_metadata": {
            "event_type": "CertificateCreationRequested",
            "time": "2023-06-14 16:28:23.266529"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "user": {
                    <key>:<value>,...
                },
                "profile": {
                    <key>:<value>,...
                },
                "course_key": <course key>,
                "mode": <mode>,
                "status": <status>,
                "grade": {
                    "percent": <0..1>,
                    "passed": <true|false>,
                    "letter_grade": <letter grade>,
                    "force_update_subsections": <true|false>
            },
            "exception": {
                "PreventCertificateCreation": <message>
                }
            }
        }

    All data keys are optionals, as well as the keys inside each.

    Note: Changes in the grade values do not take effect in the certificate and do not modify the user's grade.
    """

    def run_filter(self, user, course_key, mode, status, grade, generation_mode):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            user (User): is a Django User object.
            course_key (CourseKey): course key associated with the certificate.
            mode (str): mode of the certificate.
            status (str): status of the certificate.
            grade (CourseGrade): user's grade in this course run.
            generation_mode (str): Options are "self" (implying the user generated the cert themself) and "batch" for
                everything else.

        """
        event = "CertificateCreationRequested"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event. User: {user}, course: {course_key}, status: {status}")

            data = {
                "user": user,
                "profile": user.profile,
                "course_key": course_key,
                "mode": mode,
                "status": status,
                "grade": grade.__dict__,
                "generation_mode": generation_mode,
                "completion_summary": get_course_blocks_completion_summary(course_key, user)
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CertificateCreationRequested.PreventCertificateCreation)

            update_model(user, content.get('user'))
            update_model(user.profile, content.get('profile'))

            if 'course_key' in content:
                course_key = CourseKey.from_string(content.get('course_key'))

            if 'mode' in content:
                mode = content.get('mode')

            if 'status' in content:
                status = content.get('status')

            if 'generation_mode' in content:
                generation_mode = content.get('generation_mode')

            update_object(grade, content.get('grade'))

            _check_for_exception(exceptions, CertificateCreationRequested.PreventCertificateCreation)

        return {
            "user": user,
            "course_key": course_key,
            "mode": mode,
            "status": status,
            "grade": grade,
            "generation_mode": generation_mode,
        }


class CertificateRenderStartedWebFilter(PipelineStep):
    """
    Process CertificateRenderStarted filter.

    This filter is triggered when a certificate is about to be rendered.

    It will POST a json to the webhook url with the enrollment object.

    EXAMPLE::

        {
          "context": {
            "user_language": "en",
            "platform_name": "Your Platform Name Here",
            "course_id": "course-v1:test+test+test",
            "accomplishment_class_append": "accomplishment-certificate",
            "company_about_url": "/about",
            "company_privacy_url": "/privacy",
            "company_tos_url": "/tos_and_honor",
            "company_verified_certificate_url": "http://www.example.com/verified-certificate",
            "logo_src": "/media/certificate_template_assets/2/logo.png",
            "logo_url": "http://local.overhang.io:8000",
            "copyright_text": "&copy; 2023 Aulasneo DEV. All rights reserved.",
            "document_title": "test test Certificate | Aulasneo DEV",
            "company_tos_urltext": "Terms of Service & Honor Code",
            "company_privacy_urltext": "Privacy Policy",
            "logo_subtitle": "Certificate Validation",
            "accomplishment_copy_about": "About Aulasneo DEV Accomplishments",
            "certificate_date_issued_title": "Issued On:",
            "certificate_id_number_title": "Certificate ID Number",
            "certificate_info_title": "About Aulasneo DEV Certificates",
            "certificate_verify_title": "How Aulasneo DEV Validates Student Certificates",
            "certificate_verify_description": "Certificates issued by Aulasneo DEV ",
            "certificate_verify_urltext": "Validate this certificate for yourself",
            "company_about_description": "Aulasneo DEV offers interactive online classes and MOOCs.",
            "company_about_title": "About Aulasneo DEV",
            "company_about_urltext": "Learn more about Aulasneo DEV",
            "company_courselist_urltext": "Learn with Aulasneo DEV",
            "company_careers_urltext": "Work at Aulasneo DEV",
            "company_contact_urltext": "Contact Aulasneo DEV",
            "document_banner": "Aulasneo DEV acknowledges the following student accomplishment",
            "certificate_data": {
              "id": 12345678,
              "name": "Name of the certificate",
              "description": "Description of the certificate",
              "is_active": true,
              "version": 1,
              "signatories": [
                {
                  "name": "",
                  "title": "President of the board",
                  "organization": "Aulasneo",
                  "signature_image_path": "/asset-v1:test+test+test+type@asset+block@Signature_President.png",
                  "certificate": 12345678,
                  "id": 12345678
                },
                {
                  "name": "",
                  "title": "CEO",
                  "organization": "Aulasneo",
                  "signature_image_path": "/asset-v1:test+test+test+type@asset+block@Signature_CEO.png",
                  "certificate": 12345678,
                  "id": 12345678
                }
              ]
            },
            "certificate_type": "Honor Code",
            "certificate_title": "Certificate of Achievement",
            "organization_long_name": "test",
            "organization_short_name": "test",
            "accomplishment_copy_course_org": "test",
            "organization_logo": "",
            "full_course_image_url": "http://example.com/asset-v1:t+t+test+type@asset+block@images_course_image.jpg",
            "accomplishment_copy_course_name": "Test",
            "course_number": "test",
            "is_integrity_signature_enabled_for_course": false,
            "accomplishment_copy_course_description": "a course of study offered by test.",
            "username": "test1",
            "course_mode": "honor",
            "accomplishment_user_id": 17,
            "accomplishment_copy_name": "test1",
            "accomplishment_copy_username": "test1",
            "accomplishment_more_title": "More Information About test1's Certificate:",
            "accomplishment_banner_opening": "test1, you earned a certificate!",
            "accomplishment_banner_congrats": "Congratulations! This page summarizes what you accomplished.",
            "accomplishment_copy_more_about": "More about test1's accomplishment",
            "facebook_share_enabled": false,
            "facebook_app_id": null,
            "facebook_share_text": null,
            "twitter_share_enabled": false,
            "twitter_share_text": null,
            "share_url": "http://local.overhang.io:8000/certificates/b721009ebdff49cea9a443e05a6959fc",
            "twitter_url": "",
            "linked_in_url": null,
            "certificate_id_number": "b721009ebdff49cea9a443e05a6959fc",
            "certificate_verify_url": "Noneb721009ebdff49cea9a443e05a6959fcNone",
            "certificate_date_issued": "June 14, 2023",
            "document_meta_description": "This is a valid Aulasneo DEV certificate for test1",
            "accomplishment_copy_description_full": "successfully completed, received a passing grade",
            "certificate_type_description": "An Honor Code certificate signifies that a learner has ...",
            "certificate_info_description": "Aulasneo DEV acknowledges achievements through certificates, ...",
            "badge": null
          },
          "custom_template": {
            "id": 1,
            "created": "2023-06-14 18:39:56.824500+00:00",
            "modified": "2023-06-14 18:46:46.156615+00:00",
            "name": "cert_template",
            "description": "Test template",
            "template": "<html><body>${accomplishment_banner_congrats}</body></html>",
            "organization_id": 1,
            "course_key": "course-v1:test+test+test",
            "mode": "honor",
            "is_active": true,
            "language": ""
          },
          "event_metadata": {
            "event_type": "CertificateRenderStarted",
            "time": "2023-06-14 18:05:54.815086"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLS::

        {
            "data": {
                "context": {
                    "additional_variable": "test test",
                    "accomplishment_copy_name": "Name"
                },
                "custom_template": {
                    "template":"<html><body>${additional_variable}</body></html>"
                }
            }
        }

    All data keys are optionals, as well as the keys inside each.

    If you override any of the template fields, the change will not modify the existing template, but will
    be used for this certificate rendering only.

    Exceptions::

        "exceptions": {
            "RedirectToPage": {
                "redirect_to": <URL to redirect>
            }
            "RenderCustomResponse": {
                "content": <html content>,
                "content_type": <MIME type. By default "text/html; charset=utf-8",
                "status": <HTTP status code. By default=200>,
                "reason": <HTTP response phrase. If not provided, a default phrase will be used.>,
                "charset": <If not given it will be extracted from content_type, and if that is unsuccessful,
                    the DEFAULT_CHARSET setting will be used.>,
                "headers": <dict of HTTP headers>
            }
            "RenderAlternativeInvalidCertificate": {
                "template_name": <template name or leave empty to render the standard invalid certificate>
            }
        }

    Note: Changes in the grade values do not take effect in the certificate and do not modify the user's grade.
    To be able to update the certificate template, it must exist, be active and be associated to the course
    and organization.
    """

    def run_filter(self, context, custom_template):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            context (dict): context dictionary for certificate template.
            custom_template (CertificateTemplate): edxapp object representing custom web certificate template.
        """
        event = "CertificateRenderStarted"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            user = get_user_model().objects.get(id=context.get('accomplishment_user_id'))
            course_key = CourseKey.from_string(context.get('course_id'))

            data = {
                "context": context,
                "custom_template": custom_template,
                "completion_summary": get_course_blocks_completion_summary(course_key, user)
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CertificateRenderStarted.RedirectToPage)

            update_object(custom_template, content.get('custom_template'))

            if 'context' in content:
                context.update(content.get('context'))

            _check_for_exception(exceptions, CertificateRenderStarted.RedirectToPage)
            _check_for_exception(exceptions, CertificateRenderStarted.RenderAlternativeInvalidCertificate)
            _check_for_exception(exceptions, CertificateRenderStarted.RenderCustomResponse)

        return {
            "context": context,
            "custom_template": custom_template,
        }


class CohortChangeRequestedWebFilter(PipelineStep):
    """
    Process CohortChangeRequested filter.

    This filter is triggered when a user is about to be changed to another cohort.

    It will POST a json to the webhook url with the cohort object.

    EXAMPLE::

        {
          "current_membership": {
            "id": 1,
            "course_user_group_id": 2,
            "user_id": 4,
            "course_id": "course-v1:edX+DemoX+Demo_Course"
          },
          "target_cohort": {
            "id": 1,
            "name": "Cohort test",
            "course_id": "course-v1:edX+DemoX+Demo_Course",
            "group_type": "cohort"
          },
          "user": {
            "id": 4,
            "password": "pbkdf2_sha256$****=",
            "last_login": "2023-06-21 16:43:46.264292+00:00",
            "is_superuser": true,
            "username": "andres",
            "first_name": "",
            "last_name": "",
            "email": "andres@aulasneo.com",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2023-01-26 16:22:57.939766+00:00"
          },
          "user_profile": {
            "id": 2,
            "user_id": 4,
            "name": "John Doe",
            "meta": "",
            "courseware": "course.xml",
            "language": "",
            "location": "",
            "year_of_birth": null,
            "gender": null,
            "level_of_education": null,
            "mailing_address": null,
            "city": null,
            "country": null,
            "state": null,
            "goals": null,
            "bio": null,
            "profile_image_uploaded_at": null,
            "phone_number": null
          },
          "course_key": "course-v1:edX+DemoX+Demo_Course",
          "event_metadata": {
            "event_type": "CohortChangeRequested",
            "time": "2023-06-30 17:52:03.671230"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
            ...
            }
        }

    All data keys are optionals, as well as the keys inside each.

    Exceptions::

        "exceptions": {
            "PreventCohortChange": <message>
        }
    """

    def run_filter(self, current_membership, target_cohort):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            current_membership (CohortMembership): edxapp object representing the user's cohort current membership
                object.
            target_cohort (CourseUserGroup): edxapp object representing the new user's cohort.

        """
        event = "CohortChangeRequested"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            user = get_user_model().objects.get(id=current_membership.user_id)
            user_profile = user.profile
            course_key = current_membership.course_id

            data = {
                "current_membership": current_membership,
                "target_cohort": target_cohort,
                "user": user,
                "user_profile": user_profile,
                "course_key": course_key
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CohortChangeRequested.PreventCohortChange)

            update_object(current_membership, content.get('current_membership'))
            update_object(target_cohort, content.get('target_cohort'))

            _check_for_exception(exceptions, CohortChangeRequested.PreventCohortChange)

        return {
            "current_membership": current_membership,
            "target_cohort": target_cohort,
        }


class CohortAssignmentRequestedWebFilter(PipelineStep):
    """
    Process CohortAssignmentRequested filter.

    This filter is triggered when a user is about to be assigned to a cohort.

    It will POST a json to the webhook url with the cohort object.

    EXAMPLE::

        {
          "target_cohort": {
            "id": 1,
            "name": "Cohort test",
            "course_id": "course-v1:edX+DemoX+Demo_Course",
            "group_type": "cohort"
          },
          "user": {
            "id": 4,
            "password": "pbkdf2_sha256$****=",
            "last_login": "2023-06-21 16:43:46.264292+00:00",
            "is_superuser": true,
            "username": "andres",
            "first_name": "",
            "last_name": "",
            "email": "andres@aulasneo.com",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2023-01-26 16:22:57.939766+00:00"
          },
          "user_profile": {
            "id": 2,
            "user_id": 4,
            "name": "John Doe",
            "meta": "",
            "courseware": "course.xml",
            "language": "",
            "location": "",
            "year_of_birth": null,
            "gender": null,
            "level_of_education": null,
            "mailing_address": null,
            "city": null,
            "country": null,
            "state": null,
            "goals": null,
            "bio": null,
            "profile_image_uploaded_at": null,
            "phone_number": null
          },
          "course_key": "course-v1:edX+DemoX+Demo_Course",
          "event_metadata": {
            "event_type": "CohortChangeRequested",
            "time": "2023-06-30 17:52:03.671230"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
            ...
            }
        }

    All data keys are optionals, as well as the keys inside each.

    Exceptions::

        "exceptions": {
            "PreventCohortAssignment": <message>
        }

    Note: Currently the exception message is logged in the console but not shown to the user.

    """

    def run_filter(self, user, target_cohort):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            user (User): is a Django User object to be added in the cohort.
            target_cohort (CourseUserGroup): edxapp object representing the new user's cohort.
        """
        event = "CohortAssignmentRequested"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            user_profile = user.profile
            course_key = target_cohort.course_id

            data = {
                "target_cohort": target_cohort,
                "user": user,
                "user_profile": user_profile,
                "course_key": course_key
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CohortAssignmentRequested.PreventCohortAssignment)

            update_object(user, content.get('user'))
            update_object(user.profile, content.get('user_profile'))
            update_object(target_cohort, content.get('target_cohort'))

            _check_for_exception(exceptions, CohortAssignmentRequested.PreventCohortAssignment)

        return {
            "user": user,
            "target_cohort": target_cohort,
        }


class CourseAboutRenderStartedWebFilter(PipelineStep):
    r"""
    Process CourseAboutRenderStarted filter.

    This filter is triggered when the course about page is about to be rendered.

    It will POST a json to the webhook url with the cohort object.

    EXAMPLE::

        {
          "context": {
            "course": {
              "xmodule_runtime": null,
              "_asides": [],
              "_parent_block": null,
              "_parent_block_id": null,
              "_child_cache": {},
              "_deprecated_per_instance_field_data": "",
              "_field_data_cache": {
                "wiki_slug": "edX.DemoX.Demo_Course",
                "due_date_display_format": null,
                "show_timezone": true,
                "grading_policy": {
                  "GRADER": [
                    {
                      "type": "Homework",
                      "min_count": 3,
                      "drop_count": 1,
                      "short_label": "Ex",
                      "weight": 0
                    },
                    {
                      "type": "Exam",
                      "min_count": 1,
                      "drop_count": 0,
                      "short_label": "",
                      "weight": 0
                    },
                    {
                      "type": "test",
                      "min_count": 1,
                      "drop_count": 0,
                      "short_label": "",
                      "weight": 1
                    }
                  ],
                  "GRADE_CUTOFFS": {
                    "Pass": 0.6
                  }
                },
                "discussion_topics": {
                  "General": {
                    "id": "i4x-edx-eiorguegnru-course-foobarbaz"
                  }
                },
                "tabs": [
                  "<lms.djangoapps.courseware.tabs.CourseInfoTab object at 0x7f05c1f39100>",
                  "<lms.djangoapps.courseware.tabs.CoursewareTab object at 0x7f05c1f390a0>",
                  "<lms.djangoapps.discussion.plugins.DiscussionTab object at 0x7f05c1ec1400>",
                  "<lms.djangoapps.course_wiki.tab.WikiTab object at 0x7f05c1ec1430>",
                  "<lms.djangoapps.courseware.tabs.TextbookTabs object at 0x7f05c1ec1880>",
                  "<lms.djangoapps.courseware.tabs.ProgressTab object at 0x7f05c1ec1940>",
                  "<lms.djangoapps.courseware.tabs.DatesTab object at 0x7f05c1ec19a0>",
                  "<lms.djangoapps.edxnotes.plugins.EdxNotesTab object at 0x7f05c1ec1ac0>"
                ],
                "enable_ccx": false,
                "self_paced": true,
                "parent": null,
                "start": "2013-02-05 05:00:00+00:00",
                "catalog_visibility": "both",
                "end": "2023-02-01 00:00:00+00:00",
                "certificate_available_date": null,
                "certificates_display_behavior": "end",
                "enrollment_start": null,
                "enrollment_end": null,
                "pre_requisite_courses": [],
                "course_image": "images_course_image.jpg",
                "static_asset_path": "",
                "banner_image": "images_course_image.jpg",
                "video_thumbnail_image": "images_course_image.jpg",
                "language": null,
                "learning_info": [],
                "instructor_info": {
                  "instructors": []
                },
                "license": null,
                "course_edit_method": "Studio",
                "cosmetic_display_price": 0,
                "invitation_only": false,
                "max_student_enrollments_allowed": null,
                "enrollment_domain": null,
                "course_visibility": "private"
              },
              "_dirty_fields": {
                "<Dict grading_policy>": {
                  "GRADER": [
                    {
                      "type": "Homework",
                      "min_count": 3,
                      "drop_count": 1,
                      "short_label": "Ex",
                      "weight": 0
                    },
                    {
                      "type": "Exam",
                      "min_count": 1,
                      "drop_count": 0,
                      "short_label": "",
                      "weight": 0
                    },
                    {
                      "type": "test",
                      "min_count": 1,
                      "drop_count": 0,
                      "short_label": "",
                      "weight": 1
                    }
                  ],
                  "GRADE_CUTOFFS": {
                    "Pass": 0.6
                  }
                },
                "<Dict discussion_topics>": {
                  "General": {
                    "id": "i4x-edx-eiorguegnru-course-foobarbaz"
                  }
                },
                "<CourseTabList tabs>": [
                  "<lms.djangoapps.courseware.tabs.CourseInfoTab object at 0x7f05c1ec1dc0>",
                  "<lms.djangoapps.courseware.tabs.CoursewareTab object at 0x7f05c1ec17c0>",
                  "<lms.djangoapps.discussion.plugins.DiscussionTab object at 0x7f05c1ec1790>",
                  "<lms.djangoapps.course_wiki.tab.WikiTab object at 0x7f05c1ec17f0>",
                  "<lms.djangoapps.courseware.tabs.TextbookTabs object at 0x7f05c1ea8af0>",
                  "<lms.djangoapps.courseware.tabs.ProgressTab object at 0x7f05c1ea8b80>",
                  "<lms.djangoapps.courseware.tabs.DatesTab object at 0x7f05c1ea8c70>",
                  "<lms.djangoapps.edxnotes.plugins.EdxNotesTab object at 0x7f05c1ea8ca0>"
                ],
                "<Reference parent>": null,
                "<List pre_requisite_courses>": [],
                "<List learning_info>": [],
                "<Dict instructor_info>": {
                  "instructors": []
                }
              },
              "scope_ids": [
                null,
                "course",
                "block-v1:edX+DemoX+Demo_Course+type@course+block@course",
                "block-v1:edX+DemoX+Demo_Course+type@course+block@course"
              ],
              "_runtime": "",
              "gated_sequence_paywall": null,
              "_gating_prerequisites": null,
              "syllabus_present": false,
              "_grading_policy": {
                "RAW_GRADER": [
                  {
                    "type": "Homework",
                    "min_count": 3,
                    "drop_count": 1,
                    "short_label": "Ex",
                    "weight": 0
                  },
                  {
                    "type": "Exam",
                    "min_count": 1,
                    "drop_count": 0,
                    "short_label": "",
                    "weight": 0
                  },
                  {
                    "type": "test",
                    "min_count": 1,
                    "drop_count": 0,
                    "short_label": "",
                    "weight": 1
                  }
                ],
                "GRADE_CUTOFFS": {
                  "Pass": 0.6
                }
              },
              "_edited_by": 4,
              "_edited_on": "2023-06-28 14:09:01.134000+00:00",
              "previous_version": "648d078bcf0b4732adabe560",
              "update_version": "649c3efdfdd296af28980306",
              "source_version": "649c3efdfdd296af28980305",
              "definition_locator": "def-v1:63d984b5f465aece32500e3a+type@course",
              "course_version": "64b1a37eb74deb15b841b65e"
            },
            "course_details": {
              "org": "edX",
              "course_id": "DemoX",
              "run": "Demo_Course",
              "language": null,
              "start_date": "2013-02-05 05:00:00+00:00",
              "end_date": "2023-02-01 00:00:00+00:00",
              "enrollment_start": null,
              "enrollment_end": null,
              "certificate_available_date": null,
              "certificates_display_behavior": "end",
              "syllabus": null,
              "title": "",
              "subtitle": "",
              "duration": "",
              "description": "",
              "short_description": "",
              "overview": "<section class=\"about\">\n   <h2>About This Course</h2>\n   ....",
              "about_sidebar_html": "",
              "intro_video": null,
              "effort": null,
              "license": null,
              "course_image_name": "images_course_image.jpg",
              "course_image_asset_path": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg",
              "banner_image_name": "images_course_image.jpg",
              "banner_image_asset_path": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg",
              "video_thumbnail_image_name": "images_course_image.jpg",
              "video_thumbnail_image_asset_path": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@image.jpg",
              "pre_requisite_courses": [],
              "entrance_exam_enabled": "",
              "entrance_exam_id": "",
              "entrance_exam_minimum_score_pct": "50",
              "self_paced": true,
              "learning_info": [],
              "instructor_info": {
                "instructors": []
              }
            },
            "staff_access": true,
            "studio_url": "//studio.local.overhang.io:8001/settings/details/course-v1:edX+DemoX+Demo_Course",
            "registered": true,
            "course_target": "http://apps.local.overhang.io:2000/learning/course/course-v1:edX+DemoX+Demo_Course/home",
            "is_cosmetic_price_enabled": true,
            "course_price": "Free",
            "ecommerce_checkout": false,
            "ecommerce_checkout_link": "",
            "ecommerce_bulk_checkout_link": "",
            "single_paid_mode": null,
            "show_courseware_link": true,
            "is_course_full": false,
            "can_enroll": true,
            "invitation_only": false,
            "active_reg_button": false,
            "is_shib_course": null,
            "disable_courseware_header": true,
            "pre_requisite_courses": [],
            "course_image_urls": {
              "raw": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg",
              "small": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg",
              "large": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg"
            },
            "sidebar_html_enabled": false,
            "allow_anonymous": "AccessResponse(False, None, None, None, None, None)"
          },
          "template_name": "courseware/course_about.html",
          "event_metadata": {
            "event_type": "CourseAboutRenderStarted",
            "time": "2023-08-09 20:53:15.420093"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "context": {
                    "can_enroll": false
                }
            }
        }

    All data keys are optionals, as well as the keys inside each.
    Note: course and course_details are for information only, they cannot be modified by the webfilter.

    Exceptions::
        {
            "exception": {
                "RedirectToPage": {
                    "redirect_to": <URL to redirect>
                }
                "RenderCustomResponse": {
                    "content": <html content>,
                    "content_type": <MIME type. By default "text/html; charset=utf-8",
                    "status": <HTTP status code. By default=200>,
                    "reason": <HTTP response phrase. If not provided, a default phrase will be used.>,
                    "charset": <If not given it will be extracted from content_type, and if that is unsuccessful,
                        the DEFAULT_CHARSET setting will be used.>,
                    "headers": <dict of HTTP headers>
                }
                "RenderInvalidCourseAbout": {
                    "course_about_template": <template to render the standard invalid course about page>,
                    "template_context": <context for rendering the template>
                }
            }
        }

    Note: Currently the exception message is logged in the console but not shown to the user.

    """

    def run_filter(self, context, template_name):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            context (dict): context dictionary for course about template.
            template_name (str): template name to be rendered by the course about.
        """
        event = "CourseAboutRenderStarted"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            course = context.get('course')
            course_details = context.get('course_details')

            # Convert the course and course_details objects to dicts
            context_to_send = context.copy()
            context_to_send['course'] = vars(course)
            context_to_send['course_details'] = vars(course_details)

            data = {
                "context": context_to_send,
                "template_name": template_name,
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=CourseAboutRenderStarted.RedirectToPage)

            # The response data will have a course and a course_details objects that are immutable
            if 'context' in content:
                content['context'].update({'course': course})
                content['context'].update({'course_details': course_details})

            _check_for_exception(exceptions, CourseAboutRenderStarted.RedirectToPage)
            _check_for_exception(exceptions, CourseAboutRenderStarted.RenderCustomResponse)
            _check_for_exception(exceptions, CourseAboutRenderStarted.RenderInvalidCourseAbout)

            return {
                "context": content.get('context') or context,
                "template_name": content.get('template_name') or template_name,
            }

        return {
            "context": context,
            "template_name": template_name,
        }


class DashboardRenderStartedWebFilter(PipelineStep):
    """
    Process DashboardRenderStarted filter.

    This filter is triggered when the dashboard page is about to be rendered.

    It will POST a json to the webhook url with the cohort object.

    EXAMPLE::

        {
          "context": {
            "urls": {},
            "programs_data": {},
            "enterprise_message": "",
            "consent_required_courses": "set()",
            "enrollment_message": null,
            "redirect_message": "",
            "account_activation_messages": [],
            "activate_account_message": "",
            "course_enrollments": [
              "[CourseEnrollment] andres: course-v1:test+test+test (2023-02-14 14:49:26.692594+00:00); active: (True)",
            ],
            "course_entitlements": [],
            "course_entitlement_available_sessions": {},
            "unfulfilled_entitlement_pseudo_sessions": {},
            "course_optouts": "<QuerySet []>",
            "staff_access": true,
            "errored_courses": {},
            "show_courseware_links_for": {
              "course-v1:test+test+test": "AccessResponse(True, None, None, None, None, None)",
              "course-v1:edX+DemoX+Demo_Course": "AccessResponse(True, None, None, None, None, None)"
            },
            "all_course_modes": {
              "course-v1:test+test+test": {
                "show_upsell": false,
                "days_for_upsell": null
              },
              "course-v1:edX+DemoX+Demo_Course": {
                "show_upsell": false,
                "days_for_upsell": null
              }
            },
            "cert_statuses": {
              "course-v1:test+test+test": {
                "status": "downloadable",
                "mode": "honor",
                "linked_in_url": null,
                "can_unenroll": false,
                "show_survey_button": false,
                "show_cert_web_view": true,
                "cert_web_view_url": "/certificates/dea5907d215a4c15948059011c339e21",
                "grade": "1.0"
              },
              "course-v1:edX+DemoX+Demo_Course": {
                "status": "downloadable",
                "mode": "honor",
                "linked_in_url": null,
                "can_unenroll": false,
                "show_survey_button": false,
                "show_cert_web_view": true,
                "cert_web_view_url": "/certificates/cb0e2d268a894709889e0f9e2fe3bd4a",
                "grade": "0.0"
              }
            },
            "credit_statuses": {},
            "show_email_settings_for": "frozenset({CourseLocator('edX', 'DemoX', 'Demo_Course', None, None)})",
            "reverifications": {
              "approved": [],
              "denied": [],
              "pending": [],
              "must_reverify": []
            },
            "verification_display": true,
            "verification_status": "none",
            "verification_expiry": "",
            "verification_status_by_course": {},
            "verification_errors": [],
            "denied_banner": false,
            "billing_email": "info@aulasneo.com",
            "show_account_activation_popup": null,
            "user": "andres",
            "logout_url": "/logout",
            "platform_name": "Aulasneo DEV",
            "enrolled_courses_either_paid": "frozenset()",
            "enrolled_courses_voucher_refundable": "frozenset()",
            "provider_states": [],
            "courses_requirements_not_met": {},
            "nav_hidden": true,
            "inverted_programs": {},
            "show_program_listing": false,
            "show_dashboard_tabs": true,
            "disable_courseware_js": true,
            "display_course_modes_on_dashboard": false,
            "display_sidebar_account_activation_message": false,
            "display_dashboard_courses": true,
            "empty_dashboard_message": null,
            "recovery_email_message": null,
            "recovery_email_activation_message": null,
            "show_load_all_courses_link": false,
            "course_info": null,
            "plugins": {},
            "user_metadata": {
              "username": "andres",
              "user_id": 4,
              "course_id": null,
              "course_display_name": null,
              "enrollment_mode": null,
              "upgrade_link": null,
              "upgrade_price": null,
              "audit_access_deadline": null,
              "course_duration": null,
              "pacing_type": null,
              "has_staff_access": null,
              "forum_roles": null,
              "partition_groups": null,
              "has_non_audit_enrollments": null,
              "program_key_fields": null,
              "email": "andres@aulasneo.com",
              "schedule_start": null,
              "enrollment_time": null,
              "course_start": null,
              "course_end": null,
              "dynamic_upgrade_deadline": null,
              "course_upgrade_deadline": null
            },
            "resume_button_urls": [
              "/courses/course-v1:test+test+test/jump_to/block-v1:test+test+test+type@problem+block@e82xx",
              "/courses/course-v1:edX+DemoX+Demo_Course/jump_to/block-v1:edX+DemoX+Demo_Course+type@html+block@829xxx"
            ]
          },
          "template_name": "dashboard.html",
          "event_metadata": {
            "event_type": "DashboardRenderStarted",
            "time": "2023-08-14 22:30:32.013894"
          }
        }

    The webhook processor can return a json with two objects: data and exception.

    EXAMPLE::

        {
            "data": {
                "context": {
                    "can_enroll": false
                }
            }
        }

    All data keys are optionals, as well as the keys inside each.
    Note: course and course_details are for information only, they cannot be modified by the webfilter.

    Exceptions::
        {
            "exception": {
                "RedirectToPage": {
                    "redirect_to": <URL to redirect>
                }
                "RenderCustomResponse": {
                    "content": <html content>,
                    "content_type": <MIME type. By default "text/html; charset=utf-8",
                    "status": <HTTP status code. By default=200>,
                    "reason": <HTTP response phrase. If not provided, a default phrase will be used.>,
                    "charset": <If not given it will be extracted from content_type, and if that is unsuccessful,
                        the DEFAULT_CHARSET setting will be used.>,
                    "headers": <dict of HTTP headers>
                }
                "RenderInvalidCourseAbout": {
                    "course_about_template": <template to render the standard invalid course about page>,
                    "template_context": <context for rendering the template>
                }
            }
        }

    Note: Currently the exception message is logged in the console but not shown to the user.

    """

    def run_filter(self, context, template_name):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Arguments:
            context (dict): context dictionary for course about template.
            template_name (str): template name to be rendered by the course about.
        """
        event = "DashboardRenderStarted"

        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            data = {
                "context": context,
                "template_name": template_name,
            }

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=DashboardRenderStarted.RedirectToPage)

            context.update(content.get('context'))

            _check_for_exception(exceptions, DashboardRenderStarted.RedirectToPage)
            _check_for_exception(exceptions, DashboardRenderStarted.RenderCustomResponse)
            _check_for_exception(exceptions, DashboardRenderStarted.RenderInvalidDashboard)

            return {
                "context": context,
                "template_name": content.get('template_name') or template_name,
            }

        return {"context": context, "template_name": template_name}


class VerticalBlockChildRenderStartedWebFilter(PipelineStep):
    """
    Filter used to modify the rendering of a child block within a vertical block.

    Purpose:
        This filter is triggered when a child block is about to be rendered within a vertical block, allowing the filter
        to act on the block and the context used to render the child block.

    Filter Type:
        org.openedx.learning.vertical_block_child.render.started.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: xmodule/vertical_block.py
        - Function or Method: VerticalBlock._student_or_public_view
    """
    def run_filter(self, **data):
        """
        data = block: Any, context: dict[str, Any]
        """
        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=VerticalBlockChildRenderStarted.PreventChildBlockRender)

            return_data['context'].update(content.get('context', {}))

            _check_for_exception(exceptions, VerticalBlockChildRenderStarted.PreventChildBlockRender)

            return return_data

        return data


class CourseEnrollmentQuerysetRequestedWebFilter(PipelineStep):
    """
    Filter used to modify the QuerySet of course enrollments.

    Purpose:
        This filter is triggered when a QuerySet of course enrollments is requested, allowing the filter to act on the
        enrollments data.

    Filter Type:
        org.openedx.learning.course_enrollment_queryset.requested.v1

    Trigger: NA

    Additional Information:
        This filter is not currently triggered by any specific function or method in any codebase. It should be
        marked to be removed if it's not used. See openedx-filters#245 for more information.
    """


def run_filter(self, **data):
    """
    data = enrollments: QuerySet
    """
    # The event is the class name, except the last "WebFilter"
    event = type(self).__name__[:-9]

    return_data = data.copy()
    webfilters = Webfilter.objects.filter(enabled=True, event=event)

    if webfilters:
        logger.info(f"Webfilter for {event} event.")

        return_data['enrollments'] = list(data['enrollments'].values())

        content, exceptions = _process_filter(webfilters=webfilters,
                                              data=data,
                                              exception=CourseEnrollmentQuerysetRequested.PreventEnrollmentQuerysetRequest)

        return_data['enrollments'] = data['enrollments'].filter(content.get('filter', {}))

        _check_for_exception(exceptions, CourseEnrollmentQuerysetRequested.PreventEnrollmentQuerysetRequest)

    return data


class RenderXBlockStartedWebFilter(PipelineStep):
    """
    Filter in between context generation and rendering of XBlock scope.

    Purpose:
        This filter is triggered when an XBlock is about to be rendered, just before the rendering process is completed
        allowing the filter to act on the context and student_view_context used to render the XBlock.

    Filter Type:
        org.openedx.learning.xblock.render.started.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: lms/djangoapps/courseware/views/views.py
        - Function or Method: render_xblock
    """

    def run_filter(self, **data):
        """
        data = context: dict[str, Any], student_view_context: dict
        """
        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=RenderXBlockStarted.PreventXBlockBlockRender)

            return_data.update(content)

            _check_for_exception(exceptions, RenderXBlockStarted.PreventXBlockBlockRender)
            _check_for_exception(exceptions, RenderXBlockStarted.RenderCustomResponse)

            return return_data

        return data


class VerticalBlockRenderCompletedWebFilter(PipelineStep):
    """
    Filter used to act on vertical block rendering completed.

    Purpose:
        This filter is triggered when a vertical block is rendered, just after the rendering process is completed
        allowing the filter to act on the block, fragment, context, and view used to render the vertical block.

    Filter Type:
        org.openedx.learning.vertical_block.render.completed.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: xmodule/vertical_block.py
        - Function or Method: VerticalBlock._student_or_public_view
    """

    def run_filter(self, **data):
        """
        data = block: Any, fragment: Any, context: dict[str, Any], view: str

                Process the inputs using the configured pipeline steps to modify the rendering of a vertical block.

        Arguments:
            block (VerticalBlock): The VeriticalBlock instance which is being rendered.
            fragment (web_fragments.Fragment): The web-fragment containing the rendered content of VerticalBlock.
            context (dict): rendering context values like is_mobile_app, show_title..etc.
            view (str): the rendering view. Can be either 'student_view', or 'public_view'.

        Returns:
            tuple[VeticalBlock, web_fragments.Fragment, dict, str]:
                - VerticalBlock: The VeriticalBlock instance which is being rendered.
                - web_fragments.Fragment: The web-fragment containing the rendered content of VerticalBlock.
                - dict: rendering context values like is_mobile_app, show_title..etc.
                - str: the rendering view. Can be either 'student_view', or 'public_view'.
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=VerticalBlockRenderCompleted.PreventVerticalBlockRender)

            return_data['context'].update(content.get('context', {}))
            return_data['view'] = content.get('view', data.get('view'))

            _check_for_exception(exceptions, VerticalBlockRenderCompleted.PreventVerticalBlockRender)

            return return_data

        return data


class CourseHomeUrlCreationStartedWebFilter(PipelineStep):
    """
    Filter used to modify the course home url creation process.

    Purpose:
        This filter is triggered when a course home url is being generated, just before the generation process is
        completed allowing the filter to act on the course key and course home url.

    Filter Type:
        org.openedx.learning.course.homepage.url.creation.started.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: openedx/features/course_experience/__init__.py
        - Function or Method: course_home_url
    """

    def run_filter(self, **data):
        """
        data = course_key: CourseKey, course_home_url: str
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            course_key = data.get('course_key')
            course_id = f"course-v1:{course_key.org}+{course_key.course}+{course_key.run}"

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data={"course_id": course_id, "course_home_url": data.get('course_home_url')},
                                                  exception=CourseHomeUrlCreationStarted.PreventChildBlockRender)

            return_data['course_home_url'] = content.get('course_home_url', data.get('course_home_url'))

            return return_data

        return data


class CourseEnrollmentAPIRenderStartedWebFilter(PipelineStep):
    """
    Filter used to modify the course enrollment API rendering process.

    Purpose:
        This filter is triggered when a user requests to view the course enrollment API, just before the API is rendered
        allowing the filter to act on the course key and serialized enrollment data.

    Filter Type:
        org.openedx.learning.home.enrollment.api.rendered.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: lms/djangoapps/learner_home/serializers.py
        - Function or Method: EnrollmentSerializer.to_representation
    """

    def run_filter(self, **data):
        """
        data = course_key: CourseKey, serialized_enrollment: dict[str, Any]
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            course_key = data.get('course_key')
            course_id = f"course-v1:{course_key.org}+{course_key.course}+{course_key.run}"

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data={"course_id": course_id, "serialized_enrollment": data.get('serialized_enrollment')},
                                                  exception=None)

            return_data['serialized_enrollment'] = content.get('serialized_enrollment', data.get('serialized_enrollment'))

            return return_data

        return data


class CourseRunAPIRenderStartedWebFilter(PipelineStep):
    """
    Filter used to modify the course run API rendering process.

    Purpose:
        This filter is triggered when a user requests to view the course run API, just before the API is rendered
        allowing the filter to act on the serialized course run data.

    Filter Type:
        org.openedx.learning.home.courserun.api.rendered.started.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: lms/djangoapps/learner_home/serializers.py
        - Function or Method: CourseRunSerializer.to_representation
    """

    def run_filter(self, **data):
        """
        data = serialized_courserun: dict[str, Any]
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=None)

            return_data.update(content)

            return return_data

        return data


class InstructorDashboardRenderStartedWebFilter(PipelineStep):
    """
    Filter used to modify the instructor dashboard rendering process.

    Purpose:
        This filter is triggered when an instructor requests to view the dashboard, just before the page is rendered
        allowing the filter to act on the context and the template used to render the page.

    Filter Type:
        org.openedx.learning.instructor.dashboard.render.started.v1

    Trigger:
        - Repository: openedx/edx-platform
        - Path: lms/djangoapps/instructor/views/instructor_dashboard.py
        - Function or Method: instructor_dashboard_2
    """

    def run_filter(self, **data):
        """
        data = context: dict[str, Any], template_name: str
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=InstructorDashboardRenderStarted.RenderInvalidDashboard)

            return_data.update(content)

            _check_for_exception(exceptions, InstructorDashboardRenderStarted.RedirectToPage)
            _check_for_exception(exceptions, InstructorDashboardRenderStarted.RenderInvalidDashboard)
            _check_for_exception(exceptions, InstructorDashboardRenderStarted.RenderCustomResponse)

            return return_data

        return data


class ORASubmissionViewRenderStartedWebFilter(PipelineStep):
    """
    Filter used to modify the submission view rendering process.

    Purpose:
        This filter is triggered when a user requests to view the submission, just before the page is rendered allowing
        the filter to act on the context and the template used to render the page.

    Filter Type:
        org.openedx.learning.ora.submission_view.render.started.v1

    Trigger:
        - Repository: openedx/edx-ora2
        - Path: openassessment/xblock/ui_mixins/legacy/views/submission.py
        - Function or Method: render_submission
    """

    def run_filter(self, **data):
        """
        data = context: dict[str, Any], template_name: str
        """

        # The event is the class name, except the last "WebFilter"
        event = type(self).__name__[:-9]

        return_data = data.copy()
        webfilters = Webfilter.objects.filter(enabled=True, event=event)

        if webfilters:
            logger.info(f"Webfilter for {event} event.")

            content, exceptions = _process_filter(webfilters=webfilters,
                                                  data=data,
                                                  exception=ORASubmissionViewRenderStarted.RenderInvalidTemplate)

            return_data.update(content)

            _check_for_exception(exceptions, ORASubmissionViewRenderStarted.RenderInvalidTemplate)

            return return_data

        return data


# class IDVPageURLRequestedWebFilter(PipelineStep):
#     """
#     Filter used to act on ID verification page URL requests.
#
#     Purpose:
#         This filter is triggered when a user requests to view the ID verification page, just before the page is rendered
#         allowing the filter to act on the URL of the page.
#
#     Filter Type:
#         org.openedx.learning.idv.page.url.requested.v1
#
#     Trigger:
#         - Repository: openedx/edx-platform
#         - Path: lms/djangoapps/verify_student/services.py
#         - Function or Method: XBlockVerificationService.get_verify_location
#     """
#
#     def run_filter(self, **data):
#         """
#         data = url: str
#         """
#         # The event is the class name, except the last "WebFilter"
#         event = type(self).__name__[:-9]
#
#         return_data = data.copy()
#         webfilters = Webfilter.objects.filter(enabled=True, event=event)
#
#         if webfilters:
#             logger.info(f"Webfilter for {event} event.")
#
#             content, exceptions = _process_filter(webfilters=webfilters,
#                                                   data=data)
#
#             return_data.update(content)
#
#             return return_data
#
#         return data
#
#
# class CourseAboutPageURLRequestedWebFilter(PipelineStep):
#     """
#     Filter used to act on course about page URL requests.
#
#     Purpose:
#         This filter is triggered when a user requests to view the course about page, just before the page is rendered
#         allowing the filter to act on the URL of the page and the course org.
#
#     Filter Type:
#         org.openedx.learning.course_about.page.url.requested.v1
#
#     Trigger:
#         - Repository: openedx/edx-platform
#         - Path: common/djangoapps/util/course.py
#         - Function or Method: get_link_for_about_page
#      """
#
#     def run_filter(self, **data):
#         """
#         data = url: str, org: str
#         """
#
#         # The event is the class name, except the last "WebFilter"
#         event = type(self).__name__[:-9]
#
#         return_data = data.copy()
#         webfilters = Webfilter.objects.filter(enabled=True, event=event)
#
#         if webfilters:
#             logger.info(f"Webfilter for {event} event.")
#
#             content, exceptions = _process_filter(webfilters=webfilters,
#                                                   data=data)
#
#             return_data.update(content)
#
#             return return_data
#
#         return data
#
#
#
# class ScheduleQuerySetRequestedWebFilter(PipelineStep):
#     """
#     Filter used to apply additional filtering to a given QuerySet of Schedules.
#
#     Purpose:
#         This filter is triggered when a QuerySet of Schedules is requested, allowing the filter to act on the schedules
#         data. If you want to know more about the Schedules feature, please refer to the official documentation:
#             - https://github.com/openedx/edx-platform/tree/master/openedx/core/djangoapps/schedules#readme
#
#     Filter Type:
#         org.openedx.learning.schedule.queryset.requested.v1
#
#     Trigger:
#         - Repository: openedx/edx-platform
#         - Path: openedx/core/djangoapps/schedules/resolvers.py
#         - Function or Method: BinnedSchedulesBaseResolver.get_schedules_with_target_date_by_bin_and_orgs
#     """
#
#     def run_filter(self, **data):
#         """
#         data = schedules: QuerySet
#         """
#
#         # The event is the class name, except the last "WebFilter"
#         event = type(self).__name__[:-9]
#
#         return_data = data.copy()
#         return_data['schedules'] = list(data['schedules'].values())
#
#         webfilters = Webfilter.objects.filter(enabled=True, event=event)
#
#         if webfilters:
#             logger.info(f"Webfilter for {event} event.")
#
#             content, exceptions = _process_filter(webfilters=webfilters,
#                                                   data=data)
#
#             return_data['schedules'] = data['schedules'].filter(content.get('filter', {}))
#
#             return return_data
#
#         return data
#
#
#     class LMSPageURLRequestedWebFilter(PipelineStep):
#         """
#         Filter used to modify the URL of the page requested by the user.
#
#         Purpose:
#             This filter is triggered when a user loads a page in Studio that references an LMS page, allowing the filter to
#             modify the URL of the page requested by the user.
#
#         Filter Type:
#             org.openedx.content_authoring.lms.page.url.requested.v1
#
#         Trigger:
#             - Repository: openedx/edx-platform
#             - Path: cms/djangoapps/contentstore/asset_storage_handler.py
#             - Function or Method: get_asset_json
#         """
#
#         def run_filter(self, **data):
#             """
#             data = url: str, org: str
#             """
#
#             # The event is the class name, except the last "WebFilter"
#             event = type(self).__name__[:-9]
#
#             return_data = data.copy()
#
#             webfilters = Webfilter.objects.filter(enabled=True, event=event)
#
#             if webfilters:
#                 logger.info(f"Webfilter for {event} event.")
#
#                 content, exceptions = _process_filter(webfilters=webfilters,
#                                                       data=data)
#
#                 return_data.update(content)
#
#                 return return_data
#
#             return data
