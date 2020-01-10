#!/bin/env python
'''
Generate images of colormaps to populate static/images/colormaps.
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

from django.conf import settings
from utils.Viz.plotting import readCLT
import cmocean
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np

# List of tuples produced from https://matplotlib.org/tutorials/colors/colormaps.html
omaps = [('Ocean',          cmocean.cm.cmapnames),
         ('Uniform',
                            ['viridis', 'plasma', 'inferno', 'magma', 'cividis']),
         ('Sequential1',    ['Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
                             'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
                             'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']),
         ('Sequential2',    ['binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
                             'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
                             'hot', 'afmhot', 'gist_heat', 'copper']),
         ('Diverging',      ['PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
                             'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
         ('Qualitative',    ['Pastel1', 'Pastel2', 'Paired', 'Accent',
                             'Dark2', 'Set1', 'Set2', 'Set3',
                             'tab10', 'tab20', 'tab20b', 'tab20c']),
         ('Miscellaneous',  ['flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
                             'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
                             'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'])]

# Order the original colormap lists by name
cmaps = []
for cmap_category, cmap_list in omaps:
    cmaps.append((cmap_category, sorted(cmap_list)))

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

