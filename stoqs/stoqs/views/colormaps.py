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

cmaps = [('Perceptually_Uniform_Sequential',
                            ['viridis', 'inferno', 'plasma', 'magma']),
         ('Sequential_1',     ['Blues', 'BuGn', 'BuPu',
                             'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd',
                             'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu',
                             'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']),
         ('Sequential_2', ['afmhot', 'autumn', 'bone', 'cool',
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

nrows = max(len(cmap_list) for cmap_category, cmap_list in cmaps)
gradient = np.linspace(0, 1, 256)
gradient = np.vstack((gradient, gradient))

def _plot_color_gradients(cmap_category, cmap_list):
    fig, axes = plt.subplots(nrows=nrows)
    fig.subplots_adjust(top=0.95, bottom=0.01, left=0.2, right=0.99)
    axes[0].set_title(cmap_category + ' colormaps', fontsize=14)

    for ax, name in zip(axes, cmap_list):
        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(name))
        pos = list(ax.get_position().bounds)
        x_text = pos[0] - 0.01
        y_text = pos[1] + pos[3]/2.
        fig.text(x_text, y_text, name, va='center', ha='right', fontsize=10)

    # Turn off *all* ticks & spines, not just the ones with colormaps.
    for ax in axes:
        ax.set_axis_off()

    fn = os.path.join(settings.MEDIA_ROOT, 'sections', cmap_category)
    fig.savefig(fn, dpi=120)

def generate_colormaps(request):
    '''Build images as in http://matplotlib.org/examples/color/colormaps_reference.html
    '''
    for cmap_category, cmap_list in cmaps:
        _plot_color_gradients(cmap_category, cmap_list)
        fn = os.path.join(settings.MEDIA_ROOT, 'sections', cmap_category) + '.png'
        with open(fn, 'rb') as f:
            response = HttpResponse(f.read(), content_type="image/png")
            return response


    ##except Exception:
    ##    logger.exception('Doh!')
    ##    raise SuspiciousOperation('Attempt to create permalink without any data, or with invalid data')
        
    return response
    
