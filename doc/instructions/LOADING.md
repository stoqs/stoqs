Instructions for loading your data in STOQS
===========================================

### TL;DR; (Quick instructions for your Vagrant VM)

Use the `stoqs/loaders/load.py` script to create a database and load data for an existing campaign. First
use it to list existing campaigns (after creating a `campaigns.py` symbolic link in
the stoqs directory pointing to `mbari_campaigns.py`):

    export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs
    cd stoqs
    ln -s mbari_campaigns.py campaigns.py
    loaders/load.py --list

Pick a campaign of interest and load it, e.g.:

    loaders/load.py --db stoqs_september2010

Use the --help option for a suggested workflow to build up a production server.


### Details
 
These instructions cover the loading of *in situ* discrete sampling geometry feature type 
data from OPeNDAP accessible data sources.  Data adhereing to the Climate and Forecast
conventions version 1.6 are supported for loading into STOQS.  Specific feature types
supported are: trajectory, timeSeries, timeSeriesProfile, and trajectoryProfile.  
For more information please see http://cfconventions.org/
and http://www.nodc.noaa.gov/data/formats/netcdf/.

There are many ways to write data adhering to these standards - there are some examples
using Python in the stoqs/loaders/CANON/toNetCDF directory.

Here are the step-by-step instuctions for getting your data into STOQS given the above
prerequisites:

1. Add a new file to the stoqs/loaders directory named to describe the campaign that is 
   the source of the data.  The campaign name may be a project name or a month_year
   combination.  It can really be anything you want.  At MBARI for the CANON initiative
   we typically have field programs where intensive measurements are collected in
   an area of the ocean over a several week period, so we name our campaigns like
   like 'stoqs_september2010' and 'stoqs_june2011'.
   The point of using separate databases for campaigns is to constrain the size
   of the databases, which helps in managing them and in evolving stoqs applications
   while maintaining some level of consistent functionality of access for databases
   that are not under development.
   
2. In your new loadXXXX.py file instantiate a Loader object with the database alias name
   and a name for the Campaign.  Member names for the loader are defined in the class that
   is imported.  For example, look in the `stoqs/loaders/CANON/__init__.py` file for what platforms
   are supported for the CANONLoader.  There are several examples of other load files in
   the stoqs/loaders/ directory.  You may use them as a basis for the data you wish to load.

3. The CANON directory in stoqs/loaders/ contains load scripts for all of the MBARI CANON
   campaigns.  Much of the commonly used loader code has been factored out into a 
   CANONLoader class in `stoqs/loaders/CANON/__init__.py` so that the load scripts (e.g. 
   loadCANON_september2012.py) simply need to be constructed with the OPeNDAP URLs
   and parameter names for each type of platform.
   
4. (Note: Steps 4-7 are performed by the `loaders/load.py` script. You may find it easier to 
   use it to create and load your database.) Create a PostgreSQL database for your campaign, 
   in this example a test database (with '_t' suffix) is created, using psql as user with proper 
   privileges:

         create database stoqs_september2012_t owner=stoqsadm template=template_postgis;
         alter database stoqs_september2012_t set timezone='GMT';
         \c stoqs_september2012_t
         grant all on all tables in schema public to stoqsadm;

5. Assign DATABASE_URL (replacing <dbuser> <pw> <host> and <port> with your 
   values) and add your new database/campaign to STOQS_CAMPAIGNS (databases
   not in campaigns.py need to be added to this environment variable) , e.g.:

        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        export STOQS_CAMPAIGNS="stoqs_september2012_t,$STOQS_CAMPAIGNS"

6. Synchronize (migrate) the new database with the stoqs data model.  At a shell prompt 
   in your virtual environment:

        source venv-stoqs/bin/activate
        stoqs/manage.py makemigrations stoqs --settings=config.settings.local --noinput
        stoqs/manage.py migrate --settings=config.settings.local --noinput --database=stoqs_september2012_t

7. Make sure that your session does not have the PYTHONPATH environment set; you may need to do:

         unset PYTHONPATH

   Then, execute your load script on the test database:

         stoqs/loaders/CANON/loadCANON_september2012.py -t

   To populate a full-resolution database repeat steps 4-7 with database name without the 
   '_t' suffix (stoqs_september2012) and execute:

         stoqs/loaders/CANON/loadCANON_september2012.py 

8. Restart your server to force a re-read of the settings file and the modified 
   STOQS_CAMPAIGNS environment variable.  On a development server simply restart 
   `cd stoqs && ./manage.py runserver 0.0.0.0:8000 --settings=config.settings.local`
   which you normally have running in its own shell window (see 
   [DEVELOPMENT.md](DEVELOPMENT.md)).  On a production server running nginx with 
   uWSGI in Emperor mode simply touch the wsgi .ini file, e.g.:

        touch stoqs/stoqs_uwsgi.ini

9. Notes:

    - As a campaign produces data files additional URLs will need to be added to the script.  To add
      data to an existing database simply comment out previously loaded files and re-execute
      the script (step 7) with the new files.
    - Some programs to create NetCDF files from various original data files (e.g. Seabird underway 
      and profile CTD) are in the stoqs/loaders/CANON/toNetCDF directory.  See the README
      there for instructions on running those scripts to put the data on an OPeNDAP server
      so that your STOQS loader can load them.
    - Editing and running the load script during a campaign is an interactive process requiring
      interaction with people and testing the data sources for valid parameter names as well
      as monitoring the output for warning and error messages.
    - *Ex situ* subsample data are loaded from .csv files local to the loading computer.  If
      you get error messages that those files are not found you will need to copy them to
      your computer.  (There is Issue #145 which suggests establishing a mechanism for 
      loading these data via the web.)
    - To provide read-only access to your database create an 'everyone' role and grant everyone
      select privileges on specific databases:

            CREATE ROLE everyone login password 'guest';
            \c stoqs_september2012_t
            grant select on all tables in schema public to everyone;

      You may also use the --grant_everyone_select option of the load.py script to grant this
      permission to all of your databases.

    - You can use the stoqs/loaders/load.py script automate the creation and migration 
      of databases on the Postgresql server.  You will need to configure a stoqs/campaigns.py 
      file; see stoqs/mbari_campaigns.py for an example.  Execute `stoqs/loaders/load.py --help`
      for more information.

    - The stoqs-discuss mail list (https://groups.google.com/forum/?fromgroups=#!forum/stoqs-discuss)
      is a good place to ask questions if you have any.

