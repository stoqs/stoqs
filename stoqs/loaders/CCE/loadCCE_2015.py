#!/usr/bin/env python
'''

Master loader for all Coordinated Canyon Experiment data
from October 2015 through 2016

Mike McCann
MBARI 26 January March 2016
'''

import os
import sys
from datetime import datetime
parent_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parent_dir)  # settings.py is one dir up
import numpy as np

from CCE import CCELoader

cl = CCELoader('stoqs_cce2015', 'Coordinated Canyon Experiment',
                description = 'Coordinated Canyon Experiment - Measuring turbidity flows in Monterey Submarine Canyon',
                x3dTerrains = { 
                    'http://stoqs.mbari.org/x3d/MontereyCanyonBeds_1m+5m_1x_src/MontereyCanyonBeds_1m+5m_1x_src_scene.x3d': {
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
                    'http://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
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
cl.bed_base = 'http://dods.mbari.org/opendap/data/CCE_Processed/BEDs/'

# Copied from ProjectLibrary to BEDs SVN working dir for netCDF conversion, and then copied to elvis.
# See BEDs/BEDs/Visualization/py/makeBEDNetCDF_CCE.sh

cl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROT_RATE', 'ROT_COUNT', 'P', 'P_ADJUSTED',
                'P_RATE', 'P_SPLINE', 'P_SPLINE_RATE', 'ROT_DIST', 'IMPLIED_VELOCITY', 'BED_DEPTH_CSI',
                'BED_DEPTH', 'BED_DEPTH_LI', 'DIST_TOPO', 'TUMBLE_RATE', 'TUMBLE_COUNT', 'TIDE',
                'ROT_X', 'ROT_Y', 'ROT_Z', 'AXIS_X', 'AXIS_Y', 'AXIS_Z', 'ANGLE']

# Several BED files: 30200078 to 3020080
# bed_files, bed_platforms, bed_depths must have same number of items; they are zipped together in the load
##cl.bed_files = [('CanyonEvents/BED3/20151001_20160115/{}.nc').format(n) for n in range(30200078, 30200081)]
##cl.bed_platforms = ['BED03'] * len(cl.bed_files)
##cl.bed_depths = [201] * len(cl.bed_files)

# Just the event files for the CCE
cl.bed_files_framegrabs_2015 = [
                ('BED04/MBCCE_BED04_20151004_Event20151201/netcdf/40100037_full_traj.nc',
                 'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3872/00_17_50_24.html'),
                ('BED05/MBCCE_BED05_20151027_Event20151201/netcdf/50200024_decim_traj.nc',
                    'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3873/00_29_56_03.html'),
                ]
cl.bed_files_framegrabs_2016 = [
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
                ('BED09/MBCCE_BED09_20160408_Event20161124/netcdf/901001{}_full_traj.nc'.format(n), '') for n in (
                    list(range(56, 63)) + list(range(64, 66)))
                ] + [
                ('BED03/MBCCE_BED03_20161005_Event20161124/netcdf/30400015_decim_traj.nc',
                    ''),
                ('BED10/MBCCE_BED10_20160408_Event20161124/netcdf/A0100154_decim_traj.nc',
                    ''),
                ] 
cl.bed_files_framegrabs_2017 = [
                ('BED09/MBCCE_BED09_20160408_Watch/netcdf/9010000{}.nc'.format(n), '') for n in range(4, 8)
                ] + [
                ('BED09/MBCCE_BED09_20160408_Event20170109/netcdf/90100196_full_traj.nc',
                    ''),
                ('BED11/MBCCE_BED11_20161010_Event20170109/netcdf/B0100026_decim_traj.nc',
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
                ]
cl.bed_files_framegrabs = cl.bed_files_framegrabs_2015 + cl.bed_files_framegrabs_2016 + cl.bed_files_framegrabs_2017

cl.bed_files = [ffg[0] for ffg in cl.bed_files_framegrabs]
cl.bed_framegrabs = [ffg[1] for ffg in cl.bed_files_framegrabs]
cl.bed_platforms = [f.split('/')[0] for f in  cl.bed_files ]
cl.bed_depths = np.round(cl.get_start_bed_depths(), 1)

# CCE BIN data
cl.ccebin_startDatetime = datetime(2016, 1, 15)
cl.ccebin_endDatetime = datetime(2016, 1, 18)
cl.ccebin_nominaldepth = 1836
cl.ccebin_base = 'http://dods.mbari.org/opendap/data/CCE_Processed/BIN/20151013/netcdf/'
cl.ccebin_files = [
                    'MBCCE_BIN_CTD_20151013_timecorrected.nc',
                    'MBCCE_BIN_OXY_20151013_timecorrected.nc',
                    'MBCCE_BIN_ECO_20151013_timecorrected.nc',
                    'MBCCE_BIN_ADCP300_20151013.nc',
                    'MBCCE_BIN_ADCP1200_20151013.nc',
                    'MBCCE_BIN_ADCP1200_20151013.nc'
                  ]
cl.ccebin_parms = [ 'pressure', 'temperature', 'conductivity', 'turbidity', 'optical_backscatter',
                    'oxygen', 'saturation', 'optode_temperature',
                    'chlor', 'ntu1', 'ntu2',
                    'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

# MS1 ADCP data
cl.ccems1_nominal_depth = 225
cl.ccems1_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS1/20151006/ADCP300/'
cl.ccems1_files = [ 'MBCCE_MS1_ADCP300_20151006.nc' ]
cl.ccems1_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

# MS2 ADCP data
cl.ccems2_nominal_depth = 462
cl.ccems2_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS2/20151005/ADCP300/'
cl.ccems2_files = [ 'MBCCE_MS2_ADCP300_20151005.nc' ]
cl.ccems2_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

# MS3 ADCP data
cl.ccems3_nominal_depth = 764
cl.ccems3_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS3/20151005/ADCP300/'
cl.ccems3_files = [ 'MBCCE_MS3_ADCP300_20151005.nc' ]
cl.ccems3_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

# MS4 ADCP - data files are corrupted

# MS5 ADCP data
cl.ccems5_nominal_depth = 1315
cl.ccems5_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS5/20151020/ADCP300/'
cl.ccems5_files = [ 'MBCCE_MS5_ADCP300_20151020.nc' ]
cl.ccems5_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']

##cl.ccems4_nominal_depth = 462
##cl.ccems4_base = 'http://dods.mbari.org/opendap/data/CCE_Archive/MS4...'
##cl.ccems4_files = [ '' ]
##cl.ccems4_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', ]
##cl.ccems2_parms = [ 'u_1205', 'v_1206', 'w_1204', 'AGC_1202', 'Hdg_1215', 'Ptch_1216', 'Roll_1217']


# Full-deployment files, exatracted from SSDS with stride of 60
##cl.ccebin_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/ccebin2015/201510/'
##cl.ccebin_files = [
##                'ccebin2015_aanderaaoxy_20151013.nc',
##                'ccebin2015_adcp1825_20151013.nc',
##                'ccebin2015_adcp1827_20151013.nc',
##                'ccebin2015_adcp1828_20151013.nc',
##                'ccebin2015_ecotriplet_20151013.nc',
##                'ccebin2015_sbe16_20151013.nc',
##               ]
##cl.ccebin_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/ccebin20160115/201601/'
##cl.ccebin_files = [
##                ##'ccebin20160115_aanderaaoxy_20160115.nc',
##                'ccebin20160115_adcp1825_20160115.nc',
##                'ccebin20160115_adcp1827_20160115.nc',
##                'ccebin20160115_adcp1828_20160115.nc',
##                ##'ccebin20160115_ecotriplet_20160115.nc',
##                ##'ccebin20160115_sbe16_20160115.nc',
##               ]
##cl.ccebin_parms = [
##                'u_component_uncorrected', 'v_component_uncorrected',
##                'echo_intensity_beam1', 
##                #'echo_intensity_beam2', 'echo_intensity_beam3', 'echo_intensity_beam4',
##                #'std_head', 'std_pitch', 'std_roll', 'xdcr_temperature',
##                ##'Pressure', 'Salinity', 'Temperature',
##                ##'AirSaturation', 'Oxygen',
##                ##'Chlor', 'NTU1', 'NTU2',
##                  ] 


# Execute the load for trajectory representation
cl.process_command_line()

def load_cce_moorings(low_res_stride=20, high_res_stride=1,
                      bin_low_res_stride=300, bin_high_res_stride=1):
    # MS1: Low-res
    cl.ccems1_start_datetime = datetime(2016, 1, 15)
    cl.ccems1_end_datetime = datetime(2016, 1, 18)
    cl.load_ccems1(stride=low_res_stride)

    # High-res
    cl.ccems1_start_datetime = datetime(2016, 1, 15, 19, 0)
    cl.ccems1_end_datetime = datetime(2016, 1, 16, 0, 30)
    cl.load_ccems1(stride=high_res_stride)

    # MS2: Low-res
    cl.ccems2_start_datetime = datetime(2016, 1, 15)
    cl.ccems2_end_datetime = datetime(2016, 1, 18)
    cl.load_ccems2(stride=low_res_stride)

    # High-res
    cl.ccems2_start_datetime = datetime(2016, 1, 15, 21, 0)
    cl.ccems2_end_datetime = datetime(2016, 1, 16, 2, 0)
    cl.load_ccems2(stride=high_res_stride)

    # MS3: Low-res
    cl.ccems3_start_datetime = datetime(2016, 1, 15)
    cl.ccems3_end_datetime = datetime(2016, 1, 18)
    cl.load_ccems3(stride=low_res_stride)

    # High-res
    cl.ccems3_start_datetime = datetime(2016, 1, 15, 21, 0)
    cl.ccems3_end_datetime = datetime(2016, 1, 16, 2, 0)
    cl.load_ccems3(stride=high_res_stride)

    # MS5: Low-res
    cl.ccems5_start_datetime = datetime(2016, 1, 15)
    cl.ccems5_end_datetime = datetime(2016, 1, 18)
    cl.load_ccems5(stride=low_res_stride)

    # High-res
    cl.ccems5_start_datetime = datetime(2016, 1, 15, 21, 0)
    cl.ccems5_end_datetime = datetime(2016, 1, 16, 2, 0)
    cl.load_ccems5(stride=high_res_stride)

    # BIN: Low-res (10 minute) five day period
    cl.ccebin_startDatetime = datetime(2016, 1, 13)
    cl.ccebin_endDatetime = datetime(2016, 1, 18)
    cl.loadCCEBIN(stride=bin_low_res_stride)

    # High-res (2 second) 1-hour period
    cl.ccebin_startDatetime = datetime(2016, 1, 15, 23, 30)
    cl.ccebin_endDatetime = datetime(2016, 1, 16, 0, 30)
    cl.loadCCEBIN(stride=bin_high_res_stride)

if cl.args.test:
    load_cce_moorings(low_res_stride=300, high_res_stride=10, bin_low_res_stride=300, bin_high_res_stride=10)
    cl.loadBEDS(stride=5, featureType='trajectory')

elif cl.args.optimal_stride:
    load_cce_moorings(low_res_stride=300, high_res_stride=10, bin_low_res_stride=300, bin_high_res_stride=10)
    cl.loadBEDS(stride=1, featureType='trajectory')

else:
    cl.stride = cl.args.stride
    load_cce_moorings()
    cl.loadBEDS(featureType='trajectory')

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

