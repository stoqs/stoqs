Serving STOQS with nginx and uWSGI
==================================

STOQS is configured to be installed on your own self-hosted web server or on a 
Platform as a Service (PaaS) provider, such as Heroku.  It follows
[The Twelve-Factor App](http://12factor.net/) guidelines with deployment 
settings placed in environment variables.  Unless otherwise noted all commands
should be executed from a regular user account that you will use to manage
the stoqs application, e.g. an account something like USER='stoqsadm'.

### Steps for hosting on your own server

1. On your server install nginx and configure to start (configure nginx
   by editing the /etc/nginx/conf.d/default.conf file after you install it):

        sudo yum -y install nginx
        sudo chkconfig nginx on
        sudo /sbin/service nginx start

2. Clone STOQS to a local writable directory on your server. A good practice
   is to not push any changes from a production server back to the repository,
   therefore our clone can be read-only without any ssh keys configured, e.g.:

        export STOQS_HOME=/opt/stoqsgit
        cd `dirname $STOQS_HOME`
        git clone https://github.com/stoqs/stoqs.git stoqsgit

3. Provision your server, there are many options: 

    * Start with a system provisioned with a `Vagrant up --provider virtualbox` command
    * Install all the required software using [provision.sh](../../provision.sh) as a guide
    * Use a server that already has much of the required software installed
    * Other ways, including Docker, that are up-and-coming in the DevOps world

4. Create a virtualenv using the executable associated with Python 2.7, install 
   the production requirements, and setup the environment:
   
        cd $STOQS_HOME 
        /usr/local/bin/virtualenv venv-stoqs
        source venv-stoqs/bin/activate
        ./setup.sh production
        export PATH=/usr/pgsql-9.4/bin:$PATH
        alias psql='psql -p 5433'   # For postgresql server running on port 5433

5. As privileged 'postgres' user create default stoqs database (skip this step on
   a system built with `Vagrant up --provider virtualbox` where the `./test.sh`
   has been run, as test.sh creates the default database):

        /bin/su postgres
        export PATH=/usr/pgsql-9.4/bin:$PATH
        alias psql='psql -p 5433'   # For postgresql server running on port 5433
        psql -c "CREATE DATABASE stoqs owner=stoqsadm template=template_postgis;"
        psql -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';"

6. As regular 'stoqsadm' user initialize and load the default stoqs database (again,
   skip this step on a STOQS Vagrantfile provisioned system):

        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        stoqs/manage.py makemigrations stoqs --settings=config.settings.local --noinput
        stoqs/manage.py migrate --settings=config.settings.local --noinput --database=default
        wget -q -N -O stoqs/loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
        stoqs/loaders/loadTestData.py

7. Copy the file `$STOQS_HOME/stoqs/stoqs_nginx.conf` to a file that will be
   specific for your system and edit it to and change the server_name
   and location settings for your server.  There are absolute directory paths in 
   this file; make sure they refer to paths on your servers.  Then create a
   symlink of it to the nginx config directory, e.g.:

        cp $STOQS_HOME/stoqs/stoqs_nginx.conf $STOQS_HOME/stoqs/stoqs_nginx_<host>.conf
        vi $STOQS_HOME/stoqs/stoqs_nginx_<host>.conf
        sudo ln -s $STOQS_HOME/stoqs/stoqs_nginx_<host>.conf /etc/nginx/conf.d

8. Copy the `stoqs/stoqs_uwsgi.ini` file to one specific for your host and edit
   so the the value of $STOQS_HOME is explicit:

        cp $STOQS_HOME/stoqs/stoqs_uwsgi.ini $STOQS_HOME/stoqs/stoqs_uwsgi_$HOST.ini
        vi $STOQS_HOME/stoqs/stoqs_uwsgi_$HOST.ini    # Edit to make sure paths are correct

9. Create the media and static web directories and copy the static files to the 
   production web server location. The $STATIC_ROOT directory must be writable 
   by the user that executes the `collectstatic` command:

        sudo mkdir /usr/share/nginx/html/media
        sudo mkdir /usr/share/nginx/html/static
        sudo chown $USER /usr/share/nginx/html/static
        export STATIC_ROOT=/usr/share/nginx/html/static
        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        stoqs/manage.py collectstatic

10. Create the `$MEDIA_ROOT/sections` and `$MEDIA_ROOT/parameterparameter`
    directories and set permissions for writing by the web process. 

        export MEDIA_ROOT=/usr/share/nginx/html/media
        sudo mkdir $MEDIA_ROOT/sections
        sudo mkdir $MEDIA_ROOT/parameterparameter
        sudo chown -R $USER /usr/share/nginx/html/media
        sudo chmod 733 $MEDIA_ROOT/sections
        sudo chmod 733 $MEDIA_ROOT/parameterparameter


11. Create a bash script to start the stoqs uWSGI application, replacing 
    `<dbuser>, <pw>, <host>, <port>, <mapserver_ip_address>`, and other values 
    that are specific to your server, e.g.:

        vi $STOQS_HOME/start_uwsgi.sh
        # Start the stoqs uWSGI application for nginx
        export STOQS_HOME=/opt/stoqsgit
        export STATIC_ROOT=/usr/share/nginx/html/static
        export MEDIA_ROOT=/usr/share/nginx/html/media
        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        export MAPSERVER_HOST="<mapserver_ip_address>"
        export STOQS_CAMPAIGNS="<comma_separated>,<databases>,<not_in_campaigns>"
        export SECRET_KEY="<random_sequence_of_impossible_to_guess_characters>"
        export GDAL_DATA=/usr/share/gdal
        # Execute uwsgi for command-line testing
        uwsgi --ini stoqs/stoqs_uwsgi_$HOST.ini
        # Execute uwsgi in daemon mode for use in production
        ##uwsgi --emperor /etc/uwsgi/vassals --uid www-data --gid www-data --daemonize /var/log/uwsgi/uwsgi-emperor.log --pidfile /var/run/uwsgi.pid

12. Execute the `$STOQS_HOME/start_uwsgi.sh` script and confirm that the
    web application works the same way as it does when the development 
    server is running:

        $STOQS_HOME/start_uwsgi.sh
        http://<server_name>:<port>/

13. Configure your server to run uWSGI in emperor mode (see: http://bit.ly/1KQH5Sv
    for complete instructions) and test:

        deactivate
        sudo pip3.6 install uwsgi
        sudo mkdir -p /etc/uwsgi/vassals
        sudo ln -s $STOQS_HOME/stoqs/stoqs_uwsgi_$HOST.ini /etc/uwsgi/vassals
        # Set env variables that are set in start_uwsgi.sh and test at command line
        /usr/local/bin/uwsgi --emperor /etc/uwsgi/vassals --uid www-data --gid www-data

14. To configure uWSGI to start on system boot comment out the first uwsgi 
    line in file $STOQS_HOME/start_uwsgi.sh and uncomment the daemon mode 
    version of uwsgi.
   
    As this script contains keys and database credentials take appropriate steps to 
    protect it from prying eyes. On a CentOS 7 system you may copy an edited version of
    [sample_uwsgi.service](sample_uwsgi.service) /etc/systemd/system/ to create
    a unit for systemctl.  Then enable and start it:

        cp doc/instructions/sample_uwsgi.service $STOQS_HOME/stoqs/uwsgi.service
        vi $STOQS_HOME/stoqs/uwsgi.service    # Edit to execute start_uwsgi_$HOST.sh
        sudo cp $STOQS_HOME/stoqs/uwsgi.service /etc/systemd/system
        sudo systemctl enable uwsgi
        sudo systemctl start uwsgi

15. To restart a production uWSGI server running in emperor mode simply `touch`
    the file that is linked in the `/etc/uwsgi/vassals/` directory, e.g.:

        touch $STOQS_HOME/stoqs/stoqs_uwsgi_$HOST.ini

    A restart is needed to use updated software or configurations, for example
    following a `git pull` command.

    It is a good idea to monitor the log file whenever restarting a service:

        tail -f /var/log/uwsgi/uwsgi-emperor.log

16. These steps will generate serveral customized files in $STOQS_HOME.  They should
    not be checked into version control.  If you are comfortable with seeing them
    listed in a `git status` command and have the discipline to not add and commit
    them then leave them be; otherwise, you may want to add them to .gitignore, e.g.:

        # Special for kraken2 installation - do not commit this change!
        start_uwsgi.sh
        stoqs/stoqs/media/loadlogs/
        stoqs/stoqs_nginx_kraken2.conf
        stoqs/stoqs_uwsgi_kraken2.ini

