/** @namespace x3dom.nodeTypes */
/*
 * X3DOM JavaScript Library
 * http://www.x3dom.org
 *
 * (C)2009 Fraunhofer IGD, Darmstadt, Germany
 * Dual licensed under the MIT and GPL
 */

/* ### GeoOriginTransform ### */
x3dom.registerNodeType(
    "GeoOriginTransform",
    "Geospatial",
    defineClass(x3dom.nodeTypes.X3DTransformNode,
        
        /**
         * Constructor for GeoOriginTransform
         * @constructs x3dom.nodeTypes.GeoOriginTransform
         * @x3d 4.0
         * @component Geospatial
         * @status experimental
         * @extends x3dom.nodeTypes.X3DTransformNode
         * @param {Object} [ctx=null] - context object, containing initial settings like namespace
         * @classdesc The GeoLocation node provides the ability to geo-reference any standard X3D model.
         * That is, to take an ordinary X3D model, contained within the children of the node, and to specify its geospatial location.
         * This node is a grouping node that can be thought of as a Transform node.
         * However, the GeoLocation node specifies an absolute location, not a relative one, so content developers should not nest GeoLocation nodes within each other.
         */
        function (ctx) {
            x3dom.nodeTypes.GeoLocation.superClass.call(this, ctx);

            /**
             * The geometry of the nodes in children is to be specified in units of metres in X3D coordinates relative to the location specified by the geoCoords field.
             * The geoCoords field can be used to dynamically update the geospatial location of the model.
             * @var {x3dom.fields.SFBool} onlyYUp
             * @memberof x3dom.nodeTypes.GeoOriginTransform
             * @initvalue false
             * @field x3dom
             * @instance
             */
            this.addField_SFBool(ctx, 'onlyYUp', false);

            /**
             * The geoOrigin field is used to specify a local coordinate frame for extended precision.
             * @var {x3dom.fields.SFNode} geoOrigin
             * @memberof x3dom.nodeTypes.GeoOriginTransform
             * @initvalue x3dom.nodeTypes.GeoOrigin
             * @field x3dom
             * @instance
             */
            this.addField_SFNode('geoOrigin', x3dom.nodeTypes.GeoOrigin);
        },

        {
            nodeChanged: function()
            {
                // similar to what transform in Grouping.js does
                // var position = this._vf.geoCoords;
                // var geoSystem = this._vf.geoSystem;
                var geoOrigin = this._cf.geoOrigin; // gets only populated if in nodeChanged()

                //this._trafo =  this.getGeoTransRotMat(geoSystem, geoOrigin, position);
                this._trafo =  this.getGeoTransRotMat(geoOrigin);
            },
        
            getGeoRotMat: function (geoSystem, positionGC)
            {
                //returns transformation matrix to align coordinate system with geoposition as required:
                //2 rotations to get required orientation
                //Up (Y) to skywards, and depth (-Z) to North
                //1) around X to point up by
                //angle between Z and new up plus 90
                //(angle between Z and orig. up)
                //2) around Z to get orig. up on longitude

                var coords = new x3dom.fields.MFVec3f();
                coords.push(positionGC);
                var positionGD = x3dom.nodeTypes.GeoCoordinate.prototype.GCtoGD(geoSystem, coords)[0];
                
                var Xaxis = new  x3dom.fields.SFVec3f(1,0,0);
                var rotlat = 180 - positionGD.y; // latitude
                var deg2rad = Math.PI/180;
                var rotUpQuat = x3dom.fields.Quaternion.axisAngle(Xaxis, rotlat*deg2rad);

                var Zaxis = new x3dom.fields.SFVec3f(0,0,1);
                var rotlon = 90 + positionGD.x;// 90 to get to prime meridian;
                var rotZQuat = x3dom.fields.Quaternion.axisAngle(Zaxis, rotlon*deg2rad);

                //return rotZQuat.toMatrix().mult(rotUpQuat.toMatrix();
                return rotZQuat.multiply(rotUpQuat).toMatrix();

            },

            getGeoTransRotMat: function (geoOrigin)
            {
                // accept geocoords, return translation/rotation transform matrix
                // var coords = new x3dom.fields.MFVec3f();
                // coords.push(position);

                // var transformed = x3dom.nodeTypes.GeoCoordinate.prototype.GEOtoGC(geoSystem, geoOrigin, coords)[0];
                // var rotMat = this.getGeoRotMat(geoSystem, transformed);
                // account for geoOrigin with and without rotateYUp
                if (geoOrigin.node)
                {
                    var origin = x3dom.nodeTypes.GeoCoordinate.prototype.OriginToGC(geoOrigin);
                    if(geoOrigin.node._vf.rotateYUp)
                    {
                        // inverse rotation after offset
                        var rotMatOrigin = this.getGeoRotMat(geoOrigin.node._vf.geoSystem, origin);
                        if (this._vf.onlyYUp) {
                            return rotMatOrigin.inverse();    
                        }
                        return rotMatOrigin.inverse().mult(x3dom.fields.SFMatrix4f.translation(origin.negate()));
                    }
                    //translate; 
                    return x3dom.fields.SFMatrix4f.translation(origin.negate());
                }
                else
                // no GeoOrigin: do nothing, eg. identity
                
                {
                    //return x3dom.fields.SFMatrix4f.translation(transformed).mult(rotMat);
                    return x3dom.fields.SFMatrix4f.identity();;
                }
            },

            //mimic what transform node does
            fieldChanged: function (fieldName)
            {
                if (fieldName == "onlyYUp" ||
                    fieldName == "geoOrigin")
                {
                    //var position = this._vf.geoCoords;
                    //var geoSystem = this._vf.geoSystem;
                    var geoOrigin = this._cf.geoOrigin;
                    this._trafo =  this.getGeoTransRotMat(geoOrigin);

                    this.invalidateVolume();
                    //this.invalidateCache();
                }
                else if (fieldName == "render") {
                    this.invalidateVolume();
                    //this.invalidateCache();
                }
            }
            //deal with geolocation in geolocation here? behaviour is undefined in spec

        }
    )
);
