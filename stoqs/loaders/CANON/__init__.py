#!/usr/bin/env python

__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

'''
Contains class for common routines for loading all CANON data

Mike McCann
MBARI 22 April 2012

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                os.path.dirname(__file__), "../../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

import DAPloaders
import requests
import urllib
import xarray as xr

from SampleLoaders import SeabirdLoader, SubSamplesLoader, ParentSamplesLoader
from lrauv_support import MissionLoader
from LRAUV.make_load_scripts import lrauvs
from bs4 import BeautifulSoup
from loaders import LoadScript, FileNotFound, SIGMAT, SPICE, SPICINESS, ALTITUDE
from stoqs.models import InstantPoint
from django.db.models import Max
from datetime import datetime, timedelta
from argparse import Namespace
from lxml import etree
from nettow import NetTow
from planktonpump import PlanktonPump
from thredds_crawler.crawl import Crawl
from urllib.request import urlopen, HTTPError
import logging
import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex
import numpy as np
import re
import webob

def getStrideText(stride):
    '''
    Format stride into a string to be appended to the Activity name, if stride==1 return empty string
    '''
    if stride == 1:
        return ''
    else:
        return ' (stride=%d)' % stride


class CANONLoader(LoadScript):
    '''
    Common routines for loading all CANON data
    '''

    brownish = {'dorado':       '8c510a',
                'tethys':       'bf812d',
                'daphne':       'dfc27d',
                'fulmar':       'f6e8c3',
                'waveglider':   'c7eae5',
                'nps_g29':      '80cdc1',
                'l_662':        '35978f',
                'l_662a':       '38978f',
                'm1':           '35f78f',
                'm2':           '35f760',
                'martin':       '01665e',
                'flyer':        '11665e',
                'espdrift':     '21665e',
             }
    colors = { 
                'other':        'ffeda0',
                'fulmar':       'fd8d3c',
                'waveglider':   'fc4e2a',
                'nps_g29':      'e31a1c',
                'l_662':        'bd0026',
                'l_662a':       'bd008f',
                'nps29':        '0b9131',
                'nps34':        '36d40f',
                'nps34a':        '36d40f',
                'sg539':        '5f9131',
                'sg621':        '507131',
                'm1':           'bd2026',
                'm2':           'bd4040',
                'oa':           '0f9cd4',
                'oa2':          '2d2426',
                'hehape':       'bd2026',
                'rusalka':      'bd4026',
                'carmen':       'bd8026',
                'martin':       '800026',
                'flyer':        '801026',
                'carson':       '730a46',
                'espdrift':     '802026',
                'espmack':      '804026',
                'espbruce':     '808026',
                'Stella201':    '26f080',
                'Stella202':    'F02696',
                'Stella203':    'F08026',
                'Stella204':    'AAAA26',
                'stella203':    'F08026',
                'stella204':    'AAAA26',
                'Stella205':    '2696f0',
                'nemesis':      'FFF026',
                'ucsc294':      'FFBA26',
                'slocum_294':   'FFBA26',
                'slocum_nemesis':'FFF026',
                'ucsc260':      'FF8426',
                'slocum_260':   'FF8426',
                'wg_oa':        '0f9cd4',
                'wg_tex':       '9626ff',
                'wg_Tiny':      '960000',
                'wg_Sparky':    'FCDD00',
                'wg_272':       '98FF26',
                'wg_Hansen':    '9AD484',
                'deimos':       '33D4FF',
                'saildrone':    'ff0c0c',   # CSS button color on https://www.saildrone.com/
             }

    # Distribute AUV colors along a yellow to brown palette, auv_names imported from LRAUV/make_load_scripts.py
    YlOrBr = plt.cm.YlOrBr
    # Have dummy1 take up the first blackish color
    auv_names = ['dummy1', 'dorado'] + list(lrauvs)
    for auv_name, c in zip(auv_names, YlOrBr(np.linspace(0, YlOrBr.N, len(auv_names), dtype=int))):
        colors[auv_name] = rgb2hex(c)[1:]

    # Colors for roms_* "platforms"
    roms_platforms = ('roms_spray', 'roms_sg621')
    num_roms = len(roms_platforms)
    oranges = plt.cm.Oranges
    for b, c in zip(roms_platforms, oranges(np.arange(0, oranges.N, oranges.N/num_roms))):
        colors[b] = rgb2hex(c)[1:]

    def loadDorado(self, startdate=None, enddate=None,
                   parameters=[
                    # Legacy Matlab built parameters
                    'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine', 'par',
                    'bbp470', 'bbp676', 'fl676_uncorr',
                    'sepCountList', 'mepCountList', 'roll', 'pitch', 'yaw', 
                    # New auv-python built parameters
                    'ctd1_temperature_onboard', 'ctd1_temperature',
                    'ctd1_salinity_onboard', 'ctd1_salinity', 'ctd1_flow1',
                    'ctd2_temperature_onboard', 'ctd2_temperature',
                    'ctd2_salinity_onboard', 'ctd2_salinity', 'ctd2_flow2',
                    'ctd1_dissolvedO2', 'ctd1_oxygen_mll', 'ctd1_oxygen_umolkg',
                    'hs2_bb470', 'hs2_bb676', 'hs2_fl676',
                    'hs2_bb420', 'hs2_bb700', 'hs2_fl700',
                    'navigation_roll', 'navigation_pitch', 'navigation_yaw',
                    'navigation_mWaterSpeed', 'tailcone_propRpm',
                    'lopc_countListSum', 'lopc_transCount', 'lopc_nonTransCount',
                    'lopc_LCcount', 'lopc_flowSpeed',
                    'ecopuck_bbp700', 'ecopuck_cdom', 'ecopuck_chl',
                    'biolume_flow', 'biolume_raw', 'biolume_avg_biolume',
                    'biolume_nbflash_high', 'biolume_nbflash_low', 'biolume_bg_biolume',
                    'biolume_proxy_adinos', 'biolume_proxy_hdinos', 'biolume_proxy_diatoms',
                    'biolume_intflash', 'profile_number',
                    'isus_nitrate',
                    ], stride=None,
                    file_patterns=(r".*_decim.nc$", r".*netcdf/dorado_.*1S.nc", ),
                    build_attrs=False, plankton_proxies=False, title_match=""):
        '''
        Support legacy use of loadDorado() and permit wider use by specifying startdate and endate
        '''
        pname = 'dorado'
        psl = ParentSamplesLoader('', '', dbAlias=self.dbAlias)
        if build_attrs:
            self.logger.info(f'Building load parameter attributes from crawling TDS')
            self.build_dorado_attrs(pname, startdate, enddate, parameters, file_patterns, title_match)
        else:
            self.logger.info(f'Using load {pname} attributes set in load script')
            parameters = getattr(self, f'{pname}_parms')

        stride = stride or self.stride
        if hasattr(self, 'dorado_base'):
            urls = [os.path.join(self.dorado_base, f) for f in self.dorado_files]
        else:
            urls = self.dorado_urls

        for url in urls:
            dfile = url.split('/')[-1]
            aname = dfile + getStrideText(stride)
            try:
                mps_loaded = DAPloaders.runDoradoLoader(url, self.campaignName, self.campaignDescription, aname, 
                                           pname, self.colors[pname], 'auv', 'AUV mission', 
                                           self.dorado_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain,
                                           plotTimeSeriesDepth=0.0, plankton_proxies=plankton_proxies)
                if mps_loaded:
                    if aname.startswith("Dorado389"):
                        # Legacy Gulper loads
                        psl.load_gulps(aname, dfile, self.dbAlias)
                    elif aname.startswith("dorado_"):
                        # New Gulper loads as Activities
                        psl.load_gulper_activities(aname, dfile, self.dbAlias, url, self.colors[pname])
            except DAPloaders.DuplicateData as e:
                self.logger.warn(str(e))
                self.logger.info(f"Skipping load of {url}")

        self.addPlatformResources('https://stoqs.mbari.org/x3d/dorado/dorado_scan3.glb', pname,
                                  scalefactor=2)

    def load_i2MAP(self, startdate=None, enddate=None,
                   parameters=[ 'seabird25p_temperature_onboard', 'seabird25p_temperature',
                                'seabird25p_conductivity_onboard', 'seabird25p_conductivity',
                                'seabird25p_salinity_onboard', 'seabird25p_salinity',
                                'seabird25p_dissolvedO2_onboard', 'seabird25p_dissolvedO2',
                                'seabird25p_dissolvedO2_port_onboard', 'seabird25p_dissolvedO2_port',
                                'seabird25p_dissolvedO2_stbd_onboard', 'seabird25p_dissolvedO2_stbd',
                                'seabird25p_oxygen_mll', 'seabird25p_oxygen_umolkg',
                                'seabird25p_oxygen_mll_port', 'seabird25p_oxygen_umolkg_port',
                                'seabird25p_oxygen_mll_stbd', 'seabird25p_oxygen_umolkg_stbd',
                                'seabird25p_beam_transmittance',
                                'navigation_roll', 'navigation_pitch', 'navigation_yaw',
                                'navigation_mWaterSpeed', 'tailcone_propRpm' ],
                    stride=None,
                    file_patterns=r".*netcdf/i2map_.*1S.nc", build_attrs=False, plankton_proxies=False):
        '''
        With i2map_*_1S.nc files in the AUVCTD/surveys directories we can use the Dorado loading code
        '''
        pname = 'i2map'
        psl = ParentSamplesLoader('', '', dbAlias=self.dbAlias)
        if build_attrs:
            self.logger.info(f"Building load parameter attributes for {pname} by crawling TDS with file_patterns={file_patterns}")
            self.build_i2map_attrs(pname, startdate, enddate, parameters, file_patterns)
        else:
            self.logger.info(f'Using load {pname} attributes set in load script')
            parameters = getattr(self, f'{pname}_parms')

        stride = stride or self.stride
        if hasattr(self, 'i2map_base'):
            urls = [os.path.join(self.i2map_base, f) for f in self.i2map_files]
        else:
            urls = self.i2map_urls

        for url in urls:
            dfile = url.split('/')[-1]
            aname = dfile + getStrideText(stride)
            try:
                mps_loaded = DAPloaders.runDoradoLoader(url, self.campaignName, self.campaignDescription, aname, 
                                           pname, self.colors['dorado'], 'auv', 'i2MAP mission', 
                                           self.i2map_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain,
                                           plotTimeSeriesDepth=0.0, plankton_proxies=plankton_proxies)
                if mps_loaded:
                    psl.load_gulps(aname, dfile, self.dbAlias)
            except DAPloaders.DuplicateData as e:
                self.logger.warn(str(e))
                self.logger.info(f"Skipping load of {url}")

        self.addPlatformResources('https://stoqs.mbari.org/x3d/dorado/simpleDorado389.x3d', pname,
                                  scalefactor=2)

    def _execute_load(self, pname, parameters, stride, critSimpleDepthTime):
        psl = ParentSamplesLoader('', '', dbAlias=self.dbAlias)
        lrauv_ml = MissionLoader('', '', dbAlias=self.dbAlias)
        stride = stride or self.stride
        files = getattr(self, f'{pname}_files')
        base = getattr(self, f'{pname}_base')
        for (aname, f) in zip([ a + getStrideText(stride) for a in files], files):
            url = os.path.join(base, f)
            # shorten the activity names
            if 'slate.nc' in aname or 'shore' in aname:
                aname = f"{pname}_{'_'.join(aname.split('/')[-2:])}"
            else:
                aname = f"{pname}_{aname.rsplit('/', 1)[-1]}"
            if hasattr(self, f'{pname}_aux_coords'):
                aux_coords = getattr(self, f'{pname}_aux_coords')
            else:
                setattr(self, f'{pname}s_aux_coords', None)
                aux_coords = None
            try:
                # Early LRAUV data had time coord of 'Time', override with auxCoords setting from load script
                DAPloaders.runLrauvLoader(url, self.campaignName, self.campaignDescription, aname, 
                                          pname, self.colors[pname], 'auv', 'LRAUV log',
                                          parameters, self.dbAlias, stride, 
                                          grdTerrain=self.grdTerrain, command_line_args=self.args,
                                          plotTimeSeriesDepth=0, auxCoords=aux_coords,
                                          critSimpleDepthTime=critSimpleDepthTime)
                psl.load_lrauv_samples(pname, aname, url, self.dbAlias)
                lrauv_ml.load_missions(pname, aname, url, self.dbAlias)
            except DAPloaders.NoValidData:
                self.logger.info("No valid data in %s" % url)
            except (webob.exc.HTTPError, UnboundLocalError) as e:
                self.logger.warn(f"{e}")
            except FileNotFoundError as e:
                # Likely missing syslog for LRAUV mission - should be reported as a failed unserialize
                self.logger.error(str(e))
            except Exception as e:
                if 'shore_i.nc' in url:
                    self.logger.warn(f"{e}")
                    self.logger.info(f"Being tolerant of shore_i.nc files and ignoring this warning")
                else:
                    raise

        self.addPlatformResources(f'https://stoqs.mbari.org/x3d/lrauv/lrauv_{pname}.x3d', pname,
                                  scalefactor=2)

    def loadLRAUV(self, pname, startdate=None, enddate=None, 
                  parameters=['temperature', 'salinity', 'chlorophyll', 'nitrate', 'oxygen','bbp470', 'bbp650','PAR',
                    'yaw', 'pitch', 'roll', 'control_inputs_rudder_angle', 'control_inputs_mass_position',
                    'control_inputs_buoyancy_position', 'control_inputs_propeller_rotation_rate',
                    'health_platform_battery_charge', 'health_platform_average_voltage',
                    'health_platform_average_current','fix_latitude', 'fix_longitude',
                    'fix_residual_percent_distance_traveled_DeadReckonUsingSpeedCalculator',
                    'pose_longitude_DeadReckonUsingSpeedCalculator',
                    'pose_latitude_DeadReckonUsingSpeedCalculator',
                    'pose_depth_DeadReckonUsingSpeedCalculator',
                    'fix_residual_percent_distance_traveled_DeadReckonUsingMultipleVelocitySources',
                    'pose_longitude_DeadReckonUsingMultipleVelocitySources',
                    'pose_latitude_DeadReckonUsingMultipleVelocitySources',
                    'pose_depth_DeadReckonUsingMultipleVelocitySources',
                    'chromophoric_dissolved_organic_matter',
                    'BackscatteringCoeff700nm',
                    'VolumeScatCoeff117deg700nm',
                    'petroleum_hydrocarbons',
                    'mass_concentration_of_oxygen_in_sea_water', 'chl',
                    'bin_mean_sea_water_salinity', 'bin_median_sea_water_salinity', 
                    'bin_mean_sea_water_temperature', 'bin_median_sea_water_temperature',
                    'bin_mean_mass_concentration_of_chlorophyll_in_sea_water', 'bin_median_mass_concentration_of_chlorophyll_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water',
                    'bin_mean_mass_concentration_of_petroleum_hydrocarbons_in_sea_water',
                    'bin_median_mass_concentration_of_petroleum_hydrocarbons_in_sea_water',
                    'concentration_of_colored_dissolved_organic_matter_in_sea_water',
                    'bin_mean_concentration_of_colored_dissolved_organic_matter_in_sea_water',
                    'bin_median_concentration_of_colored_dissolved_organic_matter_in_sea_water',
                  ],
                  stride=None, file_patterns=('.*2S_scieng.nc$'), build_attrs=True, 
                  dlist_str=None, err_on_missing_file=False, critSimpleDepthTime=10,
                  sbd_logs=False, cell_logs=False):

        if sbd_logs:
            dir_string = 'sbdlogs' 
            file_patterns=('.*shore_i.nc$')
        elif cell_logs:
            dir_string = "TODO: Will be 'celllogs' when implemented" 
        else:
            dir_string = 'missionlogs'
        if build_attrs:
            self.logger.info(f'Building load parameter attributes crawling LRAUV {dir_string} dirs for {pname}')
            for mission_year in range(startdate.year, enddate.year + 1):
                self.build_lrauv_attrs(mission_year, pname, startdate, enddate, parameters, 
                                       file_patterns, dlist_str, err_on_missing_file, sbd_logs, cell_logs)
                self._execute_load(pname, parameters, stride, critSimpleDepthTime)
        else:
            self.logger.info(f'Using load {pname} attributes set in load script')
            parameters = getattr(self, f'{pname}_parms')
            self._execute_load(pname, parameters, stride, critSimpleDepthTime)

    def loadMartin(self, stride=None):
        '''
        Martin specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.martin_files], self.martin_files):
            url = self.martin_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'Martin', self.colors['martin'], 'ship', 'cruise', 
                                           self.martin_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadJMuctd(self, stride=None):
        '''
        Martin specific underway load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.JMuctd_files], self.JMuctd_files):
            url = self.JMuctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'John_Martin_UCTD', self.colors['martin'], 'ship', 'cruise', 
                                           self.JMuctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadJMpctd(self, stride=None, platformName='John_Martin_PCTD', activitytypeName='John Martin Profile CTD Data'):
        '''
        Martin specific underway load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.JMpctd_files], self.JMpctd_files):
            url = self.JMpctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           platformName, self.colors['martin'], 'ship', activitytypeName,
                                           self.JMpctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)
        # load all the bottles           
        sl = SeabirdLoader(aName[:5], platformName, dbAlias=self.dbAlias, campaignName=self.campaignName, 
                           platformColor=self.colors['martin'], platformTypeName='ship', dodsBase=self.JMpctd_base)
        if self.args.verbose:
            sl.logger.setLevel(logging.DEBUG)
        sl.tdsBase= self.tdsBase
        sl.process_btl_files(self.JMpctd_files)

    def loadFulmar(self, stride=None):
        '''
        Fulmar specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.fulmar_files], self.fulmar_files):
            url = self.fulmar_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'fulmar', self.colors['fulmar'], 'ship', 'cruise', 
                                           self.fulmar_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadNps_g29(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.nps_g29_files], self.nps_g29_files):
            url = self.nps_g29_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'nps_g29', self.colors['nps_g29'], 'glider', 'Glider Mission', 
                                       self.nps_g29_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain,
                                       command_line_args=self.args)

    def loadL_662(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.l_662_files], self.l_662_files):
            url = self.l_662_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'SPRAY_L66_Glider', self.colors['l_662'], 'glider', 'Glider Mission', 
                                       self.l_662_parms, self.dbAlias, stride, self.l_662_startDatetime, 
                                       self.l_662_endDatetime, grdTerrain=self.grdTerrain,
                                       command_line_args=self.args)

    def loadL_662a(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.l_662a_files], self.l_662a_files):
            url = self.l_662a_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'SPRAY_L66a_Glider', self.colors['l_662a'], 'glider', 'Glider Mission',
                                       self.l_662a_parms, self.dbAlias, stride, self.l_662a_startDatetime,
                                       self.l_662a_endDatetime, grdTerrain=self.grdTerrain,
                                       command_line_args=self.args)

    def load_NPS29(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.nps29_files], self.nps29_files):
            url = self.nps29_base + f
            try:
                DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'NPS_Glider_29', self.colors['nps29'], 'glider', 'Glider Mission', 
                                            self.nps29_parms, self.dbAlias, stride, self.nps29_startDatetime, 
                                            self.nps29_endDatetime, grdTerrain=self.grdTerrain, 
                                            command_line_args=self.args)
            except (DAPloaders.OpendapError, DAPloaders.NoValidData, webob.exc.HTTPError) as e:
                self.logger.warn(str(e))

    def load_SG539(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.sg539_files], self.sg539_files):
            url = self.sg539_base + f
            try:
                DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'SG_Glider_539', self.colors['sg539'], 'glider', 'Glider Mission',
                                        self.sg539_parms, self.dbAlias, stride, self.sg539_startDatetime,
                                        self.sg539_endDatetime, grdTerrain=self.grdTerrain,
                                        command_line_args=self.args)
            except (DAPloaders.OpendapError, DAPloaders.NoValidData) as e:
                self.logger.warn(str(e))

    def load_SG621(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.sg621_files], self.sg621_files):
            url = self.sg621_base + f
            try:
                DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'SG_Glider_621', self.colors['sg621'], 'glider', 'Glider Mission',
                                        self.sg621_parms, self.dbAlias, stride, self.sg621_startDatetime,
                                        self.sg621_endDatetime, grdTerrain=self.grdTerrain,
                                        command_line_args=self.args)
            except (DAPloaders.OpendapError, DAPloaders.NoValidData) as e:
                self.logger.warn(str(e))

    def load_NPS34(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.nps34_files], self.nps34_files):
            url = self.nps34_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'NPS_Glider_34', self.colors['nps34'], 'glider', 'Glider Mission', 
                                        self.nps34_parms, self.dbAlias, stride, self.nps34_startDatetime, 
                                        self.nps34_endDatetime, grdTerrain=self.grdTerrain,
                                        command_line_args=self.args)

    def load_NPS34a(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.nps34a_files], self.nps34a_files):
            url = self.nps34a_base + f
            try:
                DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'NPS_Glider_34', self.colors['nps34a'], 'glider', 'Glider Mission',
                                        self.nps34a_parms, self.dbAlias, stride, self.nps34a_startDatetime,
                                        self.nps34a_endDatetime, grdTerrain=self.grdTerrain,
                                        command_line_args=self.args)
            except (webob.exc.HTTPError, DAPloaders.NoValidData) as e:
                self.logger.warn(str(e))
                self.logger.warn(f'{e}')

    def load_glider_ctd(self, stride=None):
        '''
        Glider load functions.  Requires apriori knowledge of glider file names so we can extract platform and color name
        To be used with gliders that follow the same naming convention, i.e. nemesis_ctd.nc, ucsc260_ctd.nc
        and that load the exact same parameters, i.e. TEMP, PSAL or TEMP, PSAL, FLU2 or TEMP, FLU2, OPBS etc
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.glider_ctd_files], self.glider_ctd_files):
            url = self.glider_ctd_base + f
            gplatform=aName.split('_')[0].upper() + '_Glider'
            gname=aName.split('_')[0].lower()
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       gplatform, self.colors[gname], 'glider', 'Glider Mission', 
                                       self.glider_ctd_parms, self.dbAlias, stride, self.glider_ctd_startDatetime, 
                                       self.glider_ctd_endDatetime, grdTerrain=self.grdTerrain)

    def load_glider_met(self, stride=None):
        '''
        Glider load functions.  Requires apriori knowledge of glider file names so we can extract platform and color name
        To be used with gliders that follow the same naming convention, i.e. nemesis_met.nc, ucsc260_met.nc
        and that load the exact same parameters, i.e. meanu,meanv or windspeed, winddirection etc.
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.glider_met_files], self.glider_met_files):
            url = self.glider_met_base + f
            gplatform=aName.split('_')[0].upper() + '_Glider'
            gname=aName.split('_')[0].lower()
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       gplatform, self.colors[gname], 'glider', 'Glider Mission', 
                                       self.glider_met_parms, self.dbAlias, stride, self.glider_met_startDatetime, 
                                       self.glider_met_endDatetime, grdTerrain=self.grdTerrain)


    def load_slocum_260(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.slocum_260_files], self.slocum_260_files):
            url = self.slocum_260_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'Slocum_260', self.colors['slocum_260'], 'glider', 'Glider Mission', 
                                       self.slocum_260_parms, self.dbAlias, stride, self.slocum_260_startDatetime, 
                                       self.slocum_260_endDatetime, grdTerrain=self.grdTerrain)

    def load_slocum_294(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.slocum_294_files], self.slocum_294_files):
            url = self.slocum_294_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'Slocum_294', self.colors['slocum_294'], 'glider', 'Glider Mission', 
                                       self.slocum_294_parms, self.dbAlias, stride, 
                                       self.slocum_294_startDatetime, self.slocum_294_endDatetime,
                                       grdTerrain=self.grdTerrain)

    def load_slocum_nemesis(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.slocum_nemesis_files], self.slocum_nemesis_files):
            url = self.slocum_nemesis_base + f
            try:
                DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'Slocum_nemesis', self.colors['slocum_nemesis'], 'glider', 'Glider Mission', 
                                        self.slocum_nemesis_parms, self.dbAlias, stride, 
                                        self.slocum_nemesis_startDatetime, self.slocum_nemesis_endDatetime,
                                        grdTerrain=self.grdTerrain, plotTimeSeriesDepth=0)
            except DAPloaders.NoValidData as e:
                self.logger.warn(f'No valid data in {url}')
            except DAPloaders.DuplicateData as e:
                self.logger.warn(f'Data from {url} already in database, skipping')

    def load_wg_oa(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_oa_files], self.wg_oa_files):
            url = self.wg_oa_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_OA_Glider', self.colors['wg_oa'], 'waveglider', 'Glider Mission',
                                       self.wg_oa_parms, self.dbAlias, stride, self.wg_oa_startDatetime, 
                                       self.wg_oa_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_oa_pco2(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_oa_pco2_files], self.wg_oa_pco2_files):
            url = self.wg_oa_pco2_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_OA_Glider', self.colors['wg_oa'], 'waveglider', 'Glider Mission', 
                                       self.wg_oa_pco2_parms, self.dbAlias, stride, 
                                       self.wg_oa_pco2_startDatetime, self.wg_oa_pco2_endDatetime,
                                       grdTerrain=self.grdTerrain)

    def load_wg_oa_ctd(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_oa_ctd_files], self.wg_oa_ctd_files):
            url = self.wg_oa_ctd_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_OA_Glider', self.colors['wg_oa'], 'waveglider', 'Glider Mission', 
                                       self.wg_oa_ctd_parms, self.dbAlias, stride, self.wg_oa_ctd_startDatetime, 
                                       self.wg_oa_ctd_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_tex_ctd(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_tex_ctd_files], self.wg_tex_ctd_files):
            url = self.wg_tex_ctd_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_Tex_Glider', self.colors['wg_tex'], 'waveglider', 'Glider Mission', 
                                       self.wg_tex_ctd_parms, self.dbAlias, stride, self.wg_tex_ctd_startDatetime, 
                                       self.wg_tex_ctd_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_oa_met(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_oa_met_files], self.wg_oa_met_files):
            url = self.wg_oa_met_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_OA_Glider', self.colors['wg_oa'], 'waveglider', 'Glider Mission', 
                                       self.wg_oa_met_parms, self.dbAlias, stride, self.wg_oa_met_startDatetime, 
                                       self.wg_oa_met_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_tex_met(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_tex_met_files], self.wg_tex_met_files):
            url = self.wg_tex_met_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_Tex_Glider', self.colors['wg_tex'], 'waveglider', 'Glider Mission', 
                                       self.wg_tex_met_parms, self.dbAlias, stride, self.wg_tex_met_startDatetime, 
                                       self.wg_tex_met_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_tex(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_tex_files], self.wg_tex_files):
            url = self.wg_tex_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_Tex_Glider', self.colors['wg_tex'], 'waveglider', 'Glider Mission', 
                                       self.wg_tex_parms, self.dbAlias, stride, self.wg_tex_startDatetime, 
                                       self.wg_tex_endDatetime, grdTerrain=self.grdTerrain)

    def load_wg_Tiny(self, stride=None):
        '''
        Glider specific load functions, sets plotTimeSeriesDepth=0 to get Parameter tab in UI
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_Tiny_files], self.wg_Tiny_files):
            url = self.wg_Tiny_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_Tiny_Glider', self.colors['wg_Tiny'], 'waveglider', 'Glider Mission',
                                       self.wg_Tiny_parms, self.dbAlias, stride, self.wg_Tiny_startDatetime, 
                                       self.wg_Tiny_endDatetime, grdTerrain=self.grdTerrain, plotTimeSeriesDepth=0,
                                       command_line_args=self.args)

    def load_wg_Sparky(self, stride=None):
        '''
        Glider specific load functions, sets plotTimeSeriesDepth=0 to get Parameter tab in UI
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_Sparky_files], self.wg_Sparky_files):
            url = self.wg_Sparky_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'wg_Sparky_Glider', self.colors['wg_Sparky'], 'waveglider', 'Glider Mission',
                                       self.wg_Sparky_parms, self.dbAlias, stride, self.wg_Sparky_startDatetime,
                                       self.wg_Sparky_endDatetime, grdTerrain=self.grdTerrain, plotTimeSeriesDepth=0)

    def load_wg_272(self, stride=None):
        '''
        Glider specific load functions, sets plotTimeSeriesDepth=0 to get Parameter tab in UI
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_272_files], self.wg_272_files):
            url = self.wg_272_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'wg_272_Glider', self.colors['wg_272'], 'waveglider', 'Glider Mission',
                                       self.wg_272_parms, self.dbAlias, stride, self.wg_272_startDatetime,
                                       self.wg_272_endDatetime, grdTerrain=self.grdTerrain, plotTimeSeriesDepth=0)

    def load_wg_Hansen(self, stride=None):
        '''
        Glider specific load functions, sets plotTimeSeriesDepth=0 to get Parameter tab in UI
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_Hansen_files], self.wg_Hansen_files):
            url = self.wg_Hansen_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName,
                                       'wg_Hansen_Glider', self.colors['wg_Hansen'], 'waveglider', 'Glider Mission',
                                       self.wg_Hansen_parms, self.dbAlias, stride, self.wg_Hansen_startDatetime,
                                       self.wg_Hansen_endDatetime, grdTerrain=self.grdTerrain, plotTimeSeriesDepth=0,
                                       command_line_args=self.args)


    def load_wg_oa(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wg_oa_files], self.wg_oa_files):
            url = self.wg_oa_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'wg_OA_Glider', self.colors['wg_oa'], 'waveglider', 'Glider Mission', 
                                       self.wg_oa_parms, self.dbAlias, stride, self.wg_oa_startDatetime, 
                                       self.wg_oa_endDatetime, grdTerrain=self.grdTerrain)

    def load_oa1(self, stride=None):
        '''
        Mooring OA1 specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.oa1_files], self.oa1_files):
            url = os.path.join(self.oa1_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment',
                                        self.oa1_parms, self.dbAlias, stride, self.oa1_startDatetime, self.oa1_endDatetime,
                                        command_line_args=self.args)

    def load_oa2(self, stride=None):
        '''
        Mooring OA2 specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.oa2_files], self.oa2_files):
            url = os.path.join(self.oa2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment',
                                        self.oa2_parms, self.dbAlias, stride, self.oa2_startDatetime, self.oa2_endDatetime,
                                        command_line_args=self.args)


    def loadOA1pco2(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1pco2_files], self.OA1pco2_files):
            url = os.path.join(self.OA1pco2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1pco2_parms, self.dbAlias, stride, self.OA1pco2_startDatetime, self.OA1pco2_endDatetime)


    def loadOA1fl(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1fl_files], self.OA1fl_files):
            url = os.path.join(self.OA1fl_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1fl_parms, self.dbAlias, stride, self.OA1fl_startDatetime, self.OA1fl_endDatetime)


    def loadOA1o2(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1o2_files], self.OA1o2_files):
            url = os.path.join(self.OA1o2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1o2_parms, self.dbAlias, stride, self.OA1o2_startDatetime, self.OA1o2_endDatetime)

    def loadOA1ctd(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1ctd_files], self.OA1ctd_files):
            url = os.path.join(self.OA1ctd_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1ctd_parms, self.dbAlias, stride, self.OA1ctd_startDatetime, self.OA1ctd_endDatetime)


    def loadOA1pH(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1pH_files], self.OA1pH_files):
            url = os.path.join(self.OA1pH_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1pH_parms, self.dbAlias, stride, self.OA1pH_startDatetime, self.OA1pH_endDatetime)


    def loadOA1met(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA1met_files], self.OA1met_files):
            url = os.path.join(self.OA1met_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA1_Mooring', self.colors['oa'], 'mooring', 'Mooring Deployment', 
                                        self.OA1met_parms, self.dbAlias, stride, self.OA1met_startDatetime, self.OA1met_endDatetime)


    def loadOA2pco2(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2pco2_files], self.OA2pco2_files):
            url = os.path.join(self.OA2pco2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2pco2_parms, self.dbAlias, stride, self.OA2pco2_startDatetime, self.OA2pco2_endDatetime)


    def loadOA2fl(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2fl_files], self.OA2fl_files):
            url = os.path.join(self.OA2fl_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2fl_parms, self.dbAlias, stride, self.OA2fl_startDatetime, self.OA2fl_endDatetime)


    def loadOA2o2(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2o2_files], self.OA2o2_files):
            url = os.path.join(self.OA2o2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2o2_parms, self.dbAlias, stride, self.OA2o2_startDatetime, self.OA2o2_endDatetime)

    def loadOA2ctd(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2ctd_files], self.OA2ctd_files):
            url = os.path.join(self.OA2ctd_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2ctd_parms, self.dbAlias, stride, self.OA2ctd_startDatetime, self.OA2ctd_endDatetime)


    def loadOA2pH(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2pH_files], self.OA2pH_files):
            url = os.path.join(self.OA2pH_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2pH_parms, self.dbAlias, stride, self.OA2pH_startDatetime, self.OA2pH_endDatetime)


    def loadOA2met(self, stride=None):
        '''
        Mooring OA specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.OA2met_files], self.OA2met_files):
            url = os.path.join(self.OA2met_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'OA2_Mooring', self.colors['oa2'], 'mooring', 'Mooring Deployment', 
                                        self.OA2met_parms, self.dbAlias, stride, self.OA2met_startDatetime, self.OA2met_endDatetime)

    def loadBruceMoor(self, stride=None):
        '''
        Mooring Bruce specific load functions
        '''
        stride = stride or self.stride
        pName = 'ESP_Bruce_Mooring'
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.bruce_moor_files], self.bruce_moor_files):
            url = os.path.join(self.bruce_moor_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        pName, self.colors['espbruce'], 'mooring', 
                                        'Mooring Deployment', self.bruce_moor_parms, self.dbAlias, stride, 
                                        self.bruce_moor_startDatetime, self.bruce_moor_endDatetime)

        # Let browser code use {{STATIC_URL}} to fill in the /stoqs/static path
        self.addPlatformResources('x3d/ESPMooring/esp_base_scene.x3d', pName)

    def loadMackMoor(self, stride=None):
        '''
        Mooring Mack specific load functions
        '''
        stride = stride or self.stride
        pName = 'ESP_Mack_Mooring'
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.mack_moor_files], self.mack_moor_files):
            url = os.path.join(self.mack_moor_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        pName, self.colors['espmack'], 'mooring', 'Mooring Deployment',
                                        self.mack_moor_parms, self.dbAlias, stride, 
                                        self.mack_moor_startDatetime, self.mack_moor_endDatetime)

        # Let browser code use {{STATIC_URL}} to fill in the /stoqs/static path
        self.addPlatformResources('x3d/ESPMooring/esp_base_scene.x3d', pName)

    def loadM1(self, stride=None):
        '''
        Mooring M1 specific load functions
        '''
        platformName = 'M1_Mooring'
        stride = stride or self.stride
        start_datetime = getattr(self, 'm1_startDatetime', None)
        end_datetime = getattr(self, 'm1_endDatetime', None)
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.m1_files], self.m1_files):
            url = os.path.join(self.m1_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        platformName, self.colors['m1'], 'mooring', 'Mooring Deployment', 
                                        self.m1_parms, self.dbAlias, stride, start_datetime, 
                                        end_datetime, command_line_args=self.args) 
    
        # For timeseriesProfile data we need to pass the nominaldepth of the plaform
        # so that the model is put at the correct depth in the Spatial -> 3D view.
        try:
            self.addPlatformResources('https://stoqs.mbari.org/x3d/m1_assembly/m1_assembly_scene.x3d', 
                                      platformName, nominaldepth=self.m1_nominaldepth)
        except AttributeError:
            self.addPlatformResources('https://stoqs.mbari.org/x3d/m1_assembly/m1_assembly_scene.x3d', 
                                      platformName)

    def loadM2(self, stride=None):
        '''
        Mooring M2 specific load functions
        '''
        platformName = 'M2_Mooring'
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.m2_files], self.m2_files):
            url = os.path.join(self.m2_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        platformName, self.colors['m2'], 'mooring', 'Mooring Deployment', 
                                        self.m2_parms, self.dbAlias, stride, self.m2_startDatetime, 
                                        self.m2_endDatetime, command_line_args=self.args)
    
        # For timeseriesProfile data we need to pass the nominaldepth of the plaform
        # so that the model is put at the correct depth in the Spatial -> 3D view.
        try:
            self.addPlatformResources('https://stoqs.mbari.org/x3d/m1_assembly/m1_assembly_scene.x3d', 
                                      platformName, nominaldepth=self.m2_nominaldepth)
        except AttributeError:
            self.addPlatformResources('https://stoqs.mbari.org/x3d/m1_assembly/m1_assembly_scene.x3d', 
                                      platformName)

    def loadM1ts(self, stride=None):
        '''
        Mooring M1ts specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.m1ts_files], self.m1ts_files):
            url = self.m1ts_base + f
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'M1_Mooring', self.colors['m1'], 'mooring', 'Mooring Deployment', 
                                        self.m1ts_parms, self.dbAlias, stride, 
                                        self.m1ts_startDatetime, self.m1ts_endDatetime)

    def loadM1met(self, stride=None):
        '''
        Mooring M1met specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.m1met_files], self.m1met_files):
            url = self.m1met_base + f
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        'M1_Mooring', self.colors['m1'], 'mooring', 'Mooring Deployment', 
                                        self.m1met_parms, self.dbAlias, stride, 
                                        self.m1met_startDatetime, self.m1met_endDatetime)

    def loadDEIMOS(self, startdate=None, enddate=None, stride=None):
        '''
        Mooring DEIMOS EK60 specific load functions
        '''
        platformName = 'DEIMOS'
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.deimos_files], self.deimos_files):
            url = os.path.join(self.deimos_base, f)
            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName, 
                                        platformName, self.colors['deimos'], 'mooring', 'Mooring Deployment', 
                                        self.deimos_parms, self.dbAlias, stride, startdate,
                                        enddate, command_line_args=self.args) 
    
    def loadHeHaPe(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.hehape_files], self.hehape_files):
            url = self.hehape_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'hehape', self.colors['hehape'], 'glider', 'Glider Mission', 
                                       self.hehape_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadRusalka(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.rusalka_files], self.rusalka_files):
            url = self.rusalka_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'rusalka', self.colors['rusalka'], 'glider', 'Glider Mission', 
                                       self.rusalka_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadCarmen(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.carmen_files], self.carmen_files):
            url = self.carmen_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'carmen', self.colors['carmen'], 'glider', 'Glider Mission', 
                                       self.carmen_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadWaveglider(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.waveglider_files], self.waveglider_files):
            url = self.waveglider_base + f
            DAPloaders.runGliderLoader(url, self.campaignName, self.campaignDescription, aName, 
                                       'waveglider', self.colors['waveglider'], 'glider', 'Glider Mission', 
                                       self.waveglider_parms, self.dbAlias, stride, self.waveglider_startDatetime, 
                                       self.waveglider_endDatetime, grdTerrain=self.grdTerrain)

    def loadStella(self, stride=None):
        '''
        Stella drift specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.stella_files], self.stella_files):
            url = self.stella_base + f
            dname='Stella' + aName[6:9]
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           dname, self.colors[dname], 'drifter', 'Stella drifter Mission', 
                                           self.stella_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadESPdrift(self, stride=None):
        '''
        ESPdrift specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.espdrift_files], self.espdrift_files):
            url = self.espdrift_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'espdrift', self.colors['espdrift'], 'drifter', 'ESP drift Mission', 
                                           self.espdrift_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadESPmack(self, stride=None):
        '''
        ESPmack specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.espmack_files], self.espmack_files):
            url = self.espmack_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'ESP_Mack_Drifter', self.colors['espmack'], 'espmack', 'ESP mack Mission', 
                                           self.espmack_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadESPbruce(self, stride=None):
        '''
        ESPbruce specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.espbruce_files], self.espbruce_files):
            url = self.espbruce_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           'espbruce', self.colors['espbruce'], 'espbruce', 'ESP bruce Mission', 
                                           self.espbruce_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadWFuctd(self, stride=None, platformName='WesternFlyer_UCTD', activitytypeName='Western Flyer Underway CTD Data'):
        '''
        WF uctd specific load functions.  Override defaults for @platformName and activitytypeName if it's desired
        to consider uctd and pctd coming from the same platform.  You may want to do this to use the data 
        visualization capabilities in STOQS.
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.wfuctd_files], self.wfuctd_files):
            url = self.wfuctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           platformName, self.colors['flyer'], 'ship', activitytypeName,
                                           self.wfuctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

        self.addPlatformResources('https://stoqs.mbari.org/x3d/flyer/flyer.x3d', platformName)

    def loadWFpctd(self, stride=None, platformName='WesternFlyer_PCTD', activitytypeName='Western Flyer Profile CTD Data'):
        '''
        WF pctd specific load functions. Override defaults for @platformName and activitytypeName if it's desired
        to consider uctd and pctd coming from the same platform.  You may want to do this to use the data 
        visualization capabilities in STOQS.
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a.split('.')[0] + getStrideText(stride) for a in self.wfpctd_files], self.wfpctd_files):
            url = self.wfpctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           platformName, self.colors['flyer'], 'ship', activitytypeName, 
                                           self.wfpctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)
        # Now load all the bottles           
        sl = SeabirdLoader('activity name', platformName, dbAlias=self.dbAlias, campaignName=self.campaignName, 
                           platformColor=self.colors['flyer'], dodsBase=self.wfpctd_base)
        if self.args.verbose:
            sl.logger.setLevel(logging.DEBUG)
        sl.tdsBase= self.tdsBase
        sl.process_btl_files(self.wfpctd_files)

    def loadRCuctd(self, stride=None, platformName='RachelCarson_UCTD', activitytypeName='Rachel Carson Underway CTD Data'):
        '''
        RC uctd specific load functions
        '''
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.rcuctd_files], self.rcuctd_files):
            url = self.rcuctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           platformName, self.colors['carson'], 'ship', activitytypeName, 
                                           self.rcuctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)

    def loadRCpctd(self, stride=None, platformName='RachelCarson_PCTD', activitytypeName='Rachel Carson Profile CTD Data'):
        '''
        RC pctd specific load functions
        '''
        stride = stride or self.stride
        #platformName = 'rc_pctd'
        for (aName, f) in zip([ a.split('.')[0] + getStrideText(stride) for a in self.rcpctd_files], self.rcpctd_files):
            url = self.rcpctd_base + f
            DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, 
                                           platformName, self.colors['carson'], 'ship', activitytypeName, 
                                           self.rcpctd_parms, self.dbAlias, stride, grdTerrain=self.grdTerrain)
        # load all the bottles           

        sl = SeabirdLoader(aName[:5], platformName, dbAlias=self.dbAlias, campaignName=self.campaignName, 
                           platformColor=self.colors['carson'], platformTypeName='ship', dodsBase=self.rcpctd_base)
        if self.args.verbose:
            sl.logger.setLevel(logging.DEBUG)
        sl.tdsBase= self.tdsBase
        sl.process_btl_files(self.rcpctd_files)

    # Dynamic method creation for any number of 'roms' platforms
    @staticmethod
    def make_load_roms_method(name):
        def _generic_load_roms(self, stride=None):
            # Generalize attribute value lookup
            plt_name = '_'.join(name.split('_')[1:])
            base = getattr(self, plt_name + '_base')
            files = getattr(self, plt_name + '_files')
            parms = getattr(self, plt_name + '_parms')
            start_datetime = getattr(self, plt_name + '_start_datetime')
            end_datetime = getattr(self, plt_name + '_end_datetime')

            stride = stride or self.stride
            for (aName, f) in zip([ a + getStrideText(stride) for a in files], files):
                url = os.path.join(base, f)
                try:
                    loader = DAPloaders.Trajectory_Loader(url = url,
                                        campaignName = self.campaignName,
                                        campaignDescription = self.campaignDescription,
                                        dbAlias = self.dbAlias,
                                        activityName = aName,
                                        activitytypeName = 'Simulated Glider/AUV Deployment',
                                        platformName = plt_name,
                                        platformColor = self.colors[plt_name],
                                        platformTypeName = 'simulated_trajectory',
                                        stride = stride,
                                        startDatetime = start_datetime,
                                        endDatetime = end_datetime,
                                        dataStartDatetime = None)
                except DAPloaders.OpendapError:
                    self.logger.info("Cannot open %s" % url)
                else:
                    loader.include_names = parms
                    loader.auxCoords = {}
                    loader.process_data()

        return _generic_load_roms

    def find_saildrone_urls(self, base, search_str, startdate, enddate):
        '''Use Thredds Crawler to return a list of DAP urls.  Initially written for LRAUV data, for
        which we don't initially know the urls.
        '''
        urls = []
        catalog_url = os.path.join(base, 'catalog.xml')
        c = Crawl(catalog_url, select=[search_str])
        d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
        for url in d:
            file_dt = datetime.strptime(url.split('-')[-4], '%Y%m%dT%H%M%S')
            if startdate < file_dt and file_dt < enddate:
                urls.append(url)
                self.logger.debug(f'* {url}')
            else:
                self.logger.debug(f'{url}')

        if not urls:
            raise FileNotFound('No urls matching "{search_str}" found in {catalog_url}')

        return urls

    def build_saildrone_attrs(self, platform_name, startdate, enddate, parameters, file_patterns):
        '''Set loader attributes for saildrone data
        '''
        setattr(self, platform_name + '_parms' , parameters)

        urls = []
        for year in range(startdate.year, enddate.year+1):
            base = f'http://odss.mbari.org/thredds/catalog/Other/routine/Platforms/Saildrone/1046/netcdf/'
            dods_base = f'http://odss.mbari.org/thredds/dodsC/Other/routine/Platforms/Saildrone/1046/netcdf/'
            try:
                urls += self.find_saildrone_urls(base, file_patterns, startdate, enddate)
                files = []
                for url in sorted(urls):
                    files.append(url.split('/')[-1])
            except FileNotFound as e:
                self.logger.debug(f'{e}')

        # Send signal that urls span years by not setting _base so that _urls is used instead
        if startdate.year == enddate.year:
            setattr(self, platform_name + '_base', dods_base)
        else:
            setattr(self, platform_name + '_urls', sorted(urls))

        setattr(self, platform_name + '_files', files)
        setattr(self, platform_name  + '_startDatetime', startdate)
        setattr(self, platform_name + '_endDatetime', enddate)

    def loadSaildrone(self, startdate=None, enddate=None, parameters=['SOG_FILTERED_MEAN',
                        'COG_FILTERED_MEAN', 'HDG_FILTERED_MEAN', 'ROLL_FILTERED_MEAN',
                        'PITCH_FILTERED_MEAN', 'UWND_MEAN', 'VWND_MEAN', 'WWND_MEAN',
                        'TEMP_AIR_MEAN', 'RH_MEAN', 'BARO_PRES_MEAN', 'PAR_AIR_MEAN',
                        'WAVE_DOMINANT_PERIOD', 'WAVE_SIGNIFICANT_HEIGHT', 'TEMP_SBE37_MEAN',
                        'SAL_SBE37_MEAN', 'O2_CONC_SBE37_MEAN', 'O2_SAT_SBE37_MEAN',
                        'CHLOR_WETLABS_MEAN',],
                      stride=None, file_patterns=('.*montereybay_mbari_2019_001-sd1046.*nc$'), build_attrs=False):
        '''First deployed for CANON May 2019 for DEIMOS campaigns
        '''
        platform_name = 'saildrone'
        activity_type_name = 'Saildrone Deployment'
        stride = stride or self.stride
        # Save these here in case we want to add them
        rbr_parms = ['TEMP_CTD_RBR_MEAN', 'SAL_RBR_MEAN', 'O2_CONC_RBR_MEAN', 'O2_SAT_RBR_MEAN',
                     'CHLOR_RBR_MEAN']

        if build_attrs:
            self.logger.info(f'Building load parameter attributes from crawling TDS')
            self.build_saildrone_attrs(platform_name, startdate, enddate, parameters, file_patterns)
        else:
            self.logger.info(f'Using load {pname} attributes set in load script')
            parameters = getattr(self, f'{platform_name}_parms')

        for (aName, f) in zip([ a.split('.')[0] + getStrideText(stride) for a in self.saildrone_files], self.saildrone_files):
            url = self.saildrone_base + f
            try:
                loader = DAPloaders.Trajectory_Loader(url = url,
                                    campaignName = self.campaignName,
                                    campaignDescription = self.campaignDescription,
                                    dbAlias = self.dbAlias,
                                    activityName = aName,
                                    activitytypeName = activity_type_name,
                                    platformName = platform_name,
                                    platformColor = self.colors[platform_name],
                                    platformTypeName = 'glider',
                                    stride = stride,
                                    startDatetime = startdate,
                                    endDatetime = enddate,
                                    dataStartDatetime = None)
            except webob.exc.HTTPError as e:
                self.logger.warn(f"Skipping over {url}")

            loader.include_names = parameters
            loader.auxCoords = {}
            for parm in parameters:
                loader.auxCoords[parm] = {'latitude': 'latitude', 'longitude': 'longitude', 'time': 'time', 'depth': 0.0}
                loader.plotTimeSeriesDepth = dict.fromkeys(parameters + [ALTITUDE, SIGMAT, SPICE], 0.0)
            try:
                loader.process_data()
            except (DAPloaders.OpendapError, IndexError) as e:
                self.logger.warn(f"Skipping over {url} due to Execption: {e}")

    def loadSubSamples(self):
        '''
        Load water sample analysis Sampled data values from spreadsheets (.csv files).  Expects to have the subsample_csv_base and
        subsample_csv_files set by the load script.
        '''
        ssl = SubSamplesLoader('', '', dbAlias=self.dbAlias)
        if self.args.verbose:
            ssl.logger.setLevel(logging.DEBUG)
        for csvFile in [ os.path.join(self.subsample_csv_base, f) for f in self.subsample_csv_files ]:
            ssl.logger.info("Processing subsamples from file %s", csvFile)
            try:
                ssl.process_subsample_file(csvFile, False)
            except IOError as e:
                ssl.logger.error(e)

    def loadParentNetTowSamples(self):
        '''
        Load Parent NetTow Samples. This must be done after CTD cast data are loaded and before subsamples are loaded.
        '''
        nt = NetTow()
        ns = Namespace()

        # Produce parent samples file, e.g.:
        # cd loaders/MolecularEcology/SIMZOct2013
        # ../../nettow.py --database stoqs_simz_oct2013 --subsampleFile 2013_SIMZ_TowNets_STOQS.csv \
        #                 --csvFile 2013_SIMZ_TowNet_ParentSamples.csv -v
        ns.database = self.dbAlias
        ns.loadFile = os.path.join(self.subsample_csv_base, self.parent_nettow_file)
        ns.purpose = ''
        ns.laboratory = ''
        ns.researcher = ''
        nt.args = ns
        try:
            nt.load_samples()
        except IOError as e:
            self.logger.error(e)

    def loadParentPlanktonPumpSamples(self, duration=10):
        '''
        Load Parent PlanktonPump Samples. This must be done after CTD cast data are loaded and before subsamples are loaded.
        duration is pumping time in minutes.
        '''
        pp = PlanktonPump()
        ns = Namespace()

        # Produce parent samples file, e.g.:
        # cd loaders/MolecularEcology/SIMZOct2013
        # ../../planktonpump.py --database stoqs_simz_oct2013 --subsampleFile SIMZ_2013_PPump_STOQS_tidy_v2.csv \
        #                       --csvFile 2013_SIMZ_PlanktonPump_ParentSamples.csv -v
        ns.database = self.dbAlias
        ns.load_file = os.path.join(self.subsample_csv_base, self.parent_planktonpump_file)
        ns.duration = duration
        ns.purpose = ''
        ns.laboratory = ''
        ns.researcher = ''
        pp.args = ns
        try:
            pp.load_samples()
        except IOError as e:
            self.logger.error(str(e))

    def find_lrauv_urls(self, base, search_str, startdate, enddate, date_intersect=True):
        '''Use Thredds Crawler to return a list of DAP urls.  Initially written for LRAUV data, for
        which we don't initially know the urls.
        '''
        INV_NS = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
        url = os.path.join(base, 'catalog.xml')
        self.logger.info(f"Crawling: {url}")
        skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$" ]
        u = urllib.parse.urlsplit(url)
        name, ext = os.path.splitext(u.path)
        if ext == ".html":
            u = urllib.parse.urlsplit(url.replace(".html", ".xml"))
        url = u.geturl()
        urls = []
        # Get an etree object
        r = requests.get(url)
        if r.status_code == 200:
            tree = etree.XML(r.text.encode('utf-8'))
        else:
            self.logger.debug(f"status_code != 200, Skipping {url}")
            return urls

        # Crawl the catalogRefs:
        for ref in tree.findall('.//{%s}catalogRef' % INV_NS):

            # get the mission directory name and extract the start and ending dates
            mission_dir_name = ref.attrib['{http://www.w3.org/1999/xlink}title']
            if '_' in mission_dir_name:
                dts = mission_dir_name.split('_')
                dir_start =  datetime.strptime(dts[0], '%Y%m%d')
                dir_end =  datetime.strptime(dts[1], '%Y%m%d')

                if date_intersect:
                    # Grab the valid urls for all log files in a .dlist directory that intersect the Campaign dates
                    if ( (startdate <= dir_start and dir_start <= enddate) or (startdate <= dir_end and dir_end <= enddate) ):
                        self.logger.debug(f'{mission_dir_name}: Collecting all log files matching {search_str} in this directory')
                        catalog = ref.attrib['{http://www.w3.org/1999/xlink}href']
                        c = Crawl(os.path.join(base, catalog), select=[search_str], skip=skips)
                        d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                        for url in d:
                            self.logger.debug(f'{url}')
                            urls.append(url)
                else:
                    # Grab the valid urls for .dlist directories encompasing the startdate and enddate for the Campaign
                    self.logger.debug(f'{mission_dir_name}: Looking for {search_str} files between {startdate} and {enddate}')
                    if dir_start >= startdate and dir_end <= enddate:
                        catalog = ref.attrib['{http://www.w3.org/1999/xlink}href']
                        c = Crawl(os.path.join(base, catalog), select=[search_str], skip=skips)
                        d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                        for url in d:
                            self.logger.debug(f'{url}')
                            urls.append(url)
            else:
                # Likely a realtime log - add to urls if only url date is between startdate and enddate
                catalog = ref.attrib['{http://www.w3.org/1999/xlink}href']
                c = Crawl(os.path.join(base, catalog), select=[search_str], skip=skips)
                d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                for url in d:
                    try:
                        dir_start =  datetime.strptime(url.split('/')[11], '%Y%m%dT%H%M%S')
                    except ValueError as e:
                        self.logger.warn(f"{e} from url = {url}")
                        self.logger.warn(f"Likely due to a log file found in the parent dir. Ignoring.")
                    if (startdate <= dir_start and dir_start <= enddate):
                        self.logger.debug(f'{url}')
                        urls.append(url)

        if not urls:
            raise FileNotFound('No urls matching "{}" found in {}'.format(search_str, os.path.join(base, 'catalog.html')))

        return urls

    def _get_mission_url(self, nc_str, mission_dir, mission_dods):
        soup = BeautifulSoup(urlopen(mission_dir).read(), 'lxml')
        for link in soup.find_all('a'):
            if nc_str in link.get('href'):
                mission_url = os.path.join(mission_dods, link.get('href'))
                self.logger.debug(f"Found mission {mission_url}")
                return mission_url

    def _scieng_file_state(self, log_url):
        '''Check other contents the associated .log file to test whether there really should be a .nc file.
        Return text indicating presence or reason why not. (Borrowed from lrauv-tools/handle-lrauv-logs/lrauv-data-file-audit.)
        '''
        not_creating_line = "ERROR .* Not creating"
        no_start_and_end = "WARNING .* Can't get start and end date from .nc4"
        with requests.get(log_url) as resp:
            if resp.status_code != 200:
                self.logger.error(f"Cannot read {log_url}, resp.status_code = {resp.status_code}")
                return 'log_file_missing'
            for line in (r.decode('utf-8') for r in resp.iter_lines()):
                self.logger.debug(f"{line}")
                if re.match(not_creating_line, line):
                    # Likely no variables available in .nc4 to produce the scieng.nc file
                    return 'missing_no_variables'
                if re.match(no_start_and_end, line):
                    # Likely no time_time variable in the scieng.nc file
                    return 'missing_no_time_time'

        return 'should_be_present'

    def find_lrauv_urls_by_dlist_string(self, dlist_str, platform, startdate, enddate, mission_year, nc_str='_2S_scieng.nc'):
        '''Crawl web accessible directories and search for missions that have dlist_str.
        Find all .dlist files and scan contents of the .dlist that has `dlist_str`.
        Return a list of those urls. This is called by build_lrauv_attrs() which needs 
        to do its work one year at a time. Add urls that fall within startdate and
        enddate, but do this only for one mission_year at a time, set by build_lrauv_attrs().
        '''
        urls = []
        file_base = f'http://dods.mbari.org/data/lrauv/{platform}/missionlogs/{mission_year}'
        dods_base = f'http://dods.mbari.org/opendap/data/lrauv/{platform}/missionlogs/{mission_year}'
        self.logger.info(f"Looking in {file_base} for .dlist files containing string '{dlist_str}'")
        soup = BeautifulSoup(urlopen(file_base).read(), 'lxml')
        for link in soup.find_all('a'):
            if '.dlist' in link.get('href'):
                dlist_dir = link.get('href').split('/')[-1].split('.')[0]
                dlist_url = os.path.join(file_base, f"{dlist_dir}.dlist")
                self.logger.debug(f"Cheking if {platform}/missionlogs/{startdate.year}/{dlist_dir}.dlist contains '{dlist_str}'")
                with requests.get(dlist_url) as resp:
                    if resp.status_code != 200:
                        self.logger.error(f"Cannot read {dlist_url}, resp.status_code = {resp.status_code}")
                        return
                    if dlist_str in resp.text:
                        self.logger.debug(f"Found a .dlist containing {dlist_str}: {dlist_dir}")
                        self.logger.debug(f"Searching uncommented directores in {dlist_url}")
                        for line in (r.decode('utf-8') for r in resp.iter_lines()):
                            self.logger.debug(f"{line}")
                            if not line.startswith('#'):
                                mission_dir = os.path.join(file_base, dlist_dir, line)
                                mission_dods = os.path.join(dods_base, dlist_dir, line)
                                url = self._get_mission_url(nc_str, mission_dir, mission_dods)
                                if url:
                                    dts = dlist_dir.split('_')
                                    dir_start =  datetime.strptime(dts[0], '%Y%m%d')
                                    dir_end =  datetime.strptime(dts[1], '%Y%m%d')
                                    # Grab the valid urls for all log files in a .dlist directory that fall within startdata and enddate
                                    if ( (startdate <= dir_start and dir_start <= enddate) or (startdate <= dir_end and dir_end <= enddate) ):
                                        self.logger.info(f"Adding {url} to urls list")
                                        urls.append(url)
                                else:
                                    # Check .log file contents to confirm that we expect a url (.nc file)
                                    log_url = self._get_mission_url(nc_str[:-2] + 'log', mission_dir, mission_dods)
                                    if log_url:
                                        log_reason = self._scieng_file_state(log_url)
                                        self.logger.debug(f"The .log file indication for .nc file: {log_reason}")
                                        if log_reason == 'should_be_present':
                                            self.logger.warn(f"Could not find {nc_str} file in {mission_dods}, it {log_reason}")
                                    else:
                                        self.logger.warning(f"Log directory {mission_dods} has no .log file from lrauvNc4ToNetcdf.py processing")
        return urls

    def build_lrauv_attrs(self, mission_year, platform, startdate, enddate, parameters, file_patterns,
                          dlist_str=None, err_on_missing_file=False, sbd_logs=False, cell_logs=False):
        '''Set loader attributes for each LRAUV platform. This is meant to be called for startdate
        and enddate being within a single year. It will fail if startdate and enddate span multiple
        years. We'd like to keep the files portion of the string short as it's the mouse-over text 
        in the UI
        '''

        base = f'http://dods.mbari.org/thredds/catalog/LRAUV/{platform}/missionlogs/{mission_year}/'
        dods_base = f'http://dods.mbari.org/opendap/data/lrauv/{platform}/missionlogs/{mission_year}/'
        if sbd_logs:
            base = f'http://dods.mbari.org/thredds/catalog/LRAUV/{platform}/realtime/sbdlogs/{mission_year}/'
            dods_base = f'http://dods.mbari.org/opendap/data/lrauv/{platform}/realtime/sbdlogs/{mission_year}/'
        # TODO: Add case for cell_logs
        setattr(self, platform + '_files', [])
        setattr(self, platform + '_base', dods_base)
        setattr(self, platform + '_parms' , parameters)

        urls = []
        try:
            if dlist_str:
                urls += self.find_lrauv_urls_by_dlist_string(dlist_str, platform,
                                                             startdate, enddate, mission_year)
            else:
                urls += self.find_lrauv_urls(base, file_patterns, startdate, enddate)
            files = []
            if len(urls) > 0:
                for url in sorted(urls):
                    if 'shore_i' in url:
                        file = '/'.join(url.split('/')[-3:])
                    else:
                        file = '/'.join(url.split('/')[-3:])
                    files.append(file)
                setattr(self, platform + '_files', files)

            setattr(self, platform  + '_startDatetime', startdate)
            setattr(self, platform + '_endDatetime', enddate)

        except urllib.error.HTTPError as e:
            self.logger.warn(f'{e}')
        except FileNotFound as e:
            if dlist_str:
                self.logger.warn(f'{e} for dlist_str = {dlist_str}')
            else:
                self.logger.warn(f'{e} between {startdate} and {enddate}')
            if err_on_missing_file:
                raise

    def _title_match(self, url, title_match):
        '''Customized for findinfind_dorado_urlsg urls produced by auv-python with proper metadata
        in dorado_info.py. Initially used to find all Dorado Monterey Bay Diamond
        missions that do not have 'REMOVE from analysis' in the comment.
        '''
        ds = xr.open_dataset(url)
        try:
            if title_match in ds.attrs['title']:
                return True
            else:
                return False
        except KeyError as e:
            self.logger.warn(f'{e} missing from {url}')
            return False

    def find_dorado_urls(self, base, search_str, startdate, enddate, title_match=""):
        '''Use Thredds Crawler to return a list of DAP urls.  Initially written for LRAUV data, for
        which we don't initially know the urls.
        '''
        urls = []
        catalog_url = os.path.join(base, 'catalog.xml')
        if isinstance(search_str, str):
            # Accommodate either string or Sequence in search_str
            search_str = [search_str]
        c = Crawl(catalog_url, select=search_str)
        d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
        for url in d:
            try:
                if 'Dorado389' in url:
                    # http://dods.mbari.org/thredds/dodsC/auv/dorado/2022/netcdf/Dorado389_2022_243_00_243_00_decim.nc
                    yyyy_yd = '_'.join(url.split('/')[-1].split('_')[1:3])
                elif 'dorado_' in url:
                    # http://dods.mbari.org/thredds/dodsC/auv/dorado/2022/netcdf/dorado_2022.243.00_1S.nc
                    yyyy_yd = '_'.join(url.split('/')[-1].split('_')[1].split('.')[:2])
                else:
                    self.logger.warning("Could not parse yyyy_yd from url = %s", url)
                    continue
                file_dt = datetime.strptime(yyyy_yd, '%Y_%j')
                sd = startdate.replace(hour=0, minute=0, second=0, microsecond=0)
                ed = enddate.replace(hour=0, minute=0, second=0, microsecond=0)
                if title_match:
                    self.logger.debug(f"Checking if '{title_match}' is in title of {url}")
                    if not self._title_match(url, title_match):
                        self.logger.debug(f"'{title_match}' NOT in title of {url}")
                        continue
                if sd <= file_dt and file_dt <= ed:
                    urls.append(url)
                    self.logger.debug(f'Using {url}')
                else:
                    self.logger.debug(f'{url}')
            except ValueError as e:
                self.logger.warning(f'ValueError: {e}')
                urls.append(f"Using {url}")

        if not urls:
            raise FileNotFound(f'No urls matching "{search_str}" found in {catalog_url}')

        return urls

    def build_dorado_attrs(self, platform, startdate, enddate, parameters, file_patterns, title_match=""):
        '''Set loader attributes for each Dorado vehicle
        '''
        setattr(self, platform + '_parms' , parameters)

        urls = []
        files = []
        for year in range(startdate.year, enddate.year+1):
            base = f'http://dods.mbari.org/thredds/catalog/auv/{platform}/{year}/netcdf/'
            # dods_base = f'http://dods.mbari.org:8181/opendap/data/auvctd/surveys/{year}/netcdf/'
            dods_base = f'http://dods.mbari.org/opendap/data/auvctd/surveys/{year}/netcdf/'
            try:
                self.logger.info(f'Searching for file_patterns = {file_patterns}')
                urls += self.find_dorado_urls(base, file_patterns, startdate, enddate, title_match)
                for url in sorted(urls):
                    files.append(url.split('/')[-1])
            except FileNotFound as e:
                self.logger.debug(f'{e}')

        if not files:
            if title_match:
                self.logger.warn(f"No files found with title_match = '{title_match}' for {platform} between {startdate} and {enddate} in {dods_base} using file_patterns = {file_patterns}")
            else:
                self.logger.warn(f"No files found for {platform} between {startdate} and {enddate} in {dods_base}")

        # Send signal that urls span years by not setting dorado_base so that dorado_urls is used instead
        if startdate.year == enddate.year:
            setattr(self, platform + '_base', dods_base)
        else:
            setattr(self, platform + '_urls', sorted(urls))

        setattr(self, platform + '_files', files)
        setattr(self, platform  + '_startDatetime', startdate)
        setattr(self, platform + '_endDatetime', enddate)

    def find_i2map_urls(self, base, search_str, startdate, enddate):
        '''Use Thredds Crawler to return a list of DAP urls.  Initially written for LRAUV data, for
        which we don't initially know the urls.
        '''
        urls = []
        catalog_url = os.path.join(base, 'catalog.xml')
        c = Crawl(catalog_url, select=[search_str])
        d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
        for url in d:
            try:
                # breakpoint()s don't work inside this loop, use debug()s to debug
                self.logger.debug(f'url = {url}')
                yyyy_yd = '_'.join(url.split('_')[1].split('.')[:2])
                self.logger.debug(f'yyyy_yd = {yyyy_yd}')
                file_dt = datetime.strptime(yyyy_yd, '%Y_%j')
                self.logger.debug(f'file_dt = {file_dt}')
                sd = startdate.replace(hour=0, minute=0, second=0, microsecond=0)
                ed = enddate.replace(hour=0, minute=0, second=0, microsecond=0)
                if sd <= file_dt and file_dt <= ed:
                    urls.append(url)
                    self.logger.debug(f'* {url}')
                else:
                    self.logger.debug(f'{url}')
            except ValueError:
                urls.append(url)

        if not urls:
            raise FileNotFound('No urls matching "{search_str}" found in {catalog_url}')
        return urls

    def build_i2map_attrs(self, platform, startdate, enddate, parameters, file_patterns):
        '''Set loader attributes to load auv-python processed i2map data
        '''
        setattr(self, platform + '_parms' , parameters)

        urls = []
        files = []
        for year in range(startdate.year, enddate.year+1):
            # i2map files are placed in dorado auvctd catalog
            base = f'http://dods.mbari.org/thredds/catalog/auv/dorado/{year}/netcdf/'
            dods_base = f'http://dods.mbari.org/opendap/data/auvctd/surveys/{year}/netcdf/'
            try:
                urls += self.find_i2map_urls(base, file_patterns, startdate, enddate)
                for url in sorted(urls):
                    files.append(url.split('/')[-1])
            except FileNotFound as e:
                self.logger.debug(f'{e}')

        if not files:
            self.logger.warn(f"No files found for {platform} between {startdate} and {enddate} in {dods_base}")

        # Send signal that urls span years by not setting i2map_base so that i2map_urls is used instead
        if startdate.year == enddate.year:
            setattr(self, platform + '_base', dods_base)
        else:
            setattr(self, platform + '_urls', sorted(urls))

        setattr(self, platform + '_files', files)
        setattr(self, platform  + '_startDatetime', startdate)
        setattr(self, platform + '_endDatetime', enddate)


if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    # Instance variable settings
    cl = CANONLoader('default', 'Test Load')
    cl.stride = 1000
    cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    cl.dorado_files = ['Dorado389_2010_300_00_300_00_decim.nc']

    # Execute the load
    cl.process_command_line()

    cl.loadAll()

