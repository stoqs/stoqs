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
    ('stoqs_rovctd_mw97',   ('ROVCTD/ROVCTDloader.py --database stoqs_rovctd_mw97 '
                            '--dives V1236 V1247 V1321 V1575 V1610 V1668 T257 V1964 '
                            'V2069 V2329 V2354 V2421 V2636 V2661 V2715 V2983 V3006 '
                            'V3079 V3334 V3363 V3417 V3607 V3630 V3646 D449 D478 '
                            'V3736 V3766 V3767 V3774 D646 '
                            '--bbox -122.1 36.65 -122.0 36.75 '
                            '--campaignName "Midwater Transect dives 1997 - 2014" '
                            '--campaignDescription "Midwater Transect dives made with '
                            'Ventana and Doc Ricketts from 1997 - 2014. Three to four '
                            'dives/year selected, representing spring, summer and fall '
                            '(~ beginning upwelling, upwelling and post-upwelling)"')),
    ('stoqs_oceansites_o',   'OceanSITES/load_moorings.py -o'),
    ('stoqs_rovctd_goc',    'ROVCTD/loadGoC_Dives.sh'),
    ('stoqs_september2010',  'CANON/loadCANON_september2010.py'),
    ('stoqs_october2010',    'CANON/loadCANON_october2010.py'),
    ('stoqs_dorado2011',     'MolecularEcology/load_dorado2011.py'),
    ('stoqs_april2011',      'CANON/loadCANON_april2011.py'),
    ('stoqs_june2011',       'CANON/loadCANON_june2011.py'),
    ('stoqs_february2012',   'MolecularEcology/loadGOC_february2012.py'),
    ('stoqs_may2012',        'CANON/loadCANON_may2012.py'),
    ('stoqs_september2012',  'CANON/loadCANON_september2012.py'),
    ('stoqs_ioos_gliders',   'IOOS/load_gliders.py'),
    ('stoqs_march2013',      'CANON/loadCANON_march2013.py'),
    ('stoqs_march2013_o',    'CANON/loadCANON_march2013.py -o'),
    ('stoqs_beds2013',           'BEDS/loadBEDS_2013.py'),
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
    ('stoqs_cce2015',            'BEDS/loadCCE_2015.py'),
    ('stoqs_michigan2016',       'LakeMichigan/load_2016.py'),
    ('stoqs_canon_september2016',   'CANON/loadCANON_september2016.py'),
])
