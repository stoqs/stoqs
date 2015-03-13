# Sample Data #

  * `loaders/SampleLoader.py` has been updated with code to load sub sample data to be attached as children to the original parent water sample.
  * The Parameters selector has been split into Sampled Parameters and Measured Parameters selectors
  * All Sample data is displayed in a table under Sample Data Access when a sample icon is clicked in the Time-Depth plot

# Parameter Value queries #

  * Multiple parameters can now be selected and retrieved via the Measurement Data Access
  * The Show data values checkbox become active when one Platform and one Parameter is selected; if checked the server will create a color-filled contour plot and place it on top of the depth-time plot.
  * The Parameter Values section allows for filtering the data selection by click and dragging a selection on the histogram plot; multiple selections may be made. If Show data values is checked and a Parameter Values selection is made then the data values are shown with colored dots rather than with a color-filled contour plot.
  * The Show sensor tracks checkbox will display the selected Measured Parameter data values on the map based on the Depth, Time, Platform, and Parameter Value selections.
  * Clear Selection buttons have been added to each selection section
  * Radio buttons for X, Y, and Color have been added for each Parameter in preparation for adding parameter-parameter plot creation

# Example Screen Shot #

This screen shot shows Nitrate from Tethys plotted for sea\_water\_temperature values between 11.96  14.69 degrees Celsius:

[Full resolution image](http://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-02-06_at_10.57.12_PM.png)
![http://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-02-06_at_10.57.12_PM.png](http://stoqs.googlecode.com/hg/doc/Screen_Shot_2013-02-06_at_10.57.12_PM.png)