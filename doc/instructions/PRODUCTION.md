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

8. Edit the `$STOQS_HOME/stoqs/stoqs_uwsgi.ini` file making sure that all the 
   absolute directory paths are correct.

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


11. Start the stoqs uWSGI application, replacing `<dbuser>, <pw>, <host>, <port>, 
    <mapserver_ip_address>`, and other values that are specific to your 
    server, e.g.:

        export STOQS_HOME=/opt/stoqsgit
        export STATIC_ROOT=/usr/share/nginx/html/static
        export MEDIA_ROOT=/usr/share/nginx/html/media
        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        export MAPSERVER_HOST="<mapserver_ip_address>"
        export STOQS_CAMPAIGNS="<comma_separated>,<databases>,<not_in_campaigns>"
        export SECRET_KEY="<random_sequence_of_impossible_to_guess_characters>"
        export GDAL_DATA=/usr/share/gdal
        uwsgi --ini stoqs/stoqs_uwsgi.ini

12. Test the STOQS user interface using the configuration of your nginx server:

        http://<server_name>:<port>/

13. Configure your server to run uWSGI in emperor mode (see: http://bit.ly/1KQH5Sv
    for complete instructions) and test:

        deactivate
        sudo /usr/local/bin/pip install uwsgi
        sudo mkdir -p /etc/uwsgi/vassals
        sudo ln -s $STOQS_HOME/stoqs/stoqs_uwsgi.ini /etc/uwsgi/vassals
        /usr/local/bin/uwsgi --emperor /etc/uwsgi/vassals --uid www-data --gid www-data

14. To configure uWSGI to start on system boot put the commands from step 11 into 
    a script file named something like `start_uwsgi.sh` and put the full path of the file
    `in /etc/rc.d/rc.local`.  To have it run in emperor mode replace the last line 
    in the script with the last line from step 13.  As this script contains keys 
    and database credentials take appropriate steps to protect it from prying eyes.

15. To restart a production uWSGI server running in emperor mode simply `touch`
    the file that is linked in the `/etc/uwsgi/vassals/` directory, e.g.:

        touch $STOQS_HOME/stoqs/stoqs_uwsgi.ini

    A restart is needed to use updated software or configurations, for example
    following a `git pull` command.

