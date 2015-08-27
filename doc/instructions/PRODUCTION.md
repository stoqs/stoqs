PRODUCTION
==========

Notes for installing STOQS on a production server

STOQS is configured to be installed on your own self-hosted web server or on a 
Platform as a Service (PaaS) provider, such as Heroku. It follows
[The Twelve-Factor App](http://12factor.net/) guidelines with deployment 
settings placed in environment variables.

### Here are the suggested steps for hosting STOQS using your own Nginx web server:

1. On your server install nginx and configure to start:

    sudo yum install nginx
    sudo chkconfig nginx on
    sudo /sbin/service nginx start

2. Clone STOQS to a local writable directory on your server. A good practice
   is to not commit any changes from a production server back to the repository,
   therefore our clone can be read only without any ssh keys configured, e.g.:

    export STOQS_HOME=/opt/stoqsgit
    cd ``dirname $STOQS_HOME``
    git clone https://github.com/stoqs/stoqs.git stoqsgit

3. Provision your server: 
    * Start with a system provisioned with a `Vagrant up` command
    * Install all the required software using provision.sh as a guide

4. Create a virtualenv, install the production requirements, and test:
   
    cd $STOQS_HOME 
    virtualenv venv-stoqs
    source venv-stoqs/bin/activate
    ./setup.sh production
    ./test.sh
   
5. Edit the file $STOQS_HOME/stoqs/stoqs_nginx.conf and change the server_name
   and location settings for your server.

6. Create a symlink to the above .conf file from the nginx config directory:

    sudo ln -s $STOQS_HOME/stoqs/stoqs_nginx.conf /etc/nginx/conf.d

7. Copy static files to the production web server location off of it's document_root.
   The STATIC_ROOT in settings.py must be writable by the user that executes this command:

    stoqs/manage.py collectstatic


 
1. Add a stoqs.conf file to the server's /etc/httpd/conf.d/ directory.  With this 
   configuration the system administrator can assign sudo privileges to administrator
   of the STOQS application, and he/she can make changes without affecting the master
   httpd.conf.
   
   
2. Add the following lines to the stoqs.conf file in /etc/httpd/conf.d/ and make sure
   that the directory where stoqs.wsgi is located is readable by the wed server.

# stoqs.conf - connector between apache/wsgi and the stoqs project

# Replace STOQS_PROJ_DIR below with the location where the STOQS project has been 
# checked out, something like "/opt/stoqshg"

WSGISocketPrefix /var/run/wsgi

WSGIDaemonProcess stoqs user=apache group=root threads=25
WSGIProcessGroup stoqs

<Directory STOQS_PROJ_DIR>
    WSGIApplicationGroup %{GLOBAL}
    Order deny,allow
    Allow from all
</Directory>

# Map web server path to location of the stoqs.wsgi file:
# WSGIScriptAlias /<parent_web_site> <path_to_stoqs.wsgi_file>, e.g.:
WSGIScriptAlias /canon STOQS_PROJ_DIR/stoqs.wsgi


NOTE: Multiple WSGIScriptAliass may be configured for different projects served from the
      same web server.  Simply clone the repository to another directory, set up the
      virtual environment and execute setup.sh as described in the end of PREREQUISITES.

3. Edit privateSettings if the DATABASE_* settings are different.  (Your Postgres
   server will most likely may have tighter access controls in a production environment.)
   
   Make sure that you have DEBUG set to False
   
4. Copy static files to the production web server location off of it's document_root.
   The STATIC_ROOT in settings.py must be writable by the user that executes this command:

    python manage.py collectstatic


5. Create the STATIC_ROOT/media/sections and STATIC_ROOT/media/parameterparameter directories. 
   (These are used by matplotlib for data visualization for the UI.)  They need to be
   writable by the owner of the httpd process.  This can be done on a typical CentOS 
   install with these commands:

    mkdir -p /var/www/html/stoqs/media/sections/
    mkdir -p /var/www/html/stoqs/media/parameterparameter/
    chmod 733 /var/www/html/stoqs/media/sections/
    chmod 733 /var/www/html/stoqs/media/parameterparameter/


6. Restart the apache web server:

    sudo /sbin/service httpd restart


7. Test the STOQS user interface at URL:

    http://<your_server_name>/canon/


8. You may need to add the follwing lines to the startup script for apache httpd, typically file 
   /etc/init.d/http:

    export LD_LIBRARY_PATH='/usr/local/lib/'
    export GDAL_DATA='/usr/share/gdal/'
  
   You'll know if you'll need to add this if you get a message saying the gdal library can't be found.
   Check for error messages in /var/log/httpd/error_log and of course on the web pages from the stoqs ui.


TODO: Instructions for setting up celery to run as a daemon. (Note: celery is used for managing 
      long running processes, as of 25 February 2013 stoqs has no such processes.  This is a
      placeholder should stoqs develop long running processes in the future.)


--
Mike McCann
MBARI 25 February 2013
