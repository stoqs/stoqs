#!/bin/sh
# Try loading each campaign in a new python instance to try
# and fix the id_seq reset problem.  Must be run from the 
# loaders/CANON directory.  Argument is the stride.

python loadCANON_september2010.py 10 stoqs_september2010_s10
python loadCANON_october2010.py 10 stoqs_october2010_s10
python loadCANON_april2011.py 10 stoqs_april2011_s10
python loadCANON_june2011.py 10 stoqs_june2011_s10
python loadCANON_october2011.py 10 stoqs_october2011_s10
python loadCANON_september2011.py 10 stoqs_september2011_s10
python loadCANON_may2012.py 10 stoqs_may2012_s10
python loadCANON_september2012.py 10 stoqs_september2012_s10

