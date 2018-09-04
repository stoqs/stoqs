# Docker Tidbits

These are miscellaneous bits of information that are useful for 
operating a Dockerized production STOQS installation.  They have been 
assembled over time as a way to document the sometimes arcane things
that need to be done.  These instructions assume that you are operating
in an environment that has been created following 
[these instructions](https://github.com/stoqs/stoqs#production-deployment-with-docker).

The STOQS_HOME environment variable is the location where the GitHub project was 
cloned if you are using STOQS that way, e.g. on MBARI servers:

STOQS_HOME=/opt/stoqsgit

## Miscellaneous PostgreSQL operations

Acquire an interactive psql prompt by executing up `psql` on the running postgis container. 
(Need to use docker-compose as docker-compose.yml provides all the required connection settings.)

```bash
docker-compose exec postgis psql -U stoqsadm
```

After the `stoqsadm=>` you can enter the commands below.  *Note: With this command you are operating as administrator
on all of the stoqs databases.  You have the capability to do great damage.  Use the privilege with great responsibility.*


### Manually managing schema evolution: adding a geometry column to the Activity table to an existing database:

This SQL text derive from output of `stoqs/manage.py sqlall stoqs`; replace `<database>` with your database name:

```sql
\c <database>
SELECT AddGeometryColumn('stoqs_activity', 'mappoint', 4326, 'POINT', 2);
CREATE INDEX "stoqs_activity_mappoint_id" ON "stoqs_activity" USING GIST ( "mappoint" GIST_GEOMETRY_OPS );
```


### Drop NOT NULL constraint on foreign key where we do not always have an Analysis Method:


```sql
ALTER TABLE stoqs_sampledparameter ALTER COLUMN analysismethod_id DROP NOT NULL;
```


### Examples of adding columns to accomodate a new schema:

Note: This is now better done with schema evolution (migrations) that are now available in Django. 

```sql
ALTER TABLE stoqs_parametergroup ADD COLUMN "description" varchar(128);
ALTER TABLE stoqs_measurement ADD COLUMN "nominallocation_id" integer REFERENCES "stoqs_nominallocation" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE stoqs_nominallocation ADD COLUMN "activity_id" integer REFERENCES "stoqs_activity" ("id") DEFERRABLE INITIALLY DEFERRED;
```


### Change database password:

```sql
ALTER ROLE stoqsadm login password 'newpassword';
```

Note: also update the `STOQSADM_PASSWORD` value in your docker/.env file.


### Add an 'everyone' Postgres user with read access to all databases

Highly recommended for supporting Jupyter Notebook use of data in your databases.
Note: The stoqs/loaders/load.py has the --grant_everyone_select that will do this for you.

```sql
CREATE ROLE everyone login password 'guest';
\c <database>
GRANT select on all tables in schema public to everyone;
```


## Miscellaneous Python-Django operations

To launch an interactive Python session to interact with data in STOQS database
we can run a new container using the settings from docker-compose:

```bash
cd $STOQS_HOME/docker
docker-compose run stoqs stoqs/manage.py shell_plus
```

Once the interactive `>>>`  REPL prompt appears enter you can enter the following Python snippets.

### A little script to update the start and end dates for a set of Campaigns on a server:

```python
from django.db.models import Max, Min
from django.db.utils import OperationalError

dbAliases = [   'stoqs_may2012', 'stoqs_october2010', 'stoqs_september2010', 'stoqs_september2010',
                'default', 'stoqs_june2011', 'stoqs_september2010', 'stoqs_april2011', 
                'stoqs_may2012', 'stoqs_april2011', 'stoqs_june2011']
for dbAlias in dbAliases:
    try:
        ip_qs = InstantPoint.objects.using(dbAlias).aggregate(Max('timevalue'), Min('timevalue'))
        Campaign.objects.using(dbAlias).update(startdate = ip_qs['timevalue__min'], enddate = ip_qs['timevalue__max'])
        print(f"Database {dbAlias} updated with new Campaign start and end times: {ip_qs['timevalue__min']}, {ip_qs['timevalue__max']}")
    except OperationalError as e:
        print(f'{e}')
```


### A little script to update the start and end dates for all the Activities of a Campaign

```python
from django.db.models import Max, Min
for a in acts:
    ip_qs = InstantPoint.objects.using('stoqs_cce2015_t').filter(activity=a).aggregate(Max('timevalue'), Min('timevalue'))
    if ip_qs['timevalue__min'] and ip_qs['timevalue__max']:
        a.startdate = ip_qs['timevalue__min']
        a.enddate = ip_qs['timevalue__max']
        a.save(using='stoqs_cce2015_t')
```


### Delete an Activity:

```python
acts = Activity.objects.using('stoqs_march2013_s').filter(name__contains='plm04')
for a in acts:
    a.delete(using='stoqs_march2013_s')
```

This will cause a cascade delete of all measurments and measured_parameters associated with the Activities in `acts`.


## Running Python code for data processing requiring an additional volume mount

To run code that may require access to institutional NFS volume mounts run a new container with the appropriate
user id and volume specified with the `-u` and `-v` options:

```bash
docker-compose run -u 1087 -v /mbari/LRAUV:/LRAUV stoqs /bin/bash
```

It is also recommended to perform database loads using `docker-compose run ...` rather than `docker-compose exec ...` 
as a restart of the stoqs container running the web app behind the nginx service will not interrupt their execution.

Notes:
    * A `docker-compose down` will stop these additional container executions

