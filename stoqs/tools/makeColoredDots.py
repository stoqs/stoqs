#!/usr/bin/env python

__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Generate individual bitmap images that are colored according to a color map.
To be used to build .png files for use in building KML files so that colored 
IconStyles are not needed. This will allow openlayers to render the colored
dots.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up
import settings
from utils.KML import readCLT

def savePPM(r, g, b, dir):
    '''
    Write ASCII netPPM file with 0-1 values for @r, @g, @b.  Files will
    be named with the hex values of abgr, the KML ordering of components.
    '''
    ##print 'r, g, b = %f, %f, %f' % (r, g, b)
    if r < 0 or r > 1 or g < 0 or g > 1 or b < 0 or b > 1:
        raise Exception('Illegal color components.  Values must be > 0.0 and < 1.0.')

    ge_color = "ff%02x%02x%02x" % ((round(b * 255), round(g * 255), round(r * 255)))
    im_color = "%02x%02x%02x" % ((round(r * 255), round(g * 255), round(b * 255)))
    fileName = os.path.join(dir, ge_color + '.png')
    ##print 'Creating fileName = %s' % fileName

    # ImageMagick to create dot similar to http://maps.google.com/mapfiles/kml/shapes/dot.png, but with color
    cmd = '''convert -size 64x64 xc:none -fill '#%s' -draw 'circle 31.5,31.5 31.5,21' %s''' % (im_color, fileName)
    print cmd
    os.system(cmd)

def processColorMap(colormapFileName='jetplus.txt'):
    '''
    Read in colormap values and write ppm files
    '''

    dir = os.path.join(settings.STATICFILES_DIRS[0], 'colormaps', 'jetplus_dots')
    for c in readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', colormapFileName)):
        savePPM(c[0], c[1], c[2], dir)

if __name__ == '__main__':

    processColorMap()
    print "Now commit and pus the changes in mercurial and run:\nmanage.py collectstatic"
    
