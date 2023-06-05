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

Developing
==========

More information about available signals can be found in the `events documentation`_
and the `filters documentation`_

.. _events documentation: https://github.com/openedx/edx-platform/blob/master/docs/guides/hooks/events.rst
.. _filters documentation: https://github.com/openedx/edx-platform/blob/master/docs/guides/hooks/filters.rst


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

Deploying
=========

To install this plugin into an Open edX installed by Tutor add this line
to the `OPENEDX_EXTRA_PIP_REQUIREMENTS` list.

.. code-block::

    - git+https://github.com/aulasneo/openedx-webhooks

If it is an existing installation, you might need to run migrations to create
the database table. For this, run:

.. code-block::

     tutor {dev|local|k8s} exec lms ./manage.py lms migrate

Configuring
===========

A new section named `Webhooks` will be available in the LMS Django admin site.
Add a new webhook to define the URLs that will be called after each event is
received. More than one URL can be configured for each event. In this case,
all URLs will be called.

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
Please read `How To Contribute <https://openedx.org/r/how-to-contribute>`_ for details.

This project is currently accepting all types of contributions, bug fixes,
security fixes, maintenance work, or new features.  However, please make sure
to have a discussion about your new feature idea with the maintainers prior to
beginning development to maximize the chances of your change being accepted.
You can start a conversation by creating a new issue on this repo summarizing
your idea.

The Open edX Code of Conduct
****************************

All community members are expected to follow the `Open edX Code of Conduct`_.

.. _Open edX Code of Conduct: https://openedx.org/code-of-conduct/

People
******

The assigned maintainers for this component and other project details may be
found in `Backstage`_. Backstage pulls this data from the ``catalog-info.yaml``
file in this repo.

.. _Backstage: https://backstage.openedx.org/catalog/default/component/webhooks

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@tcril.org.

.. |pypi-badge| image:: https://img.shields.io/pypi/v/webhooks.svg
    :target: https://pypi.python.org/pypi/webhooks/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/openedx/webhooks/workflows/Python%20CI/badge.svg?branch=main
    :target: https://github.com/openedx/webhooks/actions
    :alt: CI

.. |codecov-badge| image:: https://codecov.io/github/openedx/webhooks/coverage.svg?branch=main
    :target: https://codecov.io/github/openedx/webhooks?branch=main
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/webhooks/badge/?version=latest
    :target: https://docs.openedx.org/projects/webhooks
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/webhooks.svg
    :target: https://pypi.python.org/pypi/webhooks/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/openedx/webhooks.svg
    :target: https://github.com/openedx/webhooks/blob/main/LICENSE.txt
    :alt: License

.. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Maintained-brightgreen
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Deprecated-orange
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Unsupported-red
