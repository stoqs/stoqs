Instructions for creating terrain files for 3D spatial data visualization in STOQS
==================================================================================

### GeoElevationGrid

1. Execute script in mapping@elvis:/mbari/TerrainData/scripts to create .wrl or .x3dv file
2. Edit resulting file keeping heights and making it X3D:

```
<scene>
<shape>
    <Appearance>
        <Material diffuseColor='0.7 0.7 0.7'/>
    </Appearance>
    <GeoElevationGrid colorPerVertex='true' creaseAngle='3.14' geoGridOrigin='36 -122 0' geoSystem='"GD" "WE"' solid='false' xDimension='1438' xSpacing='0.0005057477' yScale='10' zDimension='1224' zSpacing='0.0005058092' normalPerVertex='true' ccw='true' containerField='geometry' height='-2403.4 ....'>
    </GeoElevationGrid>
</shape>
</scene>
```


### X3DOM popGeometry or SRC from a GMT .grd file:

1. Start with a GMT .grd bathymetry file such as that produced by an mbgrid(1) execution

2. Convert to an xyz .asc "point cloud", apply 10x vertical exaggeration, convert to Earth Centered Earth Fixed coordinate system, e.g.:

   a. Geocentric - no GeoOrigin:

        grd2xyz Monterey25.grd --D_FORMAT=%f | sed '/NaN/d' | awk '{print $1, $2, 10 * $3}' | mapproject -E > Monterey25_10x.asc

   b. With a GeoOrigin:

        echo -121 36 0 | mapproject -E --D_FORMAT=%f      # -2660686.065357 -4428125.227549 3728191.675831
        grd2xyz MontereyCanyonBeds_1m+5m.grd --D_FORMAT=%f | sed '/NaN/d' | awk '{print $1, $2, 10 * $3}' | mapproject -E --D_FORMAT=%f | \
          awk '{print $1 - -2660686.065357, $2 - -4428125.227549, $3 - 3728191.675831}' > MontereyCanyonBeds_1m+5m_10x_GeoOrigin_-121_36_0.asc

3. Use Meshlab to construct a surface from the .asc file and save it as a Stanford .ply file.  You need to use Meshlab interactively
   to load the .asc mesh, construct Normals and a surface, and clean it up before saving as a .ply or .x3d file.  Here are the
   suggested steps relevent to Meshlab_64bit v1.3.3 on a Mac:

        File -> Import Mesh...                                      (Select .asc file produced in step 1 using defaults on the dialog)
        Filters -> Point Set -> Compute normals for point set       (Use defaults on dialog)
        Filters -> Point Set -> Surface Reconstruction Poisson      (Set Octree Depth to 11 and Solver Divide to 10)
        Wait a serveral minutes (There is no progress bar displayed)
        Filters -> Sampling -> Mesh Element Subsampling             (Subsampling by about a factor of 2 maintains fidelity and helps reduce
                                                                 spurious faces. Subsample more to reduce the number of triangles.)
        Select the Sampled Mesh layer
        Filters -> Point Set -> Surface Reconstruction Poisson      (Set Octree Depth to 11 and Solver Divide to 10)
        Clean the new mesh by selecting face outside of the original point cloud and deleting them. (The Poisson reconstruction
        expects to create a closed surface and the extrapolated faces need to be removed.)
        File -> Export Mesh As...                                   (Pick an appropriate .ply name and have only Face Normal selected in the dialog)

   There are several good Meshlab video tutorials online that will help you understand how to use the UI.

   Here's another Meshlab set of operations that rendered a high quality mesh for 1m+5m bathymetry data for Monterey Canyon:

        Load .asc file
        Sampling -> Poisson-disk Sampling (to reduce number of vertices from 49,879,075 to 20,000,000)
        Point Sets -> Compute normals for point sets
        Surface Reconstruction: Poisson (Octree Depth: 12, Solver Divide: 10)
        Remeshing, Simplification and Reconstruction -> Quadric Edge Collapse Decimation:
                - Preserve Normal
                - Preseve Topology
                - Optimal Position of Simplified Vertices
                - Planar Simplification
                - Post-simplification cleaning
        Cleanup (with plenty of intermediate saves)
        Smoothing ... -> Laplacian smooth (surface preserve)
        Export mesh to .ply

4. Use InstantReality aopt tool to "flatten" the Scene and create popGeometry, e.g.:

        mkdir /Users/mccann/Downloads/binGeo -or- remove files in /Users/mccann/Downloads/binGeo
        ./aopt -i /Users/mccann/Downloads/Monterey25_10x-clean.ply -F Scene -b /Users/mccann/Downloads/Monterey25_10x-opt.x3db
        ./aopt -i /Users/mccann/Downloads/Monterey25_10x-opt.x3db -f PrimitiveSet:creaseAngle:4 -V -K "/Users/mccann/Downloads/binGeo/:ib" -N /Users/mccann/Downloads/Monterey25_10x.html

5. Copy the X3D <scene> element and its contents from the generated .html file into a .x3d file and put it along with the the associated files 
   in binGeo to the stoqs/static/x3d directory.  Replace the paths to the binGeo files with what works on the stoqs server, e.g.:

        :%s#/Users/mccann/Downloads/binGeo#/stoqs/static/x3d/Monterey25/binGeo#g

6. Test that the STOQS UI displays the new mesh in the Spatial -> 3D tab.

7. With X3DOM 1.6 and later and at least aopt V2.6.0 we can generate more efficient SRC instead of popGeometry, so instead of the last step in 3 do:

        cd /Users/mccann/Downloads/
        aopt -i Monterey25_10x-opt.x3db -f PrimitiveSet:creaseAngle:4 -V -Y "nodeType(Geometry)" -N Monterey25_10x_src.html

    Edit Monterey25_10x_src.html:

    - Add 'SRC/' to the url path for the .src files.

    - Change aopt's <material> node from:
        ```
        <material diffuseColor='0.6 0.6 0.6' specularColor='0.6 0.6 0.6'></material>
        ```
      to:
        ```
        <material diffuseColor='0.7 0.7 0.7' specularColor='0.1 0.1 0.1'></material>
        ```

    Copy Monterey25_10x_src.html to Monterey25_10x_src_scene.x3d and edit:

    - Remove surrounding elements from the <scene> tags
    - Edit in the FQDN for the urls so that Django will load it.
    - Remove <viewpoint> node that aopt added

