## About STOQS ##
STOQS (Spatial Temporal Oceanographic Query System) is a geospatial database software package designed for providing efficient access to in situ oceanographic measurement data. This efficient data access capability enables development of advanced visualization and analysis tools. One of them in wide use is a web-based user interface that follows Ben Shneiderman’s mantra (Overview first, zoom and filter, then details-on-demand) for exploring collections of observational data.

Here's a short video giving the context in which STOQS is used:

<a href='http://www.youtube.com/watch?feature=player_embedded&v=E8wO3qMevV8' target='_blank'><img src='http://img.youtube.com/vi/E8wO3qMevV8/0.jpg' width='425' height=344 /></a>

## Use Case ##
**Precondition:**

Observational data from a variety of platforms (Autonomous Underwater Vehicles, gliders, moorings, drifters, shipboard systems)
are individually available from OPeNDAP servers.

**Goal:**

Retrieve data by parameter name across all platforms in a specific area over a
specific span of time

## Data Management Niche ##
STOQS complements other data management technologies
such as NetCDF and OPeNDAP by providing an ability to index data retrieval
across parameter and spatial dimensions in addition to the _a priori_ indexed
coordinate dimensions of CF-NetCDF.  It also provides a functional bridge between
NetCDF and Geographic Information Systems technologies.

## Operation ##
After installation, data is loaded into a STOQS database from a variety of data sources,
including OPeNDAP data sets, other relational databases, and flat files.
Products are delivered in numerous formats, including KML, X3D, WMS, CSV, and HTML via REST-style
web requests. Programmatic access is possible through direct SQL queries. STOQS is used at the Monterey Bay Aquarium Research Institute for data management, visualization, and analysis of a wide assortment of _in situ_
measurement data. A web-based user interface permits a user to follow [Ben Shneiderman's mantra](http://www.infovis-wiki.net/index.php/Visual_Information-Seeking_Mantra) (Overview first, zoom and filter, then details-on-demand) in exploring a collection of data:

Here's a short video showing how to use the User Interface:

<a href='http://www.youtube.com/watch?feature=player_embedded&v=Vq_9sCGCt0s' target='_blank'><img src='http://img.youtube.com/vi/Vq_9sCGCt0s/0.jpg' width='425' height=344 /></a>

## Example Web Site ##
The MBARI Oceanographic Decision Support System hosts http://odss.mbari.org/canon/default/query/ to provide access to upper water column _in situ_ measurement data collected as part of the Controlled, Agile and Novel Observing Network (CANON) inititative. Click on "Campaign list" to explore some large data collections, please also exoplore the Wiki postings on this site.

## Installation ##
STOQS is 100% open source software. If you wish to investigate using it for your data start by following the instructions in the [README](http://code.google.com/p/stoqs/source/browse/README) file.

## Acknowledgments ##
Development of the STOQS software is supported at MBARI with funding from the David and Lucile Packard Foundation