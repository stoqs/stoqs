README
======

Spatial Temporal Oceanographic Query System (STOQS)
---------------------------------------------------

STOQS is a geospatial database web application designed for providing efficient 
acccess to *in situ* oceanographic data across any dimension - e.g., retrieving
a common parameter from all measuring platforms in a specific area over a 
specific span of time.  STOQS complements other data management technologies
such as NetCDF and OPeNDAP by providing an ability to index data retrieval 
across parameter and spatial dimensions in addition to the *a priori* indexed
coordinate dimensions in NetCDF.  It also provides a functional bridge between 
NetCDF and Geographic Information Systems technologies. See http://www.stoqs.org
for videos and general information.

Getting started with a STOQS development system:

    wget https://raw.githubusercontent.com/MBARIMike/stoqs/django17upgrade/Vagrantfile
    vagrant up

After your virtual machine has booted log in, finish the Python setup, and load some test data:

    vagrant ssh --provider virtualbox
    cd dev/stoqsgit
    source venv-stoqs/bin/activate
    ./setup.sh
    ./test.sh

Visit your own server's STOQS User interface:

    http://localhost:8000



The stoqs project web site has a wiki with links to presentations and periodic feature
updates.  The [stoqs-discuss](https://groups.google.com/forum/#!forum/stoqs-discuss) list in Google Groups is also a good place to post questions
or any sort of comments about STOQS.    



