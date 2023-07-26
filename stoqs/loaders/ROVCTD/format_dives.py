#! /usr/bin/env python

import sys

with open(sys.argv[1]) as f:
    for num, rec in enumerate(f):
        if "rov, dive" not in rec:  # Skip header
            rov, dive = rec.split(",")
            print(f"{rov.strip()[0]}{dive.strip()} ", end="")
            if not num % 10:
                print("\\")

print("\\")
