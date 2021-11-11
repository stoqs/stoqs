#!/bin/bash

# $Id: $

# Generate simulated decoded BED data files, convert to netCDF, 
# and copy to a place where they can be loaded into STOQS.
# Note: Visualization in STOQS is misleading. I think that the 
#       conversion from axis-angle to quaternion and then to 
#       Euler angles (roll, pitch, yaw) introduces axis flipping
#       and gymbol lock that you can see in the STOQS UI.

# Work in subdirector of BEDs/BEDs/Visualization/py/
cd simulated

../genBEDfile.py -o BED00_cycle_rot_axes_300_302.E00 -t ../MontereyCanyonBeds_1m+5m_profile.ssv --beg_depth 300 --end_depth 302 --cycle_rot_axes

../bed2netcdf.py -i BED00_cycle_rot_axes_300_302.E00 -o BED00_cycle_rot_axes_300_302_trajectory.nc --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --beg_depth 300 --end_depth 302 --title "Simulated BED cycling through rotations about X, Y, and Z axes between 300 and 302 m along thalweg" --summary "Data generated with: ../genBEDfile.py -o BED00_cycle_rot_axes_300_302.E00 -t ../MontereyCanyonBeds_1m+5m_profile.ssv --beg_depth 300 --end_depth 302 --cycle_rot_axes"


# Copy the netcdf files to CCE_Processed
scp BED00_cycle_rot_axes_300_302_trajectory.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED00/Simulated/netcdf

