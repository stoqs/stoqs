Instructions for doing STOQS development
========================================

You should have your own development system available at your disposal. 
Follow the directions in [README.md](../../README.md) to build one using 
Vagrant and VirtualBox.

The GitHub web site (https://github.com/stoqs/stoqs) is the central place
to engage with other developers, raise issues, get updated code, and to
contribute any code changes. See [CONTRIBUTING.md](CONTRIBUTING.md) for
instructions on how to contribute.

With the major Django upgrade work done in 2015 the STOQS directory
follows the conventions put forth by the "Two Scoops of Django" books
and the [Django Cookiecutter](https://github.com/pydanny/cookiecutter-django)
project.  Depending on what you are working on here are the directories:

* Load scripts:   stoqs/loaders
* Analysis programs:  stoqs/contrib/analysis
* STOQS User Interface:   stoqs/utils and stoqs/stoqs

#### Testing

    At any time you should be able to execute the test.sh script in the project
    home directory to perform a set of unit and functional tests.  It is a good
    idea to run these tests before pushing anything up to your fork of the 
    repository. If any of the tests fail you can run that specific test using a
    dot notation for the test, e.g.:

        cd stoqs
        ./manage.py test stoqs.tests.unit_tests.SummaryDataTestCase.test_parameterparameterplot2 --settings=config.settings.ci

    (Make sure that you are not running your development server when you execute 
    the test.sh script as it starts and then kills a development server for the 
    functional tests.)

    If you send a pull request then automated testing is performed by Travis-CI
    ensuring that the tested code does not break.  If you are adding a new feature
    it is imperative that the code coverage does not decrease, therefore you *must*
    write tests for any new feature that you add.

#### Development

    Enter your virtualenv, set environment variable(s), and launch your development
    server in a shell window:
  
        cd ~/dev/stoqsgit && source venv-stoqs/bin/activate
        export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs 
        stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local

    (Note: make sure to stop the development server before running test.sh.)

    Second, save a change to code in the view package.  The change is immediately compiled
    and deployed by the running Django development server.  There is no need to restart anything.


   
#### Old instrctions...

    Note: The user that executes manage.py must have privileges to create and drop database
    for Django to run the tests.  You may need to do this at psql for your shell account
    and the stoqsdm account:

        CREATE ROLE <user_name> LOGIN PASSWORD 'password_of_your_choice';
        ALTER ROLE <user_name> CREATEDB NOSUPERUSER NOCREATEROLE;

    You must also be able to create a new database using the postgis template that was installed
    with yum.  Postgres needs to be told that it is a template for other's than the owner to 
    copy it.  Update to make it a template with this psql command:

        UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'template_postgis';

    Other database roles need to have permission to see the relations (tables) in template_postgis,
    so you need to do this too; for sure, run these commands as well with stoqsadm for <user_name>:

        \c template_postgis
        GRANT ALL ON TABLE geometry_columns TO <user_name>
        GRANT ALL ON TABLE spatial_ref_sys TO <user_name>
    
    If they all pass you are good.  If you get a failure, fix it and then repeat the test.
    Iterate on these last two steps.  You may also test the links from the activities and
    mgmt views.  If there is missing coverage for a needed test please add it to stoqs/tests.
   
   
3. Additional notes:
    
    - Need to use Django 2.4.1 because of existing conflict between psycopg and Django
    - For tests to work you must apply patch at:
        https://code.djangoproject.com/ticket/16778 to adapter.py which is applied to file:
        venv-stoqs/lib/python2.6/site-packages/Django-1.3-py2.6.egg/django/contrib/gis/db/backends/postgis/adapter.py
  
    - The data from the database loaded by the DAPloaders test may be dumped into a JSON file 
      which is used as a fixture for the unit tests.  This normally needs to be done after 
      and schema changes:

        python manage.py dumpdata --database=default stoqs > stoqs/fixtures/stoqs_test_data.json
        
    - There is no unit test for the code in loaders.  The loaders code manually selects the database
      using Django's 'using=<dbalias>' technique.  Django's test runner uses the automated database 
      routing framework as implemented in stoqs/db_router.py and the <dbName> pattern in urls.py.

    - Model changes (adding new relations, etc.) may require starting over with creating and syncing
      a database then loading some data, creating a new fixture, and testing.

    - If new python modules are added with pip update the requirements.txt file with:

        pip freeze > requirements.txt

      and commit the requiremetns.txt file to the repository.
    
    - Additional information is in the file DEBUG_OPTIMIZE      

