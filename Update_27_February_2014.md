# Programmatic Access to STOQS Data #

The STOQS platform may be used to create visualizations such as this one that was [presented at the 2014 Ocean Sciences Meeting](http://www.eposters.net/poster/using-stoqs-for-analysis-and-visualization-of-biological-oceanography-data-2) in Honolulu on 27 and 28 February 2014 showing correlations of chlorophyll fluorescence and optical backscatter from 4 autonomous platforms plying the waters of Monterey Bay:

<a href='http://www.youtube.com/watch?feature=player_embedded&v=5IYS-UTD_XA' target='_blank'><img src='http://img.youtube.com/vi/5IYS-UTD_XA/0.jpg' width='425' height=344 /></a>

[Download video for playback in video player on your system](https://odss.mbari.org/data/canon/2013_Sep/Products/AUV_Gliders/stoqs_september2013_tethys_daphne_slocums_Fl_vs._bb__red_.m4v) (useful for "scrubbing" the video back and forth and visualizing the patterns).

Here are instructions for how you can create similar visualizations for any data from STOQS databases:

  1. Log on to a Linux system (you can install one for free on your PC or Mac computer, read below the fold at http://www.pgbovine.net/cde.html)
  1. Find out the word length of your system with a 'uname -a' command at a shell prompt. A 32-bit system will respond with something like "... i386 GNU/Linux", a 64-bit system will respond with something like "... x86\_64 GNU/Linux". The following steps are for a 32-bit system (you would download the appropriate file for your system).
  1. Change directory to an appropriate work place and download stoqs\_biplots\_32bit.tar.gz file from https://odss.mbari.org/data/canon/2013_Sep/Applications/, e.g. 'cd /tmp && wget "https://odss.mbari.org/data/canon/2013_Sep/Applications/stoqs_biplots_32bit.tar.gz"'
  1. Unpack, e.g. 'zcat stoqs\_biplots\_32bit.tar.gz | tar xvf -'
  1. Change directory to cde-package and read the README\_CDE file
  1. The usage note for the trajectory\_biplots.py.cde script shows the exact command used to generate the images for the video shown above:
```
./trajectory_biplots.py.cde -d stoqs_september2013 -p tethys Slocum_294 daphne Slocum_260 -x bb650 optical_backscatter660nm bb650 optical_backscatter700nm -y chlorophyll fluorescence chlorophyll fluorescence --plotDir /tmp --plotPrefix stoqs_september2013_ --hourStep 1 --hourWindow 2 --xLabel '' --yLabel '' --title 'Fl vs. bb (red)' --minDepth 0 --maxDepth 100

Saving to file /tmp/stoqs_september2013_Fl_vs._bb__red__20130909T0100.png
Saving to file /tmp/stoqs_september2013_Fl_vs._bb__red__20130909T0200.png
Saving to file /tmp/stoqs_september2013_Fl_vs._bb__red__20130909T0300.png
...
```

Note: Direct access to the PostgreSQL data is required by trajectory\_biplots.py. The database specified in the privateSettings file may be behind a firewall - establish a VPN or edit privateSettings to point to a STOQS database that you have access to.

# Live STOQS User Interface video #

Video with audio track showing interaction with the STOQS UI - the video ends with a copy of sample SQL code that selects the data used to make the visualization shown above:

<a href='http://www.youtube.com/watch?feature=player_embedded&v=Vq_9sCGCt0s' target='_blank'><img src='http://img.youtube.com/vi/Vq_9sCGCt0s/0.jpg' width='425' height=344 /></a>