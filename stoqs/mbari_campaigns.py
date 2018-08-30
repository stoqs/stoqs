# File: mbari_campaigns.py
#
# Create a symbolic link named campaigns.py to tell the Django server 
# to serve these databases: ln -s mbari_campaigns.py campaigns.py.
# The stoqs/loaders/load.py script uses the load commands associated
# with each database to execute the load and record the provenance.
# Execute 'stoqs/loaders/load.py --help' for more information.

from collections import OrderedDict

# Keys are database (campaign) names, values are paths to load script 
# for each campaign starting at the stoqs/loaders directory.  The full 
# path of 'stoqs/loaders/' is prepended to the value and then executed.
campaigns = OrderedDict([
    ('stoqs_rovctd_mb',     'ROVCTD/loadMB_Dives.sh'),
    ('stoqs_rovctd_mw93',   'ROVCTD/loadAllTransectDives.sh'),
    ('stoqs_rovctd_mw97',   'ROVCTD/loadTransectDives_mw97.sh'),
    ('stoqs_oceansites_o',   'OceanSITES/load_moorings.py -o'),
    ('stoqs_rovctd_goc',    'ROVCTD/loadGoC_Dives.sh'),
    ('stoqs_september2010',  'CANON/loadCANON_september2010.py'),
    ('stoqs_october2010',    'CANON/loadCANON_october2010.py'),
    ('stoqs_dorado2009',     'MolecularEcology/load_dorado2009.py'),
    ('stoqs_dorado2011',     'MolecularEcology/load_dorado2011.py'),
    ('stoqs_april2011',      'CANON/loadCANON_april2011.py'),
    ('stoqs_june2011',       'CANON/loadCANON_june2011.py'),
    ('stoqs_september2011',  'CANON/loadCANON_september2011.py'),
    ('stoqs_february2012',   'MolecularEcology/loadGOC_february2012.py'),
    ('stoqs_may2012',        'CANON/loadCANON_may2012.py'),
    ('stoqs_september2012',  'CANON/loadCANON_september2012.py'),
    ('stoqs_ioos_gliders',   'IOOS/load_gliders.py'),
    ('stoqs_march2013',      'CANON/loadCANON_march2013.py'),
    ('stoqs_march2013_o',    'CANON/loadCANON_march2013.py -o'),
    ('stoqs_beds_canyon_events', 'BEDS/loadBEDS_CanyonEvents.py'),
    ('stoqs_simz_aug2013',       'MolecularEcology/loadSIMZ_aug2013.py'),
    ('stoqs_september2013',      'CANON/loadCANON_september2013.py'),
    ('stoqs_september2013_o',    'CANON/loadCANON_september2013.py -o'),
    ('stoqs_cn13id_oct2013',     'CANON/loadCN13ID_october2013.py'),
    ('stoqs_simz_oct2013',       'MolecularEcology/loadSIMZ_oct2013.py'),
    ('stoqs_simz_spring2014',    'MolecularEcology/loadSIMZ_spring2014.py'),
    ('stoqs_canon_april2014',    'CANON/loadCANON_april2014.py'),
    ('stoqs_simz_jul2014',       'MolecularEcology/loadSIMZ_jul2014.py'),
    ('stoqs_september2014',      'CANON/loadCANON_september2014.py'),
    ('stoqs_simz_oct2014',       'MolecularEcology/loadSIMZ_oct2014.py'),
    ('stoqs_canon_may2015',      'CANON/loadCANON_may2015.py'),
    ('stoqs_os2015',             'CANON/loadCANON_os2015.py'),
    ('stoqs_canon_september2015',   'CANON/loadCANON_september2015.py'),
    ('stoqs_os2016',             'CANON/loadCANON_os2016.py'),
    ('stoqs_cce2015',            'CCE/loadCCE_2015.py'),
    ('stoqs_michigan2016',       'LakeMichigan/load_2016.py'),
    ('stoqs_canon_september2016',   'CANON/loadCANON_september2016.py'),
    ('stoqs_os2017',             'CANON/loadCANON_os2017.py'),
    ('stoqs_canon_april2017',    'CANON/loadCANON_april2017.py'),      
    ('stoqs_ps2017',             'CANON/loadCANON_postSeason2017.py'),
    ('stoqs_canon_september2017',   'CANON/loadCANON_september2017.py'), 
    ('stoqs_os2018',             'CANON/loadCANON_os2018.py'), 
    ('stoqs_canon_may2018',      'CANON/loadCANON_may2018.py'),     
    ('stoqs_all_dorado',      'PlanktonProxies/load_all_dorado.py'),
    ('stoqs_canon_september2018',   'CANON/loadCANON_september2018.py'),     
])
