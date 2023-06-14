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
from django.db import models
from opaque_keys.edx.keys import CourseKey
from openedx_filters import PipelineStep
from openedx_filters.learning.filters import (
    CertificateCreationRequested,
    CourseEnrollmentStarted,
    CourseUnenrollmentStarted,
    StudentLoginRequested,
    StudentRegistrationRequested,
)

from .models import Webfilter
from .utils import send

logger = logging.getLogger(__name__)


def _process_filter(event_name, data, exception):
    """
    Process all events with user data.
    """
    logger.debug(f"Processing filter: {event_name}")
    webfilters = Webfilter.objects.filter(enabled=True, event=event_name)

    response_data = {}
    response_exceptions = {}

    # Convert model objects to dicts, and remove '_state'
    payload = {}
    for key, value in data.items():
        if isinstance(value, models.Model):
            payload[key] = value.__dict__.copy()
            payload[key].pop('_state', None)
        else:
            payload[key] = value

    # Add event metadata
    payload['event_metadata'] = {
        'event_type': event_name,
        'time': str(datetime.now())
    }

    for webfilter in webfilters:
        logger.info(f"{event_name} webhook filter triggered to {webfilter.webhook_url}")

        try:
            # Send the request to the webhook URL
            response = send(webfilter.webhook_url, payload)

        except requests.exceptions.RequestException as e:
            if webfilter.halt_on_request_exception:
                logger.info(f"Halting on request exception '{e.strerror}'. "
                            f"{event_name} webhook filter triggered to {webfilter.webhook_url}")
                raise exception(
                    message=e.strerror,
                    redirect_to=webfilter.redirect_on_request_exception,
                ) from e
            logger.info(f"Not halting on request exception '{e}'."
                        f"{event_name} webhook filter triggered to {webfilter.webhook_url}")
            return None

        if 400 <= response.status_code <= 499 and webfilter.halt_on_4xx:
            logger.info(f"Request to {webfilter.webhook_url} after webhook event {event_name} returned status code "
                        f"{response.status_code} ({response.reason}). Redirecting to {webfilter.redirect_on_4xx}")
            raise exception(
                message=f"Request to {webfilter.webhook_url} after webhook event {event_name} returned status code "
                        f"{response.status_code} ({response.reason})",
                redirect_to=webfilter.redirect_on_4xx,
                status_code=response.status_code
            )

        if 500 <= response.status_code <= 599 and webfilter.halt_on_5xx:
            logger.info(f"Request to {webfilter.webhook_url} after webhook event {event_name} returned status code "
                        f"{response.status_code} ({response.reason}). Redirecting to {webfilter.redirect_on_5xx}")
            raise exception(
                message=f"Request to {webfilter.webhook_url} after webhook event {event_name} returned status code "
                        f"{response.status_code} ({response.reason})",
                redirect_to=webfilter.redirect_on_5xx,
                status_code=response.status_code
            )

        logger.info(f"Request to {webfilter.webhook_url} after webhook event {event_name} returned status code "
                    f"{response.status_code} ({response.reason}).")

        response = json.loads(response.text)

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
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(getattr(o, key), datetime):
                # Handle date time data
                setattr(o, key, datetime.fromisoformat(value))
            elif isinstance(getattr(o, key), bool):
                setattr(o, key, value.lower() == 'true')
            else:
                setattr(o, key, value)


def _check_for_exception(exceptions, exception_class):
    """
    Check if an exception configuration exists and then raises the exception.
    """
    if exception_class.__name__ in exceptions:
        exception_settings = exceptions.get(exception_class.__name__)
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
        logger.info(f"Webfilter for {event} event for user {user}")

        if user:
            # If the log in attempt is unsuccessfull, the user object will be None
            content, exceptions = _process_filter(event_name=event,
                                                  data={
                                                      "user": user,
                                                      "profile": user.profile,
                                                  },
                                                  exception=StudentLoginRequested.PreventLogin)

            update_model(user, content.get('user'))
            update_model(user.profile, content.get('profile'))
        else:
            content, exceptions = _process_filter(event_name=event,
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
        logger.info(f"Webfilter for {event} event. Form data: {form_data}.")

        content, exceptions = _process_filter(event_name=event,
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
        logger.info(f"Webfilter for {event} event. User: {user}, course: {course_key}, mode: {mode}.")

        data = {
            'user': user,
            'profile': user.profile,
            'course_key': course_key,
            'mode': mode,
        }
        content, exceptions = _process_filter(event_name=event,
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
        logger.info(f"Webfilter for {event} event. Enrollment: {enrollment}")

        user = enrollment.user

        data = {
            'user': user,
            'profile': user.profile,
            'enrollment': enrollment,
        }
        content, exceptions = _process_filter(event_name=event,
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
            "password": "pbkdf2_sha256$260000$ybxHo0UuhL7dJKFFqSUBIz$j3BMW1/Ubt3E0kB324l+JNT2pYcWeBgUGctDsHTSYbE=",
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
            "_subsection_grade_factory": "<lms.djangoapps.grades.subsection_grade_factory.SubsectionGradeFactory object at 0x7fb70a728310>"
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
            generation_mode (str): Options are "self" (implying the user generated the cert themself) and "batch"
                for everything else.
        """
        event = "CertificateCreationRequested"
        logger.info(f"Webfilter for {event} event. User: {user}, course: {course_key}, status: {status}")

        data = {
            "user": user,
            "profile": user.profile,
            "course_key": course_key,
            "mode": mode,
            "status": status,
            "grade": grade.__dict__,
            "generation_mode": generation_mode,
        }

        content, exceptions = _process_filter(event_name=event,
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
