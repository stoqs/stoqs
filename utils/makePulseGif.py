#!/usr/bin/env python
#
# Use ImageMagick to make animated gif that pulses for the ajax-loader behind
# #time-depth-flot

import os
from numpy import arange, sin, pi

smax = 20
i = 0
for s in (smax * sin(arange(0, 2*pi, 0.2))) + smax:
    cmd = "convert -size 1x1 xc:none -fill 'hsl(208,%s,89)' -draw 'point 0,0' pulse_%03d.gif" % (s, i)
    print cmd
    os.system(cmd)
    i = i + 1

cmd = "convert -loop 0 -delay 1 pulse*.gif ajax-loader-pulse.gif"
print cmd
os.system(cmd)
