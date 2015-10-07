Spatial Temporal Oceanographic Query System
-------------------------------------------

[![Build Status](https://travis-ci.org/stoqs/stoqs.svg)](https://travis-ci.org/stoqs/stoqs)
[![Coverage Status](https://coveralls.io/repos/stoqs/stoqs/badge.svg?branch=master&service=github)](https://coveralls.io/github/stoqs/stoqs?branch=master)
[![Requirements Status](https://requires.io/github/stoqs/stoqs/requirements.svg?branch=master)](https://requires.io/github/stoqs/stoqs/requirements/?branch=master)

STOQS is a geospatial database and web application designed to give oceanographers
efficient acccess to *in situ* measurement and *ex situ* sample data.
See http://www.stoqs.org for more information.

Getting started with a STOQS development system with [Vagrant](https://www.vagrantup.com/)
and [VirtualBox](doc/instructions/VirtualBox.md):

    curl "https://raw.githubusercontent.com/stoqs/stoqs/master/Vagrantfile" -o Vagrantfile
    curl "https://raw.githubusercontent.com/stoqs/stoqs/master/provision.sh" -o provision.sh
    vagrant up --provider virtualbox

The `vagrant up` command takes a few hours to provision and setup a complete CentOS 7 
STOQS server.  When it is done log in and test the installation:

    vagrant ssh -- -X
    cd ~/dev/stoqsgit && source venv-stoqs/bin/activate
    export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs
    ./test.sh CHANGEME

In another terminal window start the development server:

    vagrant ssh -- -X
    cd ~/dev/stoqsgit && source venv-stoqs/bin/activate
    export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs
    stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local

Visit your server's STOQS User Interface using your host computer's browser:

    http://localhost:8000

More instructions are in the doc/instructions directory -- see [LOADING](doc/instructions/LOADING.md) 
for how to load your own data and [CONTRIBUTING](doc/instructions/CONTRIBUTING.md) for how to share your work.
Also, see interesting [Jupyter Notebooks](stoqs/contrib/notebooks) that you can execute against your own STOQS server.
Visit the [STOQS Wiki pages](https://github.com/stoqs/stoqs/wiki) for updates and links to presentations.
The [stoqs-discuss](https://groups.google.com/forum/#!forum/stoqs-discuss) list in Google Groups is also 
a good place to ask questions and engage in discussion with the STOQS user and developer communities.

