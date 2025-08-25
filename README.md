# Spatial Temporal Oceanographic Query System

[![DOI](https://zenodo.org/badge/20654/stoqs/stoqs.svg)](https://zenodo.org/badge/latestdoi/20654/stoqs/stoqs)

STOQS is a geospatial database and web application designed to give oceanographers
efficient integrated access to *in situ* measurement and *ex situ* sample data.
See <http://www.stoqs.org>.

## Install a local development system using Docker

The instructions here are tailored for its development and operation on
MacOS arm systems.

### First time

Install [Docker](https://docker.io) and [just](https://ports.macports.org/port/just/) for MacOS.
Change directory to a location where you will clone this repository.
Clone the repo and start the services with these commands:

```
# In your home directory or other preferred location do the following
# cd to a development directory, e.g. ~/GitHub
git clone git@github.com:stoqs/stoqs.git stoqsgit
cd stoqsgit

# Build the containers
just build

# Follow instructions in the template.env file

# Start the development server the first time
just up

# Monitor the logs
just logs

```

You should see local auth, users, admin, account, etc. tables created in your local database:

```
...
django              | Running migrations:
django              |   Applying contenttypes.0001_initial... OK
django              |   Applying contenttypes.0002_remove_content_type_name... OK
django              |   Applying auth.0001_initial... OK
django              |   Applying auth.0002_alter_permission_name_max_length... OK
django              |   Applying auth.0003_alter_user_email_max_length... OK
...
```

View the development web site at <http://localhost:8000>.

### After first time

Shutdown, restart, develop, and monitor (typical operation following initial install):

```
just down
just up
code .
just logs
```

Click on the button to "Reopen in Container" in the VS Code window

## Deploy a production instance of stoqs

1. Clone the repository in a location on your production server with an account that can run docker, e.g.:

```
sudo -u docker_user -i
cd /opt
git clone github.com/stoqs/stoqs.git stoqsgit
cd /opt/stoqsgit
export STOQS_HOME=$(pwd)
```

3. Acquire certificate files, name them expd.crt, and expd.key and place them in `${STOQS_HOME}/compose/production/nginx`

4. Start the app:

```
sudo -u docker_user -i
cd /opt/stoqsgit
export DOCKER_USER_ID=$(id -u)
export STOQS_HOME=$(pwd)
export COMPOSE_FILE=$STOQS_HOME/docker-compose.production.yml
docker compose up -d
docker compose run --rm django python manage.py migrate
```

5. Navigate to <https://stoqs..mbari.org> (for example) to see a production STOQS web application.

# Additional documentation provided by cookiecutter-django

# STOQS

Spatial Temporal Oceanographic Query System

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: GPLv3

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    mypy stoqs

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    coverage run -m pytest
    coverage html
    open htmlcov/index.html

#### Running tests with pytest

    pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [Mailpit](https://github.com/axllent/mailpit) with a web interface is available as docker container.

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
