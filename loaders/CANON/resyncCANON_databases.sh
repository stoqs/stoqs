# Run this script after crecreating all the databases with recreateCANON_databases.psql
# After running this script reload all of the data with loadCANON_all.sh
# This script must be run from the Django projecct home directory, where manage.py lives

#python manage.py syncdb --noinput --database=stoqs 
python manage.py syncdb --noinput --database=stoqs_september2010
python manage.py syncdb --noinput --database=stoqs_october2010
python manage.py syncdb --noinput --database=stoqs_april2011
python manage.py syncdb --noinput --database=stoqs_june2011
python manage.py syncdb --noinput --database=stoqs_may2012
##python manage.py syncdb --noinput --database=stoqs_september2012
