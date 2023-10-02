#!/bin/env python
'''
Generate images of colormaps to populate static/images/colormaps.
Executed on development system with generated .png files committed
to source code control and pushed to the remote repo.
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

class Colormap:
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

    def _plot_color_bar(self, category, cmap, with_alpha=False, file_name=None,
                        dmin=None, dmax=None, cmin=None, cmax=None, num_colors: int=256,
                        alpha_frac=0.5):
        '''Make an image file for each colormap.
        Use with_alpha = True to generate colormaps suitable for use in VolumeData/ImageTextureAtlas
        3D simulation visualizationr; dmin/dmax & cmin/cmax may be passed to build scaled colormap
        so that volume visualization color match the chosen colormap in the Temporal Depth section.
        '''
        if dmin is not None and dmax is not None and cmin is not None and cmax is not None:
            first_frac = int(num_colors * (cmin - dmin) / (dmax - dmin))
            last_frac = int(num_colors * (dmax - cmax) / (dmax - dmin))
            inner_frac = int(num_colors * (cmax - cmin) / (dmax - dmin))
            pad_to_num_colors = num_colors - first_frac - last_frac - inner_frac
            alpha_frac = (first_frac + (inner_frac / 2)) / num_colors 
            inner_gradient = np.linspace(0, 1, inner_frac + pad_to_num_colors)
            gradient = first_frac * [0] + list(inner_gradient) + last_frac * [1]
        else:
            gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))
        if with_alpha:
            # First half ramps transparency from full to none
            alpha_cutoff = alpha_frac * num_colors
            alpha = np.arange(0.0, 1.0, 1.0 / alpha_cutoff).tolist() + int(num_colors - int(alpha_cutoff)) * [1.0]
            alpha = np.vstack((alpha, alpha))

        cb_fig = plt.figure(figsize=(2.56, 0.15))
        cb_ax = cb_fig.add_axes([0., 0., 1., 1.])
        if cmap == 'jetplus':
            cm_jetplus = colors.ListedColormap(np.array(self.jetplus_clt))
            cb_ax.imshow(gradient, aspect='auto', cmap=cm_jetplus)
        elif cmap == 'jetplus_r':
            cm_jetplus = colors.ListedColormap(np.array(self.jetplus_clt)[::-1])
            cb_ax.imshow(gradient, aspect='auto', cmap=cm_jetplus)
        else:
            if category == 'Ocean':
                if with_alpha:
                    cb_ax.imshow(gradient, alpha=alpha, aspect='auto', cmap=getattr(cmocean.cm, cmap))
                else:
                    cb_ax.imshow(gradient, aspect='auto', cmap=getattr(cmocean.cm, cmap))
            else:
                if with_alpha:
                    cb_ax.imshow(gradient, alpha=alpha, aspect='auto', cmap=plt.get_cmap(cmap))
                else:
                    cb_ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(cmap))

        cb_ax.set_axis_off()
        if with_alpha:
            if not file_name:
                file_name = os.path.join(str(settings.ROOT_DIR.path('static')), 'images', 'colormaps_alpha', cmap)
            cb_fig.savefig(file_name, dpi=100, transparent=True)
        else:
            if not file_name:
                file_name = os.path.join(str(settings.ROOT_DIR.path('static')), 'images', 'colormaps', cmap)
            cb_fig.savefig(file_name, dpi=100)
        plt.close()

    def generate_colormaps(self):
        '''Build images as in http://matplotlib.org/examples/color/colormaps_reference.html
        '''
        print('Making colormap images:')
        for cmap_category, cmap_list in self.cmaps_with_r:
            print('\t{}:'.format(cmap_category))
            for cmap in cmap_list:
                print(f'\t\t{cmap:15s}: ', end='')
                self._plot_color_bar(cmap_category, cmap)
                print('and with_alpha to colormaps_alpha')
                self._plot_color_bar(cmap_category, cmap, with_alpha=True)

    def data_range_colormap(self, cmap, dmin, dmax, cmin, cmax, num_colors, file_name):
        '''Build images as in http://matplotlib.org/examples/color/colormaps_reference.html
        '''
        if cmap in cmocean.cm.cmapnames:
            cat = 'Ocean'
        else:
            cat = 'Matplotlib'

        print(f'Making data_range_colormap image for {cmap} in category {cat} to {file_name}')
        self._plot_color_bar(cat, cmap, True, file_name, dmin, dmax, cmin, cmax, num_colors)

if __name__ == '__main__':
    cm = Colormap()
    cm.generate_colormaps()
    # Test this for use in stoqs/utils/STOQSQManager.py
    ##cm.data_range_colormap('cividis', 0, 49, .5, 2, 256, '/srv/stoqs/data_range_colormap.png')

