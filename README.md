Spatial Temporal Oceanographic Query System
-------------------------------------------

[![Build Status](https://travis-ci.org/stoqs/stoqs.svg)](https://travis-ci.org/stoqs/stoqs/branches)
[![Coverage Status](https://coveralls.io/repos/stoqs/stoqs/badge.svg?branch=master&service=github)](https://coveralls.io/github/stoqs/stoqs?branch=master)
[![Requirements Status](https://requires.io/github/stoqs/stoqs/requirements.svg?branch=master)](https://requires.io/github/stoqs/stoqs/requirements/?branch=master)
[![Code Health](https://landscape.io/github/stoqs/stoqs/master/landscape.svg?style=flat)](https://landscape.io/github/stoqs/stoqs)
[![DOI](https://zenodo.org/badge/20654/stoqs/stoqs.svg)](https://zenodo.org/badge/latestdoi/20654/stoqs/stoqs)

STOQS is a geospatial database and web application designed to give oceanographers
efficient integrated access to *in situ* measurement and *ex situ* sample data.
See http://www.stoqs.org.

#### Getting started with a STOQS development system 

First, install [Vagrant](https://www.vagrantup.com/) and and [VirtualBox](https://www.virtualbox.org/)
&mdash; there are standard installers for Mac, Windows, and Linux. (You will also need 
[X Windows System](doc/instructions/XWINDOWS.md) sofware on your computer.) Then create an empty folder off your 
home directory such as `Vagrants/stoqsvm`, open a command prompt window, cd to that folder, and enter these 
commands:

```bash
curl "https://raw.githubusercontent.com/stoqs/stoqs/master/Vagrantfile" -o Vagrantfile
curl "https://raw.githubusercontent.com/stoqs/stoqs/master/provision.sh" -o provision.sh
vagrant plugin install vagrant-vbguest
vagrant up --provider virtualbox
```

The `vagrant up` command takes an hour or so to provision and setup a complete CentOS 7 
STOQS Virtual Machine that also includes MB-System, InstantReality, and all the Python data science 
tools bundled in packages such as Anaconda.  You will be prompted for your admin password
for configuring a shared folder from the VM.  All connections to this VM are 
performed from the the directory you installed it in; you must cd to it (e.g. `cd
~/Vagrants/stoqsvm`) before logging in with the `vagrant ssh -- -X` command.  After 
installation finishes log into your new VM and test it:

```bash
vagrant ssh -- -X   # Wait for [vagrant@localhost ~]$ prompt
cd /vagrant/dev/stoqsgit && source venv-stoqs/bin/activate
export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5438/stoqs
./test.sh CHANGEME load noextraload
```

In another terminal window start the development server (after a `cd ~/Vagrants/stoqsvm`):

```bash
vagrant ssh -- -X   # Wait for [vagrant@localhost ~]$ prompt
cd /vagrant/dev/stoqsgit && source venv-stoqs/bin/activate
export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5438/stoqs
stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
```

Visit your server's STOQS User Interface using your host computer's browser:

    http://localhost:8008

More instructions are in the doc/instructions directory &mdash; see [LOADING](doc/instructions/LOADING.md) 
for specifics on loading your own data. For example, you may create your own database of an archived MBARI campaign:

    cd stoqs
    ln -s mbari_campaigns.py campaigns.py
    loaders/load.py --db stoqs_cce2015

You are encouraged to contribute to the STOQS project! Please see [CONTRIBUTING](CONTRIBUTING.md)
for how to share your work.  Also, see example 
[Jupyter Notebooks](http://nbviewer.jupyter.org/github/stoqs/stoqs/blob/master/stoqs/contrib/notebooks)
that demonstrate specific analyses and visualizations that go beyond the capabilities of the STOQS User Interface.
Visit the [STOQS Wiki pages](https://github.com/stoqs/stoqs/wiki) for updates and links to presentations.
The [stoqs-discuss](https://groups.google.com/forum/#!forum/stoqs-discuss) list in Google Groups is also 
a good place to ask questions and engage in discussion with the STOQS user and developer communities.

Supported by the David and Lucile Packard Foundation, STOQS undergoes continual development
to help support the mission of the Monterey Bay Aquarium Research Institue.  If you have your
own server you will occasionally want to get new features with:

```bash
git pull
./setup.sh
```

#### Production Deployment with Docker

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
The `docker-compose build` and `docker-compose up` commands should each take about 15 minutes.
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
docker-compose build
docker-compose up -d
```

The above commands should also be done following a `git pull` in order to deploy updated
software on your server.

See https://docs.docker.com/compose/production/ for more information about running in production.

To load some existing MBARI campaign data edit your `.env` file to uncomment the line:

```
CAMPAIGNS_MODULE=stoqs/mbari_campaigns.py
```

and restart the stoqs service, then from the docker directory execute the load script for a campaign, e.g.:

```bash
docker-compose run stoqs stoqs/loaders/load.py --db stoqs_simz_aug2013
```

In another window monitor its output:

```bash
docker-compose run stoqs tail -f /srv/stoqs/loaders/MolecularEcology/loadSIMZ_aug2013.out
# Or (The stoqs code is bound as a volume in the container from the GitHub cloned location)
tail -f $STOQS_HOME/stoqs/loaders/MolecularEcology/loadSIMZ_aug2013.out
```


If you use STOQS for your research please cite this publication:

> McCann, M.; Schramm, R.; Cline, D.; Michisaki, R.; Harvey, J.; Ryan, J., "Using STOQS (The spatial 
> temporal oceanographic query system) to manage, visualize, and understand AUV, glider, and mooring data," 
> in *Autonomous Underwater Vehicles (AUV), 2014 IEEE/OES*, pp.1-10, 6-9 Oct. 2014
> doi: 10.1109/AUV.2014.7054414

![STOQS logo](stoqs/static/images/STOQS_logo_gray1_689.png)
