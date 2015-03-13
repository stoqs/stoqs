# Parameter-Parameter visualization #

The STOQS user interface has been updated with the capability to create correlation plots amongst co-located measurements. Here are brief instructions for using the new feature:

  1. Expand the Measured Parameters section by clicking on the text
  1. Select a Parameter name or platform to enable candidate parameters for comparison
  1. Select Parameters for Parameter-Parameter correlation via the radio buttons in the X, Y, Z, and Color columns
  1. Once X and Y columns are selected the Parameter-Parameter -> 2D tab will expand with a correlation plot and its linear regression parameters
  1. The points may be colored by a third Parameter by making a selection in the Color column
  1. Sampled Parameters (results of laboratory analyses) may also be correlated against Measured Parameters

Here is a screen shot of a 2D correlation plot (the Spatial and Temporal sections have been collapsed to maximize use of browser window space). Note that if Parameters with standard\_names of sea\_water\_salinity and sea\_water\_temperature are selected for X and Y, then contours of sigma-t are also plotted:

[Full resolution image](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.54.31_PM.png)
![https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.54.31_PM.png](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.54.31_PM.png)

If a Z column is selected an interactive 3D plot will appear in the Parameter-Parameter -> 3D tab. Here is an example screen shot:

[Full resolution image](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.47.43_PM.png)
![https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.47.43_PM.png](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.47.43_PM.png)

# Geospatial 3D Visualization #

Measured Parameter trajectory data may be visualized on the Temporal -> Depth plot as time series sections by selecting a Parameter name and checking the boxes under the plot. The data may also be plotted as "sensor tracks" in Spatial -> Map. The data may also be visualized in Geospatial 3D by checking the box in the Spatial -> 3D tab. This uses the experimental Geospatial component of the X3DOM library. It's implementation in STOQS is also experimental. Comments are welcomed. Here is a screen shot of some data in San Pedro Basin from the March 2013 campaign:

[Full resolution image](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.57.37_PM.png)
![https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.57.37_PM.png](https://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-04-22_at_04.57.37_PM.png)