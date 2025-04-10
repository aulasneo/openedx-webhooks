Open edX Webhooks
#############################

|pypi-badge| |ci-badge| |codecov-badge| |doc-badge| |pyversions-badge|
|license-badge| |status-badge|

Purpose
*******

Webhooks for Open edX

This plugin implements a generic case of events handling that
trigger a request to a configurable URL when a signal is received.

Getting Started
***************

Introduction
============

A `Webhook` is a mechanism that triggers an HTTP POST request to a configurable
URL when certain events happen in the platform, including information relevant
to the event. For example, you can make the platform call an API when a user
logs in, including the user ID and email to connect to another application.

A `Webfilter` is a special case of webhook that allows also modifying the
data and/or interrupting the process. For example, after the user login event
you can update the user full name or prevent the user to log in if it is not
allowed to.

Deploying
=========

To install this plugin into an Open edX installed by Tutor add this line
to the ``OPENEDX_EXTRA_PIP_REQUIREMENTS`` list in the ``config.yml`` file.

.. code-block::

    OPENEDX_EXTRA_PIP_REQUIREMENTS:
    - openedx-webhooks

If it is an existing installation, you might need to run migrations to create
the database table. For this, run:

.. code-block::

     tutor {dev|local|k8s} exec lms ./manage.py lms migrate

Configuring
===========

A new section named `OPENEDX_WEBHOOKS` will be available in the LMS Django
admin site. It will contain two subsections: `Webhooks` and `Webfilters`.
Add a new webhook to define the URLs that will be called after each event is
received. More than one URL can be configured for each event. In this case,
all URLs will be called.

Configuring webhooks
--------------------

The `Webhooks` Django admin panel has the following settings:

* Description: Add a description for this webhook for reference.
* Event: Choose from the list the event that will trigger the webhook.
* Webhook URL: URL to call. Get it from your webhook processor.
* Enabled: Click to enable the webhook.
* Use WWW form encoding: When enabled, the data will be passed in a web form format. If disabled, data will be passed in JSON format.

Configuring webfilters
----------------------

The `Webfilters` Django admin panel has the following settings:

* Description: Add a description for this webhook for reference.
* Event: Choose from the list the event that will trigger the webhook.
* Webhook URL: URL to call. Get it from your webhook processor.
* Enabled: Click to enable the webhook.
* Disable filtering: If enabled, the data passed to the web filter will not be modified even if the response includes any update.
* Disable halting: If enabled, the process will not be interrupted even if the response includes an exception setting.
* Halt on 4xx: Interrupt the process if the call to the URL returns any 4xx error code.
* Redirect on 4xx: Include an URL to redirect in case of a 4xx response, if the event supports redirection.
* Halt on 5xx: Interrupt the process if the call to the URL returns any 5xx error code.
* Redirect on 5xx: Include an URL to redirect in case of a 5xx response, if the event supports redirection.
* Halt on request exception: Interrupt the process if the call to the URL results in a connection error (e.g., timeout).
* Redirect on request exception: Include an URL to redirect in case of a connection error, if the event supports redirection.
* Use WWW form encoding: When enabled, the data will be passed in a web form format. If disabled, data will be passed in JSON format.

Receiving data
--------------

Both webhooks and webfilters will trigger POST requests to the configured URL.
This request includes in the payload a structure with data relevant to the
event that triggered the call. In all cases, the payload will include an
``event_metadata`` key including at least the event type and the date and time
in UTC format. Other keys included will depend on the event. For example,
log in events usually include ``user`` and ``profile`` keys with details of the
user logging in.

If the ``Use WWW form encoding`` option is enabled, the data will be passed as
plain key-value pairs in form encoding. The structure will be flattened and the
key names will be concatenated. E.g., a log event will include ``user_id``,
``user_email``, ``event_metadata_time``, etc.

Responding to webfilters
------------------------

The webhook processor should respond to a webfilter with a data structure in
JSON format and a successful status code (200). The response can be empty or
can have one or both of these keys:

* data
* exception

Updating data
~~~~~~~~~~~~~

The corresponding objects will be updated with the values returned inside the
``data`` key. Only keys present in the response will be updated. Other keys
will remain unchanged in the original data structures. To disable data updates,
set ``Disable Filtering`` in the webfilter configuration at the Django admin
panel.

For example, to change the full name of a user at registration time, respond
to a `Student Registration Requested` webfilter with this data:

.. code-block::

    {
        "data": {
            "form_data": {
                "name": "New Name"
            }
        }
    }

Interrupting execution
~~~~~~~~~~~~~~~~~~~~~~

To stop the process to complete, add a JSON object as value for the `exception`
key. This object must have only one key-value pair, being the key the name
of the exception to raise. Its value can be either a string representing the
message to be shown, or another JSON object with more data.

For example, to prevent a user to register, respond to the `Student
Registration Requested` webfilter with this data:

.. code-block::

    {
        "exception": {
            "PreventRegistration": "Not allowed to register"
        }
    }

To prevent a webfilter to stop the execution of the process, set ``Disable
halting`` in the webfilter configuration at the Django admin
panel.

Check each function documentation to see the list of available values and
exceptions.

Handling multiple events
------------------------

If you set more than one webhook or webfilter for the same event, all of them
will be triggered. The responses of all the webfilters will be combined in one
data structure and used to update the objects. If more webfilter processors
include data for the same key, the last one will override all the previous.

Developing
==========


More information about available signals can be found in the `events documentation`_
and the `filters documentation`_

.. _events documentation: https://github.com/openedx/edx-platform/blob/master/docs/guides/hooks/events.rst
.. _filters documentation: https://github.com/openedx/edx-platform/blob/master/docs/guides/hooks/filters.rst


Adding more filters
-------------------

From version to version new filters are added to Open edX.
The complete list of filters and their definition can be found in filters.py at
the `openedx-filter repo`_.

.. _openedx-filter repo: https://github.com/openedx/openedx-filters/blob/main/openedx_filters/learning/filters.py

To add a new filter, create the filter class handler in ``filters.py``
containing the ``run_filter`` function. Then add a block in ``common.py``
linking the signal identifier with the function. Remember that ``run_filter``
must always return a dict (which can be empty).

Adding new event hooks
----------------------

From version to version new event producers are added to Open edX.
The complete list of events and their definition can be found in ``signals.py``
in different folders at the `openedx-events repo`_,
depending on their category.

.. _openedx-events repo: https://github.com/openedx/openedx-events/tree/main/openedx_events

To add a new event hook, add the signal to the ``signals`` dict in ``apps.py``.
Then add the corresponding block to ``receivers.py``.

One Time Setup
--------------
.. code-block::

  # Clone the repository
  git clone git@github.com:aulasneo/openedx-webhooks.git
  cd openedx-webhooks

  # Set up a virtualenv with the same name as the repo and activate it
  # Here's how you might do that if you have virtualenvwrapper setup.
  mkvirtualenv -p python3.8 openedx-webhooks


Every time you develop something in this repo
---------------------------------------------
.. code-block::

  # Activate the virtualenv
  # Here's how you might do that if you're using virtualenvwrapper.
  workon openedx-webhooks

  # Grab the latest code
  git checkout main
  git pull

  # Install/update the dev requirements
  make requirements

  # Run the tests and quality checks (to verify the status before you make any changes)
  make validate

  # Make a new branch for your changes
  git checkout -b <your_github_username>/<short_description>

  # Using your favorite editor, edit the code to make your change.
  vim ...

  # Run your new tests
  pytest ./path/to/new/tests

  # Run all the tests and quality checks
  make validate

  # Commit all your changes
  git commit ...
  git push

  # Open a PR and ask for review.

Getting Help
************

If you need any help, send us an email to `info@aulasneo.com`_.

.. _info@aulasneo.com: mailto:info@aulasneo.com

More Help
=========

If you're having trouble, we have discussion forums at
https://discuss.openedx.org where you can connect with others in the
community.

Our real-time conversations are on Slack. You can request a `Slack
invitation`_, then join our `community Slack workspace`_.

For anything non-trivial, the best path is to open an issue in this
repository with as many details about the issue you are facing as you
can provide.

https://github.com/aulasneo/openedx-webhooks/issues

For more information about these options, see the `Getting Help`_ page.

.. _Slack invitation: https://openedx.org/slack
.. _community Slack workspace: https://openedx.slack.com/
.. _Getting Help: https://openedx.org/getting-help

License
*******

The code in this repository is licensed under the AGPL 3.0 unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Contributing
************

Contributions are very welcome.
If you want to contribute to this project, please feel free to open an issue.

Reporting Security Issues
*************************

Please do not report security issues in public.
Please email `operations@aulasneo.com <mailto:operations@aulasneo.com>`_.

.. |pypi-badge| image:: https://img.shields.io/pypi/v/openedx-webhooks.svg
    :target: https://pypi.python.org/pypi/openedx-webhooks/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/aulasneo/openedx-webhooks/workflows/Python%20CI/badge.svg?branch=master
    :target: https://github.com/aulasneo/openedx-webhooks/actions
    :alt: CI

.. |codecov-badge| image:: https://codecov.io/github/aulasneo/openedx-webhooks/coverage.svg?branch=main
    :target: https://codecov.io/github/aulasneo/openedx-webhooks?branch=master
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/openedx-webhooks/badge/?version=latest
    :target: https://github.com/aulasneo/openedx-webhooks
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/openedx-webhooks.svg
    :target: https://pypi.python.org/pypi/openedx-webhooks/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/aulasneo/openedx-webhooks.svg
    :target: https://github.com/aulasneo/openedx-webhooks/blob/master/LICENSE.txt
    :alt: License

.. .. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
.. |status-badge| image:: https://img.shields.io/badge/Status-Maintained-brightgreen
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Deprecated-orange
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Unsupported-red
