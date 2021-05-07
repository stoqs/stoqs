#!/usr/bin/env python
'''
Convert STOQS Measured Parameter Data Access .parquet output to CSV format.
'''

import argparse
import pandas as pd
import sys

instructions = f'''
Can be run in an Anaconda environment thusly...
    First time - install necessary packages:
        conda create --name stoqs-parquet python=3.8
        conda activate stoqs-parquet
        pip install pandas pyarrow fastparquet
    Thereafter:
        conda activate stoqs-parquet
        {sys.argv[0]} --url ...
'''
parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter,
                                 epilog=instructions)
parser.add_argument('--url', action='store', help="The .parquet URL from STOQS", 
                    required=True)
parser.add_argument('--out', action='store', help=("Optional output file name"
                    " - if not specified then send to stdout"))
args = parser.parse_args()

df = pd.read_parquet(args.url)
if args.out:
    fh = open(args.out, 'w')
    df.to_csv(fh)
    fh.close()
else:
    print(df.to_csv())
