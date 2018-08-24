#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: $'.split()[1]
__date__ = '$Date: $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

convertToMatlab.py simply copies a set of .csv files to a parallel set renaming
the headers so that a simple Matlab script can read the data into a structure
that make converting to NetCDF easy.

File header information:
------------------------

% Device,10G100648
% File name,10G100648_20111103_112724
% Cast time (UTC),2011-11-03 11:27:24
% Cast time (local),2011-11-03 11:27:24
% Sample type,Cast
% Cast data,Processed
% Location source,GPS
% Default latitude,32
% Default altitude,0
% Start latitude,37.7246293
% Start longitude,-0.7640086
% Start altitude,42.349998474121094
% Start GPS horizontal error(Meter),2,25
% Start GPS vertical error(Meter),4,84000015258789
% Start GPS number of satellites,7
% End latitude,37.7247336
% End longitude,-0.7635351
% End altitude,74.389999389648438
% End GPS horizontal error(Meter),3,17000007629395
% End GPS vertical error(Meter),7,03999996185303
% End GPS number of satellites,7
% Cast duration (Seconds),152
% Samples per second,5
% Electronics calibration date,0001-01-01
% Conductivity calibration date,2010-07-28
% Temperature calibration date,2010-07-28
% Pressure calibration date,2010-07-28
% 
Pressure (Decibar),Depth (Meter),Temperature (Celsius),Conductivity (MicroSiemens per Centimeter),Specific conductance (MicroSiemens per Centimeter),Salinity (Practical Salinity Scale),Sound velocity (Meters per Second),Density (Kilograms per Cubic Meter)



@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import glob
import shutil

def fixHeader(line):
	'''For YSI Cataway data files replace header with a header that can be read by
	Matlab's mfcsvread.m.
	'''

	newName = {	'Pressure (Decibar)': 					'pressure',
			'Depth (Meter)': 					'depth',
			'Temperature (Celsius)': 				'temperature',
			'Conductivity (MicroSiemens per Centimeter)': 		'conductivity',
			'Specific conductance (MicroSiemens per Centimeter)': 	'specificconductivity',
			'Salinity (Practical Salinity Scale)': 			'salinity',
			'Sound velocity (Meters per Second)': 			'soundvelicity',
			'Density (Kilograms per Cubic Meter)': 			'density',
		}
   
	newLine = '' 
	for name in line.strip().split(','):
		newLine += newName[name] + ','

	return newLine[:-1]


if __name__ == '__main__':

	fixedHeaderDir = 'fixedHeaders'
	if not os.path.exists(fixedHeaderDir):
		os.mkdir(fixedHeaderDir)

	for file in glob.glob('*.csv'):
		print(file)
		outFile = open('%s/%s' % (fixedHeaderDir, file), 'w')
		i = 0
		for line in open(file, 'r'):
			if i == 0:
				fixedLine = fixHeader(line)
				outFile.write(fixedLine + '\r\n')
			else:
				outFile.write(line)
			i = i + 1

		##raw_input('Paused.')
	
