#!/bin/bash

# Shell script to load all CANON database saving the output to a .out file for ERROR and WARNING analysis
#
# Assumes that the dba on the system has created the database and synced them with the instructions in INSTALL
# Double check that the load script specifies description, x3dTerrains, grdTerrain, and executes cl.addTerrainResources() at end

loaders/CANON/loadCANON_september2010.py > loaders/CANON/loadCANON_september2010.out 2>&1
loaders/CANON/loadCANON_october2010.py > loaders/CANON/loadCANON_october2010.out 2>&1
loaders/CANON/loadCANON_april2011.py > loaders/CANON/loadCANON_april2011.out 2>&1
loaders/CANON/loadCANON_june2011.py > loaders/CANON/loadCANON_june2011.out 2>&1
loaders/CANON/loadCANON_may2012.py > loaders/CANON/loadCANON_may2012.out 2>&1
loaders/CANON/loadCANON_september2012.py > loaders/CANON/loadCANON_september2012.out 2>&1
loaders/CANON/loadCANON_march2013.py > loaders/CANON/loadCANON_march2013.out 2>&1
loaders/CANON/loadCN13ID_october2013.py > loaders/CANON/loadCN13ID_october2013.out 2>&1

