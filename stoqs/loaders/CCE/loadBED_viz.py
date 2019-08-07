#!/usr/bin/env python
'''
Loader for bench test and simulated BEDs data to help understand
the visualizations offered in the STOQS UI

Mike McCann
MBARI 24 July 2019
'''

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parent_dir)  # So that CCE is found
from CCE import CCELoader

from collections import namedtuple
from DAPloaders import NoValidData
from datetime import datetime
import numpy as np
import timing

class CCE_2015_Campaign:

    def __init__(self, db_alias='stoqs_bed_viz', campaign_name='BED rotation visualization'):
        self.cl = CCELoader(db_alias, campaign_name,
                description = 'Bentic Event Detector quaternion data visualization database',
                x3dTerrains = { 
                    'https://stoqs.mbari.org/x3d/MontereyCanyonBeds_1m+5m_1x_src/MontereyCanyonBeds_1m+5m_1x_src_scene.x3d': {
                        'name': 'MontereyCanyonBeds_1m+5m_1x',
                        'position': '2232.80938 10346.25515 3543.76722',
                        'orientation': '-0.98394 0.16804 -0.06017 1.25033',
                        'centerOfRotation': '0 0 0',
                        'VerticalExaggeration': '1',
                        'geoOrigin': '36.80, -121.87, -400',
                        'speed': '1.0',
                        'zNear': '100.0',
                        'zFar': '30000.0',
                        'selected': '1'
                    },
                    'https://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
                        'name': 'Monterey25_1x',
                        'position': '-32985.28634 88026.90417 22334.02600',
                        'orientation': '-0.99875 -0.04772 0.01482 1.31683',
                        'centerOfRotation': '-20564.015827789044 -1956.065669754069 14112.954469753739',
                        'VerticalExaggeration': '1',
                        'geoOrigin': '36.80, -121.87, -400',
                        'speed': '1.0',
                        'zNear': '-1',
                        'zFar': '-1',
                    },
                 },
                 # Do not check in .grd files to the repository, keep them in the loaders directory
                 grdTerrain=os.path.join(parent_dir, 'MontereyCanyonBeds_1m+5m.grd'),
                 ##grdTerrain=os.path.join(parent_dir, 'Monterey25.grd'),
               )

        # Base OPeNDAP server
        self.cl.bed_base = 'http://dods.mbari.org/opendap/data/CCE_Processed/BEDs/'

        # Copied from ProjectLibrary to BEDs SVN working dir for netCDF conversion, and then copied to elvis.
        # See BEDs/BEDs/Visualization/py/makeBEDNetCDF_CCE.sh

        self.cl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROT_RATE', 'ROT_COUNT', 'P', 'P_ADJUSTED',
                        'P_RATE', 'P_SPLINE', 'P_SPLINE_RATE', 'ROT_DIST', 'IMPLIED_VELOCITY', 'BED_DEPTH_CSI',
                        'BED_DEPTH', 'BED_DEPTH_LI', 'DIST_TOPO', 'TUMBLE_RATE', 'TUMBLE_COUNT', 'TIDE',
                        'ROT_X', 'ROT_Y', 'ROT_Z', 'AXIS_X', 'AXIS_Y', 'AXIS_Z', 'ANGLE']

        # Just the event files for the CCE
        self.cl.bed_files_framegrabs_2016 = [
                        # Uncomment to test 3D replay of BED motion 
                        # - Gymbol lock problems mess up the visualization, so this remains confusing
                        ##('BED00/Simulated/netcdf/BED00_SIM_rolling_trajectory.nc', ''),
                        ##('BED00/Simulated/netcdf/BED00_cycle_rot_axes_200_202_trajectory.nc', ''),
                        ##('BED00/Simulated/netcdf/BED00_cycle_rot_axes_300_302_trajectory.nc', ''),

                        # Uncomment to load data from Bench orientation video
                        ('BED00/2013_04_29_Bench_Orientation/BED00092.nc', 
                         'http://dods.mbari.org/data/CCE_Processed/BEDs/Notes/BEDS_2013_04_29_Video_X3D_orientation.m4v'),
                        ] 

        self.cl.bed_files_framegrabs = self.cl.bed_files_framegrabs_2016

        self.cl.bed_files = [ffg[0] for ffg in self.cl.bed_files_framegrabs]
        self.cl.bed_framegrabs = [ffg[1] for ffg in self.cl.bed_files_framegrabs]
        self.cl.bed_platforms = [f.split('/')[0] for f in  self.cl.bed_files ]

        self.cl.process_command_line()


if __name__ == '__main__':
    campaign = CCE_2015_Campaign()
    if campaign.cl.args.test:
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(stride=1, featureType='trajectory')

    elif campaign.cl.args.optimal_stride:
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(stride=1, featureType='trajectory')

    else:
        campaign.cl.stride = campaign.cl.args.stride
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(featureType='trajectory')

    # Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
    campaign.cl.addTerrainResources()

    campaign.cl.logger.info("All Done.")

