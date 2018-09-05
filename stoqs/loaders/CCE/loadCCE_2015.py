#!/usr/bin/env python
'''

Master loader for all Coordinated Canyon Experiment data
from October 2015 through 2016

Mike McCann
MBARI 26 January March 2016
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

# CCE event start and end times for loading timeseriesprofile mooring (ADCP) data
Event = namedtuple('Event', ['start', 'end'])
lores_event_times = [
        Event(datetime(2016, 1, 15,  0,  0), datetime(2016, 1, 18,  0,  0)),
        Event(datetime(2016, 3,  5,  0,  0), datetime(2016, 3,  8,  0,  0)),
                     ]
hires_event_times = [
        Event(datetime(2016, 1, 15, 21,  0), datetime(2016, 1, 16,  2,  0)),
        Event(datetime(2016, 3,  6,  0,  0), datetime(2016, 3,  7,  0,  0)),
                     ]

# Overall time period for the whole campaign
campaign_start_datetime = datetime(2015, 10, 13, 0,  0)
campaign_end_datetime = datetime(2017, 4, 11, 0,  0)

class CCE_2015_Campaign:

    def __init__(self, db_alias='stoqs_cce2015', campaign_name='Coordinated Canyon Experiment'):
        self.cl = CCELoader(db_alias, campaign_name,
                description = 'Coordinated Canyon Experiment - Measuring turbidity flows in Monterey Submarine Canyon',
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

        # Several BED files: 30200078 to 3020080
        # bed_files, bed_platforms, bed_depths must have same number of items; they are zipped together in the load
        ##self.cl.bed_files = [(f'CanyonEvents/BED3/20151001_20160115/{n}.nc') for n in range(30200078, 30200081)]
        ##self.cl.bed_platforms = ['BED03'] * len(self.cl.bed_files)
        ##self.cl.bed_depths = [201] * len(self.cl.bed_files)

        # Just the event files for the CCE
        self.cl.bed_files_framegrabs_2015 = [
                        ('BED04/MBCCE_BED04_20151004_Event20151201/netcdf/40100037_full_traj.nc',
                         'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3872/00_17_50_24.html'),
                        ('BED05/MBCCE_BED05_20151027_Event20151201/netcdf/50200024_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3873/00_29_56_03.html'),
                        ]
        self.cl.bed_files_framegrabs_2016 = [
                        ('BED03/20151001_20160115/netcdf/30200078_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3874/00_21_23_28.html'),
                        ('BED06/20151001_20160115/netcdf/60100068_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3870/00_15_38_23.html'),
                        ('BED03/MBCCE_BED03_20160212_Event20160217/netcdf/30300004_decim_traj.nc',
                            ''),
                        ('BED05/MBCCE_BED05_20151027_Event20160115/netcdf/50200054_decim_traj.nc',
                            ''),
                        ('BED05/MBCCE_BED05_20151027_Event20160115/netcdf/50200055_decim_traj.nc',
                            ''),
                        ('BED05/MBCCE_BED05_20151027_Event20160115/netcdf/50200056_decim_traj.nc',
                            ''),
                        ('BED05/MBCCE_BED05_20151027_Event20160115/netcdf/50200057_decim_traj.nc',
                            ''),
                        ('BED03/MBCCE_BED03_20160212_Event20160306/netcdf/30300016_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20160306/netcdf/60200011_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20160306/netcdf/60200012_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20160901/netcdf/60200130_decim_traj.nc',
                            ''),
                        ('BED09/MBCCE_BED09_20160408_Event20160901/netcdf/90100096_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3922/02_55_51_27.html'),
                        ('BED10/MBCCE_BED10_20160408_Event20160901/netcdf/A0100096_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3921/02_05_37_16.html'),

                        ('BED00/Simulated/netcdf/BED00_SIM_rolling_trajectory.nc',
                            ''),
                        ] + [
                        (f'BED09/MBCCE_BED09_20160408_Event20161124/netcdf/901001{n}_full_traj.nc', '') for n in (
                            list(range(56, 63)) + list(range(64, 65)))
                        ] + [
                        ('BED09/MBCCE_BED09_20160408_Event20161124/netcdf/90100165_full.nc',
                            ''),
                        ('BED03/MBCCE_BED03_20161005_Event20161124/netcdf/30400015_decim_traj.nc',
                            ''),
                        ('BED10/MBCCE_BED10_20160408_Event20161124/netcdf/A0100154_decim_traj.nc',
                            ''),
                        ('BED04/MBCCE_BED04_20151004_Event20161124/netcdf/40200014_decim_traj.nc',
                            ''),
                        ] 
        self.cl.bed_files_framegrabs_2017 = [
                        (f'BED09/MBCCE_BED09_20160408_Watch/netcdf/9010000{n}.nc', '') for n in range(4, 8)
                        ] + [
                        ('BED09/MBCCE_BED09_20160408_Event20170109/netcdf/90100196_full_traj.nc',
                            ''),
                        ('BED11/MBCCE_BED11_20161010_Event20170109/netcdf/B0100026_full_traj.nc',
                            ''),
                        ('BED11/MBCCE_BED11_20161010_Event20170109/netcdf/B0100027_full.nc',
                            ''),
                        ('BED11/MBCCE_BED11_20161010_Event20170109/netcdf/B0100028_full_traj.nc',
                            ''),
                        ('BED00/Simulated/netcdf/BED00_cycle_rot_axes_200_202_trajectory.nc',
                            ''),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200014_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200014_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200015_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200016_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200016_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200017_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200019_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200020_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20161124/netcdf/80200020_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20170109/netcdf/80200034_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20170109/netcdf/80200039_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20170203/netcdf/80200046_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20170218/netcdf/80200050_decim_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED08/MBCCE_BED08_20161005_Event20170218/netcdf/80200052_full_traj.nc',
                            'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3969/00_26_09_00.html'),
                        ('BED11/MBCCE_BED11_20161010_Event20161124/netcdf/B0100012_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20170109/netcdf/60200218_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20170109/netcdf/60200219_decim_traj.nc',
                            ''),
                        ('BED03/MBCCE_BED03_20161005_Event20170203/netcdf/30400034_full_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20170203/netcdf/60200236_decim_traj.nc',
                            ''),
                        ('BED06/MBCCE_BED06_20160222_Event20170218/netcdf/60200246_decim_traj.nc',
                            ''),
                        ('BED11/MBCCE_BED11_20161010_Event20170203/netcdf/B0100036_full_traj.nc',
                            ''),
                        ('BED11/MBCCE_BED11_20161010_Event20170203/netcdf/B0100037_full.nc',
                            ''),
                        ]
        self.cl.bed_files_framegrabs = self.cl.bed_files_framegrabs_2015 + self.cl.bed_files_framegrabs_2016 + self.cl.bed_files_framegrabs_2017

        self.cl.bed_files = [ffg[0] for ffg in self.cl.bed_files_framegrabs]
        self.cl.bed_framegrabs = [ffg[1] for ffg in self.cl.bed_files_framegrabs]
        self.cl.bed_platforms = [f.split('/')[0] for f in  self.cl.bed_files ]
        # Execute just before loading BEDs data, as this delays the start of loading mooring data
        ##self.cl.bed_depths = np.round(self.cl.get_start_bed_depths(), 1)

        # CCE event start and end times for loading mooring data
        self.lores_event_times = lores_event_times
        self.hires_event_times = hires_event_times

        # CCE SIN (Seafloor Instrument Node) data - all parameters but the timeseriesprofile ADCP data
        self.cl.ccesin_nominaldepth = 1836
        self.cl.ccesin_base = 'http://dods.mbari.org/opendap/data/CCE_Processed/SIN/'
        self.cl.ccesin_files = [
                            '20151013/CTDOBSTrans/MBCCE_SIN_CTDOBSTrans_20151013_timecorrected.nc',
                            '20151013/OX/MBCCE_SIN_OX_20151013_timecorrected.nc',
                            '20151013/FLNTU/MBCCE_SIN_FLNTU_20151013_timecorrected.nc',
                            '20151013/ADCP300/MBCCE_SIN_ADCP300_20151013.nc',
                            '20151013/ADCP600/MBCCE_SIN_ADCP600_20151013.nc',
                            '20151013/ADCP1200/MBCCE_SIN_ADCP1200_20151013.nc',

                            '20160417/CTDOBSTrans/MBCCE_SIN_CTDOBSTrans_20160417_timecorrected.nc',
                            '20160417/OX/MBCCE_SIN_OX_20160417_timecorrected.nc',
                            '20160417/FLNTU/MBCCE_SIN_FLNTU_20160417_timecorrected.nc',

                            '20161018/CTDOBSTrans/MBCCE_SIN_CTDOBSTrans_20161018_timecorrected.nc',
                            '20161018/OX/MBCCE_SIN_OX_20161018_timecorrected.nc',
                            '20161018/FLNTU/MBCCE_SIN_FLNTU_20161018_timecorrected.nc',
                          ]
        self.cl.ccesin_parms = [ 'pressure', 'temperature', 'conductivity', 'turbidity', 'optical_backscatter',
                            'oxygen', 'saturation', 'optode_temperature',
                            'chlor', 'ntu1', 'ntu2',
                            'Hdg_1215', 'Ptch_1216', 'Roll_1217']

        # CCE SIN (Seafloor Instrument Node) data - files and parameters to load for just the events:
        # Just the timeseriesprofile ADCP data
        self.cl.ccesin_nominaldepth_ev = self.cl.ccesin_nominaldepth
        self.cl.ccesin_base_ev = self.cl.ccesin_base
        self.cl.ccesin_files_ev = [
                            '20151013/ADCP300/MBCCE_SIN_ADCP300_20151013.nc',
                            '20151013/ADCP600/MBCCE_SIN_ADCP600_20151013.nc',
                            '20151013/ADCP1200/MBCCE_SIN_ADCP1200_20151013.nc',
                          ]
        self.cl.ccesin_parms_ev = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202' ]

        # MS1 ADCP data - timeseries data
        self.cl.ccems1_start_datetime = campaign_start_datetime
        self.cl.ccems1_end_datetime = campaign_end_datetime
        self.cl.ccems1_nominal_depth = 225
        self.cl.ccems1_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS1/'
        self.cl.ccems1_files = [ 
                           '20151006/ADCP300/MBCCE_MS1_ADCP300_20151006.nc',
                           '20151006/Aquadopp2000/MBCCE_MS1_Aquadopp2000_20151006.nc',
                           '20151006/CTOBSTrans9m/MBCCE_MS1_CTOBSTrans9m_20151006.nc',
                           '20151006/TD65m/MBCCE_MS1_TD65m_20151006.nc',
                           '20151006/TU35m/MBCCE_MS1_TU35m_20151006.nc',
                           '20151006/TU65m/MBCCE_MS1_TU65m_20151006.nc',
                          ]
        self.cl.ccems1_parms = [ 
                           'Hdg_1215', 'Ptch_1216', 'Roll_1217',
                           'P_1', 'T_1211',
                           'T_28', 'S_41', 'ST_70', 'tran_4010', 'ATTN_55', 'NEP_56', 'Trb_980',
                          ]
        # MS1 ADCP data - timeseriesprofile (ADCP) data
        self.cl.ccems1_nominal_depth_ev = self.cl.ccems1_nominal_depth
        self.cl.ccems1_base_ev = self.cl.ccems1_base
        self.cl.ccems1_files_ev = [ 
                           '20151006/ADCP300/MBCCE_MS1_ADCP300_20151006.nc',
                           '20151006/Aquadopp2000/MBCCE_MS1_Aquadopp2000_20151006.nc',
                          ]
        self.cl.ccems1_parms_ev = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202' ]

        # MS2 ADCP data - timeseries data
        self.cl.ccems2_start_datetime = campaign_start_datetime
        self.cl.ccems2_end_datetime = campaign_end_datetime
        self.cl.ccems2_nominal_depth = 462
        self.cl.ccems2_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS2/'
        self.cl.ccems2_files = [ 
                           '20151005/ADCP300/MBCCE_MS2_ADCP300_20151005.nc',
                           '20151005/CTD9m/MBCCE_MS2_CTD9m_20151005.nc',
                           '20151005/TU9m/MBCCE_MS2_TU9m_20151005.nc',
                          ]
        self.cl.ccems2_parms = [ 
                           'Hdg_1215', 'Ptch_1216', 'Roll_1217',
                           'D_3', 'P_1', 'T_28', 'S_41',
                           'NEP_56', 'Trb_980',
                          ]
        # MS2 ADCP data - timeseriesprofile (ADCP) data
        self.cl.ccems2_nominal_depth_ev = self.cl.ccems2_nominal_depth
        self.cl.ccems2_base_ev = self.cl.ccems2_base
        self.cl.ccems2_files_ev = [ 
                           '20151005/ADCP300/MBCCE_MS2_ADCP300_20151005.nc',
                          ]
        self.cl.ccems2_parms_ev = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202' ]

        # MS3 ADCP and CTD data - timeseries data
        self.cl.ccems3_start_datetime = campaign_start_datetime
        self.cl.ccems3_end_datetime = campaign_end_datetime
        self.cl.ccems3_nominal_depth = 764
        self.cl.ccems3_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS3/'
        self.cl.ccems3_files = [ 
                           '20151005/ADCP300/MBCCE_MS3_ADCP300_20151005.nc',
                           '20151005/Aquadopp2000/MBCCE_MS3_Aquadopp2000_20151005.nc',
                           '20151005/CT9m/MBCCE_MS3_CT9m_20151005.nc',
                           '20151005/TU9m/MBCCE_MS3_TU9m_20151005.nc',
                          ]
        self.cl.ccems3_parms = [ 
                           'Hdg_1215', 'Ptch_1216', 'Roll_1217',
                           'P_1', 'T_1211', 'NEP1_56',
                           'T_28', 'S_41', 'ST_70',
                           'tran_4010', 'ATTN_55',
                          ]
        # MS3 ADCP data - timeseriesprofile (ADCP) data
        self.cl.ccems3_nominal_depth_ev = self.cl.ccems3_nominal_depth
        self.cl.ccems3_base_ev = self.cl.ccems3_base
        self.cl.ccems3_files_ev = [ 
                           '20151005/ADCP300/MBCCE_MS3_ADCP300_20151005.nc',
                           '20151005/Aquadopp2000/MBCCE_MS3_Aquadopp2000_20151005.nc',
                          ]
        self.cl.ccems3_parms_ev = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202' ]


        # MS4 ADCP - 20151005 data files are corrupted
        ##self.cl.ccems4_nominal_depth = 462
        ##self.cl.ccems4_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS4...'
        ##self.cl.ccems4_files = [ '' ]
        ##self.cl.ccems4_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', ]
        ##self.cl.ccems4_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']


        # MS5 ADCP data - timeseries data
        self.cl.ccems5_start_datetime = campaign_start_datetime
        self.cl.ccems5_end_datetime = campaign_end_datetime
        self.cl.ccems5_nominal_depth = 1315
        self.cl.ccems5_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS5/'
        self.cl.ccems5_files = [ 
                           '20151020/ADCP300/MBCCE_MS5_ADCP300_20151020.nc',
                          ]
        self.cl.ccems5_parms = [ 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

        # MS3 ADCP data - timeseriesprofile (ADCP) data
        self.cl.ccems5_nominal_depth_ev = self.cl.ccems5_nominal_depth
        self.cl.ccems5_base_ev = self.cl.ccems5_base
        self.cl.ccems5_files_ev = [ 
                           '20151020/ADCP300/MBCCE_MS5_ADCP300_20151020.nc',
                          ]
        self.cl.ccems5_parms_ev = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202' ]

        # Full-deployment files, exatracted from SSDS with stride of 60
        ##self.cl.ccesin_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/ccesin2015/201510/'
        ##self.cl.ccesin_files = [
        ##                'ccesin2015_aanderaaoxy_20151013.nc',
        ##                'ccesin2015_adcp1825_20151013.nc',
        ##                'ccesin2015_adcp1827_20151013.nc',
        ##                'ccesin2015_adcp1828_20151013.nc',
        ##                'ccesin2015_ecotriplet_20151013.nc',
        ##                'ccesin2015_sbe16_20151013.nc',
        ##               ]
        ##self.cl.ccesin_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/ccesin20160115/201601/'
        ##self.cl.ccesin_files = [
        ##                ##'ccesin20160115_aanderaaoxy_20160115.nc',
        ##                'ccesin20160115_adcp1825_20160115.nc',
        ##                'ccesin20160115_adcp1827_20160115.nc',
        ##                'ccesin20160115_adcp1828_20160115.nc',
        ##                ##'ccesin20160115_ecotriplet_20160115.nc',
        ##                ##'ccesin20160115_sbe16_20160115.nc',
        ##               ]
        ##self.cl.ccesin_parms = [
        ##                'u_component_uncorrected', 'v_component_uncorrected',
        ##                'echo_intensity_beam1', 
        ##                #'echo_intensity_beam2', 'echo_intensity_beam3', 'echo_intensity_beam4',
        ##                #'std_head', 'std_pitch', 'std_roll', 'xdcr_temperature',
        ##                ##'Pressure', 'Salinity', 'Temperature',
        ##                ##'AirSaturation', 'Oxygen',
        ##                ##'Chlor', 'NTU1', 'NTU2',
        ##                  ] 


        # Execute the load for trajectory representation
        self.cl.process_command_line()

    def load_ccemoorings(self, stride=20, start_mooring=1, end_mooring=5):
        for mooring in range(start_mooring, end_mooring + 1):
            if hasattr(self.cl, f'ccems{mooring:d}_base'):
                try:
                    getattr(self.cl, f'load_ccems{mooring:d}')(stride=stride)
                except NoValidData as e:
                    self.cl.logger.warn(str(e))

    def load_ccemoorings_ev(self, low_res_stride=20, high_res_stride=1,
                                start_mooring=1, end_mooring=5):
        # DRY: for all moorings load all lo res and hi res data that have a .._base attribute
        for mooring in range(start_mooring, end_mooring + 1):
            if not hasattr(self.cl, f'ccems{mooring:d}_base_ev'):
                self.cl.logger.warning(f'Skipping mooring ms{mooring:d}, no ccems{mooring:d}_base_ev attribute')
                continue
            setattr(self.cl, f'ccems{mooring:d}_base', eval(f'self.cl.ccems{mooring:d}_base_ev'))
            setattr(self.cl, f'ccems{mooring:d}_files', eval(f'self.cl.ccems{mooring:d}_files_ev'))
            setattr(self.cl, f'ccems{mooring:d}_parms', eval(f'self.cl.ccems{mooring:d}_parms_ev'))
            if hasattr(self.cl, f'ccems{mooring:d}_base'):
                for event in self.lores_event_times:
                    setattr(self.cl, f'ccems{mooring:d}_start_datetime', event.start)
                    setattr(self.cl, f'ccems{mooring:d}_end_datetime', event.end)
                    try:
                        getattr(self.cl, f'load_ccems{mooring:d}')(stride=low_res_stride)
                    except NoValidData as e:
                        self.cl.logger.warn(str(e))

                for event in self.hires_event_times:
                    setattr(self.cl, f'ccems{mooring:d}_start_datetime', event.start)
                    setattr(self.cl, f'ccems{mooring:d}_end_datetime', event.end)
                    try:
                        getattr(self.cl, f'load_ccems{mooring:d}')(stride=high_res_stride)
                    except NoValidData as e:
                        self.cl.logger.warn(str(e))

    def load_ccesin_ev(self, low_res_stride=300, high_res_stride=1):
        # Assign standard attributes with the data we want loaded just for the events
        setattr(self.cl, 'ccesin_base', self.cl.ccesin_base_ev)
        setattr(self.cl, 'ccesin_files', self.cl.ccesin_files_ev)
        setattr(self.cl, 'ccesin_parms', self.cl.ccesin_parms_ev)
        setattr(self.cl, 'ccesin_nominaldepth', self.cl.ccesin_nominaldepth_ev)

        # SIN: start and end times Low-res with stride for 10 minute intervals
        for event in lores_event_times:
            setattr(self.cl, 'ccesin_start_datetime', event.start)
            setattr(self.cl, 'ccesin_end_datetime', event.end)
            try:
                getattr(self.cl, 'loadCCESIN')(stride=low_res_stride)
            except NoValidData as e:
                self.cl.logger.warn(str(e))

        # SIN: start and end times High-res with stride for 2 seconds intervals
        for event in hires_event_times:
            setattr(self.cl, 'ccesin_start_datetime', event.start)
            setattr(self.cl, 'ccesin_end_datetime', event.end)
            try:
                getattr(self.cl, 'loadCCESIN')(stride=high_res_stride)
            except NoValidData as e:
                self.cl.logger.warn(str(e))


if __name__ == '__main__':
    campaign = CCE_2015_Campaign()
    if campaign.cl.args.test:
        campaign.load_ccemoorings(stride=100, start_mooring=1, end_mooring=5)
        campaign.load_ccemoorings_ev(low_res_stride=10, start_mooring=1, end_mooring=5)
        campaign.cl.loadCCESIN(stride=1000)    # Normal base class loader for entire time series
        campaign.load_ccesin_ev(low_res_stride=1000, high_res_stride=100)
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(stride=100, featureType='trajectory')

    elif campaign.cl.args.optimal_stride:
        campaign.load_ccemoorings(stride=10)
        campaign.load_ccemoorings_ev(low_res_stride=10, high_res_stride=2)
        campaign.cl.loadCCESIN(stride=1000)    # Normal base class loader for entire time series
        campaign.load_ccesin_ev(low_res_stride=300, high_res_stride=2)
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(stride=1, featureType='trajectory')

    else:
        campaign.cl.stride = campaign.cl.args.stride
        campaign.load_ccemoorings()
        campaign.load_ccemoorings_ev()
        ##campaign.cl.loadCCESIN(stride=300)    # Uncomment to load entire record of 10-minute data
        campaign.load_ccesin_ev()
        campaign.cl.bed_depths = [np.round(d, 1) for d in campaign.cl.get_start_bed_depths()]
        campaign.cl.loadBEDS(featureType='trajectory')

    # Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
    campaign.cl.addTerrainResources()

    campaign.cl.logger.info("All Done.")

