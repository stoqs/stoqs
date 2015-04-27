Spatial Temporal Oceanographic Query System
-------------------------------------------

[![Travis-CI Status](https://travis-ci.org/MBARIMike/stoqs.svg?branch=django17upgrade)](https://travis-ci.org/MBARIMike/stoqs)
[![Coverage Status](https://coveralls.io/repos/MBARIMike/stoqs/badge.svg?branch=django17upgrade)](https://coveralls.io/r/MBARIMike/stoqs?branch=django17upgrade)

STOQS is a geospatial database and web application designed for providing efficient 
acccess to *in situ* oceanographic data across any dimension.
See http://www.stoqs.org for more information.

Getting started with a STOQS development system with [Vagrant](https://www.vagrantup.com/)
and [VirtualBox](https://www.virtualbox.org):

    curl "https://raw.githubusercontent.com/MBARIMike/stoqs/django17upgrade/Vagrantfile" -o Vagrantfile
    curl "https://raw.githubusercontent.com/MBARIMike/stoqs/django17upgrade/provision.sh" -o provision.sh
    vagrant up --provider virtualbox

After your virtual machine has booted, log in, finish the Python setup, and test the installation:

    vagrant ssh 
    cd dev/stoqsgit
    source venv-stoqs/bin/activate
    ./setup.sh
    ./test.sh

Start the development server:

    export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY'
    export DATABASE_URL="postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs"
    stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.vagrant

Visit your own server's STOQS User interface:

    http://localhost:8000

More instructions are in the doc/instructions directory -- see LOADING for how to load your own data. 
Visit the [STOQS Wiki pages](https://github.com/stoqs/stoqs/wiki) for updates and links to presentations.
The [stoqs-discuss](https://groups.google.com/forum/#!forum/stoqs-discuss) list in Google Groups is also 
a good place to ask questions and engage in discussion with the STOQS user and developer communities.

