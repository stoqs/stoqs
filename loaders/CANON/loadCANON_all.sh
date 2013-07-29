#!/bin/sh
# Try loading each campaign in a new python instance to try
# and fix the id_seq reset problem.  Must be run from the 
# loaders/CANON directory.  Argument is the stride.

python loadCANON_september2010.py 1 stoqs_september2010
python loadCANON_october2010.py 1 stoqs_october2010
python loadCANON_april2011.py 1 stoqs_april2011
python loadCANON_june2011.py 1 stoqs_june2011
python loadCANON_may2012.py 1 stoqs_may2012
python loadCANON_september2012.py 1 stoqs_september2012

