#!/bin/env python
'''
Generate images of colormaps to populate static/images/colormaps.
'''

import os
import sys

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                            os.path.dirname(__file__), "../")))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

from django.conf import settings
from utils.Viz.plotting import readCLT
import cmocean
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np

cmaps = [('Ocean',          cmocean.cm.cmapnames),
         ('Uniform',
                            ['viridis', 'inferno', 'plasma', 'magma', 'cividis']),
         ('Sequential',     ['Blues', 'BuGn', 'BuPu',
                             'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd',
                             'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu',
                             'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd',
                             'afmhot', 'autumn', 'bone', 'cool',
                             'copper', 'gist_heat', 'gray', 'hot',
                             'pink', 'spring', 'summer', 'winter']),
         ('Diverging',      ['BrBG', 'bwr', 'coolwarm', 'PiYG', 'PRGn', 'PuOr',
                             'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'Spectral',
                             'seismic']),
         ('Qualitative',    ['Accent', 'Dark2', 'Paired', 'Pastel1',
                             'Pastel2', 'Set1', 'Set2', 'Set3']),
         ('Miscellaneous',  ['gist_earth', 'terrain', 'ocean', 'gist_stern',
                             'brg', 'CMRmap', 'cubehelix',
                             'gnuplot', 'gnuplot2', 'gist_ncar',
                             'nipy_spectral', 'jet', 'jetplus', 'rainbow',
                             'gist_rainbow', 'hsv', 'flag', 'prism'])]

# Add reverse colormaps to the cmaps list
cmaps_with_r = []
for cmap_category, cmap_list in cmaps:
    # Use list() to make copy of cmap_list
    cmap_list_r = list(cmap_list)
    cmap_list_r.extend(['{}_r'.format(c) for c in cmap_list])
    cmaps_with_r.append((cmap_category, cmap_list_r))

jetplus_clt = readCLT(os.path.join(str(settings.ROOT_DIR.path('static')), 
                                   'colormaps', 'jetplus.txt'))

def _plot_color_bar(category, cmap):
    '''Make an image file for each colormap
    '''
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    cb_fig = plt.figure(figsize=(2.56, 0.15))
    cb_ax = cb_fig.add_axes([0., 0., 1., 1.])
    if cmap == 'jetplus':
        cm_jetplus = colors.ListedColormap(np.array(jetplus_clt))
        cb_ax.imshow(gradient, aspect='auto', cmap=cm_jetplus)
    elif cmap == 'jetplus_r':
        cm_jetplus = colors.ListedColormap(np.array(jetplus_clt)[::-1])
        cb_ax.imshow(gradient, aspect='auto', cmap=cm_jetplus)
    else:
        if category == 'Ocean':
            cb_ax.imshow(gradient, aspect='auto', cmap=getattr(cmocean.cm, cmap))
        else:
            cb_ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(cmap))

    cb_ax.set_axis_off()
    file_name = os.path.join(str(settings.ROOT_DIR.path('static')), 'images', 'colormaps', cmap)
    cb_fig.savefig(file_name, dpi=100)
    plt.close()

def generate_colormaps():
    '''Build images as in http://matplotlib.org/examples/color/colormaps_reference.html
    '''
    print('Making colormap images:')
    for cmap_category, cmap_list in cmaps_with_r:
        print('\t{}:'.format(cmap_category))
        for cmap in cmap_list:
            print('\t\t{}'.format(cmap))
            _plot_color_bar(cmap_category, cmap)

        
if __name__ == '__main__':
    generate_colormaps()

