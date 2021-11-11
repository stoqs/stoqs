#!/bin/bash

# $Id: makeBEDNetCDF_CCE.sh 13835 2019-08-05 22:42:48Z mccann $

# For use on MBARI's internal network with appropriate credentials
# Execute on VM with:
#   cd BEDs/BEDs/Visualization/py
#   source venv-beds/bin/activate
#   ./makeBEDNetCDF_CCE.sh | tee makeBEDNetCDF_CCE_20190805.out     # e.g.

# From Cruise Plan: http://mww.mbari.org/expd/log/postcruise.asp?step=display&ExpeditionID=5326
# BED 1   MBARI   Kieft and BEDs team     202    36.796624   -121.822024 2-Oct   6-Oct   R/V Carson
# BED 2   MBARI   Kieft and BEDs team     295    36.793726   -121.846285 2-Oct   6-Oct   R/V Carson
# BED 3   MBARI   Kieft and BEDs team     390    36.795040   -121.869912 19-Oct  20-Oct  R/V Carson
# BED 4   MBARI   Kieft and BEDs team     520    36.791163   -121.904035 2-Oct   5-Oct   R/V Carson

# Actual
# ======
# BED 5 deployed at 388 m, see http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3873/00_29_56_03.html
# 388m, 36.795101, -121.868980 (Roberto: 387.5 m 40.5 bar, ...)
# Surveyed from Paragon 11 Jan 2016 - See email from Brian Kieft on 12 Jan 2016
# 406m (18 db + 388 m), 36.794,-121.879  
# Last pressure from 50200024 event: 42.258 bar (using 410 m from thalweg file)
# Events 50200054-50200057 recorded on 15 Jan 2016 Pressure from 42.523 bar to 44.793 bar, (use 413 m to 435 m from thalweg file)
# Individually:
#               50200054: 42.523 bar to 43.259 bar (413 m to 420 m)
#               50200055: 43.330 bar to 44.326 bar (420 m to 430 m)
#               50200056: 44.328 bar to 44.707 bar (430 m to 433 m)
#               50200057: 44.534 bar to 44.793 bar (433 m to 435 m)

# BED 3 deployed at 201 m, see http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3874/00_21_23_28.html
# 201 m, 36.796560, -121.822032 (Roberto: 187.5 m 21.149 bar, 0.387 bar at surface)

# BED 6 deployed at 521 m, see http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3870/00_15_38_23.html
# 521 m, 36.791129, -121.904350 (Roberto: 514.9 m 53.56 bar, 0.3 bar at surface)

# BED 3 re-deployed on 13 February 2016 from the Paragon: https://mww.mbari.org/expd/log/postcruise.asp?step=display&ExpeditionID=5501
# 299 m, 36.79339, -121.84625
# Event recorded on 17 February 2016
# Surveyed in BED #3 at 36.7947, -121.8483 at 306 m water depth at 1 March 2016 20:00 UTC. 

# BED 4 found by beach comber on 20 June 2016 - Have full download of 1 December 2015 event
# deployed at 294 m, -121.846283, 36.793713, see http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2015/vnta3872/00_17_50_24.html

# Copy data from the archive to a local working directory
mkdir decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED03/MBCCE_BED03_20151006_Event20160115/FullDownload/30200078.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20151005_Event20160115/FullDownload/60100068.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED05/MBCCE_BED05_20151027_Event20151201/decimated/50200024.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED03/MBCCE_BED03_20160212_Event20160217/decimated/30300004.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED05/MBCCE_BED05_20151027_Event20160115/decimated/5020005[4-7].E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED03/MBCCE_BED03_20160212_Event20160306/decimated/30300016.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED04/MBCCE_BED04_20151004_Event20151201/FullDownload/40100037.EVT.OUT" decoded

rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20160222_Event20160306/decimated/6020001[1-2].E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20160222_Event20160901/decimated/60200130.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED09/MBCCE_BED09_20160408_Event20160901/decimated/90100096.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED10/MBCCE_BED10_20160408_Event20160901/decimated/A0100096.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED10/MBCCE_BED10_20160408_Event20160901/fullDownload/A0100097.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED09/MBCCE_BED09_20160408_Event20161124/FullDownload/901001[5-6]?.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED03/MBCCE_BED03_20161005_Event20161124/decimated/30400015.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED10/MBCCE_BED10_20160408_Event20161124/decimated/A0100154.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED09/MBCCE_BED09_20160408_Event20170109/FullDownload/90100196.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/FullDownload/B0100026.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/FullDownload/B0100027.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/FullDownload/B0100028.EVT.OUT" decoded

rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/*/*.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED08/MBCCE_BED08_20161005_Event20170109/*/*.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED08/MBCCE_BED08_20161005_Event20170203/*/*.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED08/MBCCE_BED08_20161005_Event20170218/*/*.OUT" decoded

rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED11/MBCCE_BED11_20161010_Event20161124/decimated/B0100012.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20160222_Event20170109/decimated/6020021[8-9].E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED03/MBCCE_BED03_20161005_Event20170203/FullDownload/30400034.EVT.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20160222_Event20170203/decimated/60200236.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED06/MBCCE_BED06_20160222_Event20170218/decimated/60200246.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED04/MBCCE_BED04_20151004_Event20161124/decimated/40200014.E00.OUT" decoded
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED11/MBCCE_BED11_20161010_Event20170203/FullDownload/B010003[6-7].EVT.OUT" decoded
cd decoded

# Process all .EVT.OUT files to NetCDF from the event to floating on the surface of the ocean
##for f in *.EVT.OUT 
##do
##    ../bed2netcdf.py --input $f --lat 36.796560 --lon -121.822032 --depth 201 --title 'BED03 October 2015 Deployment for CCE' --seconds_offset 28800
##done

# Process the 1 km down canyon event from 1 December 2015 - decimated data received acoustically
# Correct 7 hour difference to make PDT GMT
# Iterate on setting --bar_offset so that altitude becomes close to 0 when/where we know the BED was on the bottom
../bed2netcdf.py -i 50200024.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED05 \
  --seconds_offset 25200 \
  --title 'BED05 Event Trajectory on 1 December 2015 during the Coordinated Canyon Experiment' 

# Process just the BED3 event as a trajectory floating up
# Correct 7 hour difference to make PDT GMT
../bed2netcdf.py -i 30200078.EVT.OUT -t ../BED03_Jan2016_event_30200078.csv \
  --bed_name BED03 \
  --seconds_offset 25200 \
  --title 'BED03 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment'

# Process just the BED6 event as a trajectory floating up
# Correct 7 hour difference to make PDT GMT
../bed2netcdf.py -i 60100068.EVT.OUT -t ../BED06_Jan2016_event_60100068.csv \
  --bed_name BED06 \
  --seconds_offset 25200 \
  --title 'BED06 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment'

# Re-deployed BED3 data recovered by the Waveglider, this time time is set to GMT
# thalweg data exatracted between 299 m and 308 m 
../bed2netcdf.py -i 30300004.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED03 \
  --seconds_offset 0 \
  --yaw_offset 210 \
  --title 'BED03 Event Trajectory on 17 February 2016 during the Coordinated Canyon Experiment'

# Process the event from 15 January 2016 - decimated data received acoustically
# Correct 7 hour difference to make PDT GMT
# Iterate on setting --bar_offset so that altitude becomes close to 0 when/where we know the BED was on the bottom
../bed2netcdf.py -i 50200054.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED05 \
  --seconds_offset 25200 \
  --title 'BED05 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment' 

../bed2netcdf.py -i 50200055.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED05 \
  --seconds_offset 25200 \
  --title 'BED05 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment' 

../bed2netcdf.py -i 50200056.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED05 \
  --seconds_offset 25200 \
  --title 'BED05 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment' 

../bed2netcdf.py -i 50200057.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED05 \
  --seconds_offset 25200 \
  --title 'BED05 Event Trajectory on 15 January 2016 during the Coordinated Canyon Experiment' 


# thalweg data exatracted between 308 m and 330 m 
../bed2netcdf.py -i 30300016.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED03 \
  --seconds_offset 0 \
  --title 'BED03 Event Trajectory on 6 March 2016 during the Coordinated Canyon Experiment'

# Process 1 December 2015 event recorded by BED04 - add 1.5 sec to 7 hour PDT time, bar_offset to make altitude 0 at start of event
../bed2netcdf.py -i 40100037.EVT.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED04 \
  --seconds_offset 25201.5 \
  --title 'BED04 Event Trajectory on 1 December 2015 during the Coordinated Canyon Experiment'

# Process 6 March 2016 event captured by BED06
../bed2netcdf.py -i 60200011.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED06 \
  --title 'BED06 Event Trajectory on 6 March 2016 during the Coordinated Canyon Experiment' 

../bed2netcdf.py -i 60200012.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED06 \
  --title 'BED06 Event Trajectory on 6 March 2016 during the Coordinated Canyon Experiment' 

# Process 1 September 2016 event captured by BEDs 6, 9, and 10
# beg_depth =~ 392 from "Paragon sonar" in MBCCE_Master_Locations_asofSept22_2016.xlsx 
../bed2netcdf.py -i 60200130.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED06 \
  --title 'BED06 Event Trajectory on 1 September 2016 during the Coordinated Canyon Experiment' 

# beg_depth =~ 185 from http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3922/02_56_04_12.html
#              197.9 from "Ventana depth" in MBCCE_Master_Locations_asofSept22_2016.xlsx (+12 m ???)
#              199 from Google Earth ROV Dive playback for vnta3922.kmz
../bed2netcdf.py -i 90100096.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED09 \
  --title 'BED09 Event Trajectory on 1 September 2016 during the Coordinated Canyon Experiment' 

# beg_depth =~ 283 from http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2016/vnta3921/02_05_37_16.html
#              275 from "Ventana depth" in MBCCE_Master_Locations_asofSept22_2016.xlsx (-8 m ???)
# 2-second event in A0100097.EVT.OUT has no pressure data and can't be processed by bed2netcdf.py
../bed2netcdf.py -i A0100096.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED10 \
  --title 'BED10 Event Trajectory on 1 September 2016 during the Coordinated Canyon Experiment' 

# Generate simulated BED data with pure rolling motion for verification of ROT_DIST calculation
# Originally created to test thalweg data, etc. Fails to finish when executed on 5 Aug 2019, uncomment to run again
##../genBEDfile.py -o BED00_SIM_rolling.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --use_today_as_start
##../bed2netcdf.py -i BED00_SIM_rolling.E00.OUT -o BED00_SIM_rolling_trajectory.nc -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
##  --beg_depth 145 --end_depth 722 --title 'Simulated BED data with pure rolling motion down the thalweg trace' \
##  --summary 'Data generated with: genBEDfile.py -o BED00_SIM_rolling.E00.OUT -t MontereyCanyonBeds_1m+5m_profile.ssv --use_today_as_start'

# Event on 24 November 2016 - FullDownload from BED09 found on beach on 9 January 2017
for f in 90100{156..164}.EVT.OUT
do
    ../bed2netcdf.py -i $f -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
    --bed_name BED09 \
    --title 'BED09 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
done
../bed2netcdf.py -i 90100165.EVT.OUT --lon -121.812626 --lat 36.799824 --depth 350.35 \
  --bed_name BED09 \
  --title 'BED09 Event on 24 November 2016 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i 30400015.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED03 \
  --title 'BED03 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i A0100154.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED10 \
  --yaw_offset 180 \
  --title 'BED10 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'

# Event on 9 January 2017 - FullDownload from BED09 found on beach on 9 January 2017 and BED11 attached to AMT
../bed2netcdf.py -i 90100196.EVT.OUT -t ../BED09_Jan2017event_90100196.ssv \
  --bed_name BED09 \
  --title 'BED09 Event Trajectory on 9 January 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i B0100026.EVT.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED11 \
  --title 'BED11 Event Trajectory on 9 January 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i B0100027.EVT.OUT --lon -121.812555 --lat 36.800003 --depth 329.3 \
  --bed_name BED11 \
  --title 'BED11 Event on 9 January 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i B0100028.EVT.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --bed_name BED11 \
  --title 'BED11 Event Trajectory on 9 January 2017 during the Coordinated Canyon Experiment'

# Simulate rotation about each axes to validate visualization of axis of rotation
../genBEDfile.py -o BED00_cycle_rot_axes_200_202.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
  --beg_depth 200 --end_depth 202 --cycle_rot_axes --use_today_as_start
../bed2netcdf.py -i BED00_cycle_rot_axes_200_202.E00.OUT -o BED00_cycle_rot_axes_200_202_trajectory.nc \
  --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --beg_depth 200 --end_depth 202 \
  --title "Simulated BED cycling through rotations about X, Y, and Z axes between 200 and 202 m along thalweg" \
  --summary "Data generated with: ../genBEDfile.py -o BED00_cycle_rot_axes_200_202.E00 -t ../MontereyCanyonBeds_1m+5m_profile.ssv --beg_depth 200 --end_depth 202 --cycle_rot_axes --use_today_as_start"

# BED08 Events (decimated) - kept here for comparison with full download
for f in 80200014.E00.OUT 80200016.E00.OUT 80200020.E00.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED08 \
      --title 'BED08 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
done
# BED08 Events (full) downloaded through WaveGlider Hotspot and after recovery, only one Pressure in 80200018.EVT.OUT - skip it
for f in 802000{14..17}.EVT.OUT 802000{19..20}.EVT.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED08 \
      --title 'BED08 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
done

for f in 80200034.E00.OUT 80200039.EVT.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED08 \
      --title 'BED08 Event Trajectory on 9 January 2017 during the Coordinated Canyon Experiment'
done
for f in 80200046.E00.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED08 \
      --title 'BED08 Event Trajectory on 3 February 2017 during the Coordinated Canyon Experiment'
done
for f in 80200050.E00.OUT 80200052.EVT.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED08 \
      --title 'BED08 Event Trajectory on 18 February 2017 during the Coordinated Canyon Experiment'
done

# Roberto's email on 12 April 2017 informing me of newly available event data
../bed2netcdf.py -i B0100012.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED11 \
  --title 'BED11 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
for f in 60200218.E00.OUT 60200219.E00.OUT
do
    ../bed2netcdf.py --input $f --trajectory ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED06 \
      --title 'BED06 Event Trajectory on 9 January 2017 during the Coordinated Canyon Experiment'
done
../bed2netcdf.py -i 30400034.EVT.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED03 \
  --title 'BED03 Event Trajectory on 3 February 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i 60200236.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED06 \
  --title 'BED06 Event Trajectory on 3 February 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i 60200246.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED06 \
  --title 'BED06 Event Trajectory on 18 February 2017 during the Coordinated Canyon Experiment'

# In response to Brian Kieft's email of 2 August 2017
../bed2netcdf.py -i 40200014.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED04 \
  --title 'BED04 Event Trajectory on 24 November 2016 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i B0100036.EVT.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv --bed_name BED11 \
  --title 'BED11 Event Trajectory on 3 February 2017 during the Coordinated Canyon Experiment'
../bed2netcdf.py -i B0100037.EVT.OUT --lon -121.812566 --lat 36.799986 --depth 331.77 --bed_name BED11 \
  --title 'BED11 Event on 3 February 2017 during the Coordinated Canyon Experiment'

# Copy the netcdf files to CCE_Processed
scp 50200024_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED05/MBCCE_BED05_20151027_Event20151201/netcdf
scp 30200078_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED03/20151001_20160115/netcdf
scp 60100068_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/20151001_20160115/netcdf
scp 30300004_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED03/MBCCE_BED03_20160212_Event20160217/netcdf
scp 5020005{4..7}_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED05/MBCCE_BED05_20151027_Event20160115/netcdf
scp 30300016_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED03/MBCCE_BED03_20160212_Event20160306/netcdf
scp 40100037_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED04/MBCCE_BED04_20151004_Event20151201/netcdf

scp 6020001{1..2}_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/MBCCE_BED06_20160222_Event20160306/netcdf
scp 60200130_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/MBCCE_BED06_20160222_Event20160901/netcdf
scp 90100096_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Event20160901/netcdf
scp A0100096_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED10/MBCCE_BED10_20160408_Event20160901/netcdf

# Uncomment to copy - gen script fails on 5 Aug 2019
##scp BED00_SIM_rolling.E00.OUT mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED00/Simulated/decimated
##scp BED00_SIM_rolling_trajectory.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED00/Simulated/netcdf

scp 90100{156..162}_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Event20161124/netcdf
scp 90100164_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Event20161124/netcdf
scp 90100165_full.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Event20161124/netcdf
scp 30400015_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED03/MBCCE_BED03_20161005_Event20161124/netcdf
scp A0100154_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED10/MBCCE_BED10_20160408_Event20161124/netcdf

scp 90100196_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Event20170109/netcdf
scp B0100026_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/netcdf
scp B0100027_full.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/netcdf
scp B0100028_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20170109/netcdf

scp BED00_cycle_rot_axes_200_202.E00.OUT mccann@elvis.shore.mbari.org:/mbari/CCE_Archive/BEDs/BED00/Simulated/decimated
scp BED00_cycle_rot_axes_200_202_trajectory.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED00/Simulated/netcdf

scp 80200014_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/netcdf
scp 80200016_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/netcdf
scp 80200020_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/netcdf
scp 802000{14..17}_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/netcdf
scp 802000{19..20}_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20161124/netcdf
scp 80200034_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20170109/netcdf
scp 80200039_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20170109/netcdf
scp 80200046_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20170203/netcdf
scp 80200050_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20170218/netcdf
scp 80200052_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED08/MBCCE_BED08_20161005_Event20170218/netcdf

scp B0100012_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20161124/netcdf
scp 6020021[8-9]_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/MBCCE_BED06_20160222_Event20170109/netcdf
scp 30400034_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED03/MBCCE_BED03_20161005_Event20170203/netcdf
scp 60200236_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/MBCCE_BED06_20160222_Event20170203/netcdf
scp 60200246_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED06/MBCCE_BED06_20160222_Event20170218/netcdf

scp 40200014_decim_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED04/MBCCE_BED04_20151004_Event20161124/netcdf
scp B0100036_full_traj.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20170203/netcdf
scp B0100037_full.nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED11/MBCCE_BED11_20161010_Event20170203/netcdf

# Clean up 
##cd ..
##rm -r decoded

