PRODUCTION
==========

Notes for installing STOQS on a production server

STOQS is configured to be installed on your own self-hosted web server or on a 
Platform as a Service (PaaS) provider, such as Heroku. It follows
[The Twelve-Factor App](http://12factor.net/) guidelines with deployment 
settings placed in environment variables.

### Hosting STOQS on your own Nginx web server:

1. On your server install nginx and configure to start (you may configure nginx
   by editing the /etc/nginx/conf.d/default.conf file):

        sudo yum install nginx
        sudo chkconfig nginx on
        sudo /sbin/service nginx start

2. Clone STOQS to a local writable directory on your server. A good practice
   is to not push any changes from a production server back to the repository,
   therefore our clone can be read-only without any ssh keys configured, e.g.:

        export STOQS_HOME=/opt/stoqsgit
        cd `dirname $STOQS_HOME`
        git clone https://github.com/stoqs/stoqs.git stoqsgit

3. Provision your server: 

    * Start with a system provisioned with a `Vagrant up --provider virtualbox` command
    * Install all the required software using provision.sh as a guide
    * Use a server that already has much of the required software installed
    * There are many other ways, including Docker, for setting up the required services

4. Create a virtualenv using the executable associated with Python 2.7, install 
   the production requirements, and test using a stoqsadm password of your choice:
   
        cd $STOQS_HOME 
        /usr/local/bin/virtualenv venv-stoqs
        source venv-stoqs/bin/activate
        ./setup.sh production
        export PATH=/usr/pgsql-9.4/bin:$PATH
        alias psql='psql -p 5433'   # For postgresql server running on port 5433
        ./test.sh <stoqsadm_pw>
   
5. Edit the file $STOQS_HOME/stoqs/stoqs_nginx.conf and change the server_name
   and location settings for your server.

6. Create a symlink to the above .conf file from the nginx config directory:

        sudo ln -s $STOQS_HOME/stoqs/stoqs_nginx.conf /etc/nginx/conf.d

7. Copy static files to the production web server location.  The STATIC_ROOT in
   settings.py must be writable by the user that executes this command:

        export STATIC_ROOT=/usr/share/nginx/html/stoqsfiles/static/
        stoqs/manage.py collectstatic

8. Create the STATIC_ROOT/media/sections and STATIC_ROOT/media/parameterparameter
   directories. (These are used by matplotlib for data visualization in the UI.)
   They need to be writable by the owner of the web application, e.g.:

        export MEDIA_ROOT=/usr/share/nginx/html/stoqsfiles/
        mkdir -p $STATIC_ROOT/media/sections/
        mkdir -p $STATIC_ROOT/media/parameterparameter/
        chmod 733 $STATIC_ROOT/media/sections/
        chmod 733 $STATIC_ROOT/media/parameterparameter/

9. Start the stoqs application (replacing <dbuser> <pw> <host> and <port> with
   your values, and with all your campaigns/databases separated by commas
   assigned to STOQS_CAMPAIGNS), e.g.:

        export STATIC_ROOT=/usr/share/nginx/html/stoqsfiles/static/
        export MEDIA_ROOT=/usr/share/nginx/html/stoqsfiles/media
        export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
        export STOQS_CAMPAIGNS="stoqs_beds_canyon_events_t,stoqs_may2015"
        cd $STOQS_HOME/stoqs
        uwsgi --socket :8001 --module wsgi:application

10. Test the STOQS user interface at:

        http://<server_name>/


