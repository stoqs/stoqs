# Dockerized STOQS

First, install [Docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/install/)
on your system.  Then clone the repository; in the docker directory copy the `template.env` file to `.env` 
and edit it for your specific installation, then execute `docker-compose up`:

```bash
git clone https://github.com/stoqs/stoqs.git stoqsgit
cd stoqsgit/docker
cp template.env .env
chmod 600 .env      # Edit .env to customize (Ensure that STOQS_HOME is set to the full path of stoqsgit)
docker-compose build
docker-compose up
```

#### Developer Installation with Docker

TODO: Offer instructions that are an alternative to running a STOQS development system in Vagrant


#### Production Deployment with Docker

The `docker-compose build` and `docker-compose up` commands should each take less than 15 minutes.
The first time the latter is executed a default database is created and tests are executed.
Once you see `... [emperor] vassal /etc/uwsgi/django-uwsgi.ini is ready to accept requests`
you can visit the site at https://localhost &mdash; it uses a self-signed certificate, so your
browser will complain. (The nginx service also delivers the same app at http://localhost:8000
without the cerificate issue.)

The default settings in `template.env` will run a production nginx/uwsgi/stoqs server configured
for https://localhost.  To configure a server for intranet or public serving of
your data follow the instructions provided in the comments for the settings in your `.env` file.
After editing your `.env` file you will need to rebuild your stoqs image and restart the Docker 
services, this time with the `-d` option to run the containers in the background:

```bash
docker-compose build stoqs
docker-compose up -d
```

See https://docs.docker.com/compose/production/ for more information about running in production.

To load some existing MBARI campaign data edit your `.env` file to uncomment the line:

```
CAMPAIGNS_MODULE=stoqs/mbari_campaigns.py
```

and restart the stoqs service, then from the docker directory execute the load script for a campaign:

```bash
docker-compose exec stoqs stoqs/loaders/load.py --db stoqs_simz_aug2013
```

In another window monitor its output:

```bash
docker-compose exec stoqs tail -f /srv/stoqs/loaders/MolecularEcology/loadSIMZ_aug2013.out
# Or (The stoqs code is bound as a volume in the container from the GitHub cloned location)
tail -f $STOQS_HOME/stoqs/loaders/MolecularEcology/loadSIMZ_aug2013.out
```

