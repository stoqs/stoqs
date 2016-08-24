'''
A simple view designed to generate images of colormaps to choose from.
'''

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import Http404
from django.http import HttpResponse
import logging 
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

import matplotlib.pyplot as plt
import numpy as np
import os
import threading

logger=logging.getLogger(__name__)

cmaps = [('Uniform',
                            ['viridis', 'inferno', 'plasma', 'magma']),
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
                             'nipy_spectral', 'jet', 'rainbow',
                             'gist_rainbow', 'hsv', 'flag', 'prism'])]

def _plot_color_bar(cmap):
    '''Make an image file for each colormap
    '''
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    cb_fig = plt.figure(figsize=(2.56, 0.2))
    cb_ax = cb_fig.add_axes([0., 0., 1., 1.])
    cb_ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(cmap))
    cb_ax.set_axis_off()
    file_name = os.path.join(settings.STATIC_ROOT, 'images', 'colormaps', cmap)
    cb_fig.savefig(file_name, dpi=100)
    plt.close()

def generate_colormaps(request):
    '''Build images as in http://matplotlib.org/examples/color/colormaps_reference.html
    '''
    for cmap_category, cmap_list in cmaps:
        for cmap in cmap_list:
            _plot_color_bar(cmap)

        
    
