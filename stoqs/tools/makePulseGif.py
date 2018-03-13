#!/usr/bin/env python
#
# Use ImageMagick to make animated gif that pulses for the ajax-loader behind
# #time-depth-flot

import os
from numpy import arange, hstack

# Do a linear transition of transparency for a stronger indication of activity
i = 0
for a in hstack((arange(0, 1.0, 0.1), arange(1.0, 0, -0.1))):
    # Use background color of bootstrap's .well class
    cmd = "convert -size 1x1 xc:#f5f5f5 -fill 'rgba(192,211,228,%.2f)' -draw 'point 0,0' pulse_%03d.gif" % (a, i)
    print(cmd)
    os.system(cmd)
    i = i + 1

cmd = "convert -loop 0 -delay 1 pulse*.gif ajax-loader-pulse.gif"
print(cmd)
os.system(cmd)
