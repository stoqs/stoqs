#!/bin/bash

# Shell script to load all MolecularEcology database saving the output to a .out file for ERROR and WARNING analysis
#
# Assumes that the dba on the system has created the database and synced them with the instructions in INSTALL
# Double check that the load script specifies description, x3dTerrains, grdTerrain, and executes cl.addTerrainResources() at end

loaders/MolecularEcology/load_dorado2011.py > loaders/MolecularEcology/load_dorado2011.out 2>&1
loaders/MolecularEcology/loadGOC_february2012.py > loaders/MolecularEcology/loadGOC_february2012.out 2>&1
loaders/MolecularEcology/loadSIMZ_aug2013.py > loaders/MolecularEcology/loadSIMZ_aug2013.out 2>&1
loaders/MolecularEcology/loadSIMZ_oct2013.py > loaders/MolecularEcology/loadSIMZ_oct2013.out 2>&1
loaders/MolecularEcology/loadSIMZ_spring2014.py > loaders/MolecularEcology/loadSIMZ_spring2014.out 2>&1


