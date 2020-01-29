#!/usr/bin/env python


'''
Generate individual bitmap images that are colored according to a color map.
To be used to build .png files for use in building KML files so that colored 
IconStyles are not needed. This will allow openlayers to render the colored
dots.
'''

import os
import sys

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                            os.path.dirname(__file__), "../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend

import cmocean
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
from colormaps import cmaps
from django.conf import settings
from utils.Viz.plotting import readCLT

colordots_dir = os.path.join(str(settings.ROOT_DIR.path('static')), 'images', 'colordots')
jetplus_clt = readCLT(os.path.join(str(settings.ROOT_DIR.path('static')),
                                   'colormaps', 'jetplus.txt'))

def savePPM(r, g, b):
    '''
    Write ASCII netPPM file with 0-1 values for @r, @g, @b.  Files will
    be named with the hex values of abgr, the KML ordering of components.
    '''
    ##print 'r, g, b = %f, %f, %f' % (r, g, b)
    if r < 0 or r > 1 or g < 0 or g > 1 or b < 0 or b > 1:
        raise Exception('Illegal color components.  Values must be > 0.0 and < 1.0.')

    ge_color = "ff%02x%02x%02x" % ((round(b * 255), round(g * 255), round(r * 255)))
    im_color = "%02x%02x%02x" % ((round(r * 255), round(g * 255), round(b * 255)))
    file_name = os.path.join(colordots_dir, ge_color + '.png')
    ##print('Creating file_name = {}'.format(file_name))
    if os.path.exists(file_name):
        print('.', end='')
    else:
        # ImageMagick to create dot similar to http://maps.google.com/mapfiles/kml/shapes/dot.png, but with color
        ##cmd = '''convert -size 64x64 xc:none -fill '#%s' -draw 'circle 31.5,31.5 31.5,21' %s''' % (im_color, file_name)
        cmd = '''convert -size 8x8 xc:none -fill '#%s' -draw 'circle 3.5,3.5 3.5,0' %s''' % (im_color, file_name)
        ##print(cmd)
        os.system(cmd)
        print('X', end='')

def processColorMap(category, cmap):
    '''Read in colormap values and write ppm files
    '''

    if cmap == 'jetplus':
        cm = colors.ListedColormap(np.array(jetplus_clt))
    elif cmap == 'jetplus_r':
        cm  = colors.ListedColormap(np.array(jetplus_clt)[::-1])
    else:
        if category == 'Ocean':
            cm = getattr(cmocean.cm, cmap)
        else:
            cm = plt.get_cmap(cmap)

    for i in range(cm.N):
        c = cm(i)
        savePPM(float(c[0]), float(c[1]), float(c[2]))

if __name__ == '__main__':
    '''Create colored dot for each color in each color map
    '''
    print('Making colored dots:')
    for cmap_category, cmap_list in cmaps:
        print('  {}:'.format(cmap_category))
        for cmap in cmap_list:
            print('    {}:'.format(cmap), end='')
            processColorMap(cmap_category, cmap)
            print('')


    print("Now add/commit the changes to git and run:\nmanage.py collectstatic")
    
