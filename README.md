# Open edX Webhooks

[![PyPI](https://img.shields.io/pypi/v/openedx-webhooks.svg)](https://pypi.python.org/pypi/openedx-webhooks/)
[![CI](https://github.com/aulasneo/openedx-webhooks/workflows/Python%20CI/badge.svg?branch=master)](https://github.com/aulasneo/openedx-webhooks/actions)
[![Codecov](https://codecov.io/github/aulasneo/openedx-webhooks/coverage.svg?branch=main)](https://codecov.io/github/aulasneo/openedx-webhooks?branch=master)
[![Documentation](https://readthedocs.org/projects/openedx-webhooks/badge/?version=latest)](https://github.com/aulasneo/openedx-webhooks)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/openedx-webhooks.svg)](https://pypi.python.org/pypi/openedx-webhooks/)
[![License](https://img.shields.io/github/license/aulasneo/openedx-webhooks.svg)](https://github.com/aulasneo/openedx-webhooks/blob/master/LICENSE.txt)
![Status](https://img.shields.io/badge/Status-Maintained-brightgreen)

## Purpose

Webhooks for Open edX.

Current compatibility target: Open edX Ulmo / Tutor 21.x.

This plugin implements a generic case of event handling that triggers a request
to a configurable URL when a signal is received.

## Getting Started

### Introduction

A `Webhook` triggers an HTTP POST request to a configurable URL when certain
events happen in the platform, including information relevant to the event. For
example, you can make the platform call an API when a user logs in, including
the user ID and email to connect to another application.

A `Webfilter` is a special case of webhook that can also modify data and/or
interrupt the process. For example, after the user login event you can update
the user full name or prevent the user from logging in.

### Deploying

To install this plugin into an Open edX instance installed by Tutor, add this
line to the `OPENEDX_EXTRA_PIP_REQUIREMENTS` list in `config.yml`.

```yaml
OPENEDX_EXTRA_PIP_REQUIREMENTS:
  - openedx-webhooks
```

This release targets Open edX Ulmo and Tutor 21.x, which use Python 3.11.

If it is an existing installation, you might need to run migrations to create
the database table:

```bash
tutor {dev|local|k8s} exec lms ./manage.py lms migrate
```

This plugin now registers extension points in both LMS and CMS. Webhook and
webfilter configuration is still managed through Django admin and the same
database tables.

## Configuring

A new section named `OPENEDX_WEBHOOKS` is available in the LMS Django admin
site. It contains two subsections: `Webhooks` and `Webfilters`. Add a new
webhook to define the URLs that will be called after each event is received.
More than one URL can be configured for each event. In that case, all URLs are
called.

### Configuring Webhooks

The `Webhooks` Django admin panel has the following settings:

- Description: Add a description for this webhook for reference.
- Event: Choose from the list the event that will trigger the webhook.
- Webhook URL: URL to call. Get it from your webhook processor.
- Enabled: Click to enable the webhook.
- Use WWW form encoding: When enabled, the data will be passed in web form
  format. If disabled, data will be passed in JSON format.

### Configuring Webfilters

The `Webfilters` Django admin panel has the following settings:

- Description: Add a description for this webhook for reference.
- Event: Choose from the list the event that will trigger the webhook.
- Webhook URL: URL to call. Get it from your webhook processor.
- Enabled: Click to enable the webhook.
- Disable filtering: If enabled, the data passed to the web filter will not be
  modified even if the response includes any update.
- Disable halting: If enabled, the process will not be interrupted even if the
  response includes an exception setting.
- Halt on 4xx: Interrupt the process if the call to the URL returns any 4xx
  error code.
- Redirect on 4xx: Include a URL to redirect in case of a 4xx response, if the
  event supports redirection.
- Halt on 5xx: Interrupt the process if the call to the URL returns any 5xx
  error code.
- Redirect on 5xx: Include a URL to redirect in case of a 5xx response, if the
  event supports redirection.
- Halt on request exception: Interrupt the process if the call to the URL
  results in a connection error such as a timeout.
- Redirect on request exception: Include a URL to redirect in case of a
  connection error, if the event supports redirection.
- Use WWW form encoding: When enabled, the data will be passed in web form
  format. If disabled, data will be passed in JSON format.

## Receiving Data

Both webhooks and webfilters trigger POST requests to the configured URL. The
payload includes data relevant to the event that triggered the call. In all
cases, the payload includes an `event_metadata` key with at least the event
type and the date and time in UTC format. Other keys depend on the event. For
example, login events usually include `user` and `profile` keys with details of
the user logging in.

If the `Use WWW form encoding` option is enabled, the data is passed as plain
key-value pairs in form encoding. The structure is flattened and the key names
are concatenated. For example, a login event includes `user_id`,
`user_email`, `event_metadata_time`, and similar fields.

## Responding to Webfilters

The webhook processor should respond to a webfilter with a JSON structure and a
successful status code (`200`). The response can be empty or can have one or
both of these keys:

- `data`
- `exception`

### Updating Data

The corresponding objects are updated with the values returned inside the
`data` key. Only keys present in the response are updated. Other keys remain
unchanged in the original data structures. To disable data updates, set
`Disable Filtering` in the webfilter configuration in the Django admin panel.

For example, to change the full name of a user at registration time, respond to
the `Student Registration Requested` webfilter with this data:

```json
{
  "data": {
    "form_data": {
      "name": "New Name"
    }
  }
}
```

### Interrupting Execution

To stop the process, add a JSON object as the value for the `exception` key.
This object must have only one key-value pair: the key is the name of the
exception to raise, and the value can be either a string representing the
message to show or another JSON object with more data.

For example, to prevent a user from registering, respond to the `Student
Registration Requested` webfilter with this data:

```json
{
  "exception": {
    "PreventRegistration": "Not allowed to register"
  }
}
```

To prevent a webfilter from stopping the process, set `Disable halting` in the
webfilter configuration in the Django admin panel.

Check each function documentation to see the list of available values and
exceptions.

## Handling Multiple Events

If you set more than one webhook or webfilter for the same event, all of them
are triggered. The responses of all webfilters are combined into one data
structure and used to update the objects. If more than one webfilter processor
includes data for the same key, the last one overrides the previous ones.

## Developing

More information about available signals can be found in the [events
documentation](https://docs.openedx.org/projects/openedx-events/en/stable/reference/events.html)
and the [filters
documentation](https://docs.openedx.org/projects/openedx-filters/en/stable/reference/filters.html).

Ulmo compatibility in this package is aligned with:

- `openedx-filters==2.1.0`
- `openedx-events==10.5.0`

Supported Ulmo-era additions in this release include:

- New webhook events:
  - `LTI_PROVIDER_LAUNCH_SUCCESS`
  - `COURSE_RERUN_COMPLETED`
- Filter review against the current upstream reference found no new Ulmo filter
  types, and no renames or deprecations affecting the filters already
  registered by this plugin.

Existing recent coverage retained from prior releases includes:

- Filter: `AccountSettingsRenderStarted`
- Signals:
  - `EXTERNAL_GRADER_SCORE_SUBMITTED`
  - `LIBRARY_BLOCK_PUBLISHED`
  - `LIBRARY_CONTAINER_CREATED`
  - `LIBRARY_CONTAINER_UPDATED`
  - `LIBRARY_CONTAINER_DELETED`
  - `LIBRARY_CONTAINER_PUBLISHED`
  - `COURSE_IMPORT_COMPLETED`

### Adding More Filters

From version to version, new filters are added to Open edX. The complete list
of filters and their definitions can be found in `filters.py` in the
[openedx-filters repository](https://github.com/openedx/openedx-filters/blob/v2.1.0/openedx_filters/learning/filters.py).

To add a new filter, create the filter class handler in `filters.py`
containing the `run_filter` function. Then add a block in `common.py` linking
the signal identifier with the function. `run_filter` must always return a
dict, which can be empty.

### Adding New Event Hooks

From version to version, new event producers are added to Open edX. The
complete list of events and their definitions can be found in `signals.py` in
different folders in the
[openedx-events repository](https://github.com/openedx/openedx-events/tree/v10.5.0/openedx_events),
depending on their category.

To add a new event hook, add the signal to the `signals` dict in `apps.py`.
Then add the corresponding block to `receivers.py`.

### One-Time Setup

```bash
# Clone the repository
git clone git@github.com:aulasneo/openedx-webhooks.git
cd openedx-webhooks

# Set up a virtualenv with the same name as the repo and activate it
# Here's how you might do that if you have virtualenvwrapper setup.
mkvirtualenv -p python3.11 openedx-webhooks
```

### Every Time You Develop Something In This Repo

```bash
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
```

## Releasing

PyPI publishing uses GitHub Actions with PyPI trusted publishing. The release
workflow no longer uses a long-lived PyPI API token. Configure the project's
trusted publisher in PyPI before cutting a GitHub release.

Release automation expects tags in the format `release/v<version>`, for example
`release/v21.0.0`. Pushing one of those tags from a commit contained in `main`
creates a GitHub release, and the publish workflow can also be run manually
from the Actions tab when needed.

## Getting Help

If you need any help, email [info@aulasneo.com](mailto:info@aulasneo.com).

## More Help

If you're having trouble, there are discussion forums at
<https://discuss.openedx.org> where you can connect with others in the
community.

Real-time conversations are on Slack. You can request a [Slack
invitation](https://openedx.org/slack), then join the [community Slack
workspace](https://openedx.slack.com/).

For anything non-trivial, the best path is to open an issue in this repository
with as many details about the issue as possible:

<https://github.com/aulasneo/openedx-webhooks/issues>

For more information about these options, see the [Getting
Help](https://openedx.org/getting-help) page.

## License

The code in this repository is licensed under the AGPL 3.0 unless otherwise
noted.

See [LICENSE.txt](LICENSE.txt) for details.

## Contributing

Contributions are very welcome. If you want to contribute to this project,
please feel free to open an issue.

## Reporting Security Issues

Please do not report security issues in public. Email
[operations@aulasneo.com](mailto:operations@aulasneo.com).
