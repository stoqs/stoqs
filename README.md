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
NetCDF and Geographic Information Systems technologies.

Here's a short video giving the context in which STOQS is used:

<a href='http://www.youtube.com/watch?feature=player_embedded&v=E8wO3qMevV8' target='_blank'><img src='http://img.youtube.com/vi/E8wO3qMevV8/0.jpg' width='425' height=344 /></a>

After installation, data is loaded into STOQS from a variety of data sources, including 
OPeNDAP data sets, other relational databases, and flat files. Products are delivered 
within the STOQS User Interface and in a variety of formats, including KML, via REST-style web requests.

Installing
----------
To install the software for your own use fork the project on GitHub, clone it to your Linux system (CentOS is preferred), e.g.:

    git clone git@github.com:<your_github_id>/stoqs.git stoqsgit
    
and follow the instructions starting with the PREREQUISITES file.

Operation
---------
If you wish to load data into an already installed STOQS server you can start with
reading  the LOADING file for the instructions for creating a database, setting data
sources, and writing a loader script.


Further information is in these files:

    PREREQUISITES - System level requirements, e.g. Postgis, Django, Python modules
    INSTALL       - Steps to install the Django stoqs application
    DEVELOPMENT   - Instructions on running a development environment
    PRODUCTION    - Instructions on setting up a production environment
    LOADING       - Loading your data
    TIDBITS       - Miscellaneous tips, fixes, and examples for using STOQS
    LICENSE       - GNU General Public License text, how this software is licensed

The stoqs project web site has a wiki with links to presentations and periodic feature
updates.  The [stoqs-discuss](https://groups.google.com/forum/#!forum/stoqs-discuss) list in Google Groups is also a good place to post questions
or any sort of comments about STOQS.    



