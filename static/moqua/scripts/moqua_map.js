function MoquaMap(lasServer) {

	var self = new DynamicMap("mapDiv", "inputNorth", "inputWest", "inputSouth", "inputEast", moqua.rangeCheck)
	self.setViewSize(160,245);
	self.setView(37.445,-123.046,36.006,-121.267);
	self.setMap(lasServer + "/classes/gifs/monterey_big.jpg",38.0,-125.5,35.0,-119.5,751,1501);
	self.setSelection(36.989,-122.174,36.526,-121.762);
	return self;
}	

function DynamicMap(divId,
					northTextId, westTextId, southTextId, eastTextId,
					callback) {

	// Static map GUI variables
	this.divId = divId;
	this.callback = callback;

	this.borderId = "mapBorder";
	this.imageId = "mapImage";
	this.overlayId = "overlayImage";
	this.busyId = "busyImage";
	this.viewId = "mapView";
	this.northId = "selectNorth";
	this.westId = "selectWest";
	this.southId = "selectSouth";
	this.eastId = "selectEast";
	this.northwestId = "selectNorthWest";
	this.northeastId = "selectNorthEast";
	this.southwestId = "selectSouthWest";
	this.southeastId = "selectSouthEast";
	this.northTextId = northTextId;
	this.westTextId = westTextId;
	this.southTextId = southTextId;
	this.eastTextId = eastTextId;

	// Semi-Static map variables
	this.mapImageUrl = "";
	this.mapNorth = null;
	this.mapWest = null;
	this.mapSouth = null;
	this.mapEast = null;
	this.mapImageWidth = null;
	this.mapImageHeight = null;
	
	// Semi-Static map view variables
	this.viewHeight = null;
	this.viewWidth = null;
	
	// Dynamic map view variables
	this.viewNorth = null;
	this.viewWest = null;
	this.viewSouth = null;
	this.viewEast = null;
	
	// Dynamic Map variables derived from view
	this.mapTop = null;
	this.mapLeft = null;
	this.mapHeight = null;
	this.mapWidth = null;
	
	// Dynamic Overlay variables
	this.overlayTop = null;
	this.overlayLeft = null;
	
	// Dynamic selection variables
	this.selNorth = null;
	this.selWest = null;
	this.selSouth = null;
	this.selEast = null;
	
	// Dynamic selection variables derived from selection
	this.selTop = null;
	this.selLeft = null;
	this.selBottom = null;
	this.selRight = null;
	
	// Other gui variables
	this.mapUnderMouse = false;

	// Initialization
	this.divElement = document.getElementById(divId);
	this.divElement.innerHTML = '<div id="mapBorder"> </div> ' + // onmouseover="moquaMap.mouseOver(event)" onmouseout="moquaMap.mouseOut(event)" ondragstart="moquaMap.dragStart(event)" onselectstart="selectStart(event)" 
                            '<img id="mapImage" /> ' +
                            '<img id="overlayImage" src=""/> ' +
                            '<img id="busyImage" src="images/busy.gif">' +
                            '<div id="mapView" > </div> ' + 
                            '<img id="selectNorth" src="images/hline.gif" /> ' +
                            '<img id="selectWest" src="images/vline.gif" /> ' +
                            '<img id="selectSouth" src="images/hline.gif" /> ' +
                            '<img id="selectEast" src="images/vline.gif" /> ' +
                            '<img id="selectNorthWest" src="images/corner.gif" /> ' +
                            '<img id="selectNorthEast" src="images/corner.gif" /> ' +
                            '<img id="selectSouthWest" src="images/corner.gif" /> ' +
                            '<img id="selectSouthEast" src="images/corner.gif" />';
	
	this.borderElement = document.getElementById(this.borderId);
	this.imageElement = document.getElementById(this.imageId);
	this.overlayElement = document.getElementById(this.overlayId);
	this.busyElement = document.getElementById(this.busyId);
	this.viewElement = document.getElementById(this.viewId);
	this.northElement = document.getElementById(this.northId);
	this.westElement = document.getElementById(this.westId);
	this.southElement = document.getElementById(this.southId);
	this.eastElement = document.getElementById(this.eastId);
	this.northwestElement = document.getElementById(this.northwestId);
	this.northeastElement = document.getElementById(this.northeastId);
	this.southwestElement = document.getElementById(this.southwestId);
	this.southeastElement = document.getElementById(this.southeastId);
	this.northTextElement = document.getElementById(northTextId);
	this.westTextElement = document.getElementById(westTextId);
	this.southTextElement = document.getElementById(southTextId);
	this.eastTextElement = document.getElementById(eastTextId);		
	
	this.setGeometry= function(element, top, left, height, width, clip) {
		if(top != null) {element.style.top=top+"px";}
		if(left != null) {element.style.left=left+"px";}
		if(width != null) {element.style.width=width+"px";}
		if(height != null) {element.style.height=height+"px";}
		if(clip != null) {
			element.style.clip = "rect(" + clip[0] + "px " +
	                               clip[1] + "px " +
	                               clip[2] + "px " +
	                               clip[3] + "px)";
	        //alert(element.style.clip);
		}
	}
		
	this.setViewSize = function(viewHeight,viewWidth) {	
		this.viewHeight = viewHeight;
		this.viewWidth = viewWidth;
		if(this.viewNorth != null) {
			// adjust view if viewSize changes
			this.setView(this.viewNorth, this.viewWest, this.viewSouth, this.viewEast)
		}
		this.setGeometry(this.borderElement,0,0,viewHeight+2,viewWidth+2,null);
		this.setGeometry(this.viewElement,1,1,viewHeight,viewWidth,null);	
	}
	
	// setView must be called before setMap
	this.setView = function(viewNorth, viewWest, viewSouth, viewEast) {
		// Dynamic map view variables
		var viewNorthSouth = viewNorth-viewSouth;
		var viewEastWest = viewEast-viewWest;
		var viewAspect = this.viewWidth/this.viewHeight;
		var aspect = viewEastWest/viewNorthSouth;
		if(aspect > viewAspect) {
			viewNorthSouth = viewEastWest/viewAspect;
			viewNorth = (viewNorth + viewSouth + viewNorthSouth)/2;
			viewSouth = viewNorth - viewNorthSouth;
		}
		else if(aspect < viewAspect) {
			viewEastWest = viewNorthSouth*viewAspect;
			viewEast = (viewEast + viewWest + viewEastWest)/2;
			viewWest = viewEast - viewEastWest;
		}
		this.viewNorth = viewNorth;
		this.viewWest = viewWest;
		this.viewSouth = viewSouth;	
		this.viewEast = viewEast;
		
		this.overlayTop = 1;
		this.overlayLeft = 1;
	}

	// setMap must be called before setSelection
	this.setMap = function(image_src, mapNorth, mapWest, mapSouth, mapEast, mapImageHeight, mapImageWidth) {
		// Semi-Static map variables
		this.imageElement.src = image_src;
		this.mapNorth = mapNorth;
		this.mapWest = mapWest;
		this.mapSouth = mapSouth;
		this.mapEast = mapEast;
		this.mapImageHeight = mapImageHeight;	
		this.mapImageWidth = mapImageWidth;		
		
		// Dynamic Map variables derived from view
		var viewResolution = this.viewHeight / (this.viewNorth-this.viewSouth);
		var mapResolution = this.mapImageHeight / (this.mapNorth-this.mapSouth);		
		var mapZoom = viewResolution / mapResolution;
		this.mapHeight = Math.round(mapImageHeight * mapZoom);
		this.mapWidth = Math.round(mapImageWidth * mapZoom);
		
	    this.mapTop = (this.viewNorth-mapNorth)/(mapNorth-mapSouth)*this.mapHeight;
	    this.mapLeft = (mapWest-this.viewWest)/(mapEast-mapWest)*this.mapWidth;

        this.setGeometry(this.imageElement,this.mapTop,this.mapLeft,
        				 this.mapHeight,this.mapWidth,
        				 [-this.mapTop+1,this.viewWidth-this.mapLeft+1,
        				   this.viewHeight-this.mapTop+1,-this.mapLeft+1]);
     	if(!window.opera) {
			this.divElement.style.zIndex = "0";
		}
	}
	
	this.setSelection = function(selNorth, selWest, selSouth, selEast) {
		// Dynamic selection variables
		this.selNorth = selNorth;
		this.selWest = selWest;
		this.selSouth = selSouth;
		this.selEast = selEast;
		
		// Dynamic selection variables derived from selection
	    this.selTop = (this.viewNorth-this.selNorth)/(this.mapNorth-this.mapSouth)*this.mapHeight;
	    this.selRight = (this.selEast-this.viewWest)/(this.mapEast-this.mapWest)*this.mapWidth;
	    this.selBottom = (this.viewNorth-this.selSouth)/(this.mapNorth-this.mapSouth)*this.mapHeight;
	    this.selLeft = (this.selWest-this.viewWest)/(this.mapEast-this.mapWest)*this.mapWidth;
		
		//alert(this.selTop + " " + this.selRight + " " + this.selBottom + " " + this.selLeft);	
		
        this.setGeometry(this.northElement, this.selTop, this.selLeft, null, null, [0, this.selRight-this.selLeft, 2, 0]);
        this.setGeometry(this.westElement, this.selTop, this.selLeft, null, null, [0, 2, this.selBottom-this.selTop, 0]);
        this.setGeometry(this.southElement, this.selBottom, this.selLeft, null, null, [0, this.selRight-this.selLeft, 2, 0]);
        this.setGeometry(this.eastElement, this.selTop, this.selRight, null, null, [0, 2, this.selBottom-this.selTop, 0]);
        this.setGeometry(this.northwestElement, this.selTop-1, this.selLeft-1);
        this.setGeometry(this.northeastElement, this.selTop-1, this.selRight-3);
        this.setGeometry(this.southwestElement, this.selBottom-3, this.selLeft-1);
        this.setGeometry(this.southeastElement, this.selBottom-3, this.selRight-3);
        
        this.northTextElement.value = Math.round(1000*this.selNorth)/1000;
	    this.westTextElement.value = Math.round(1000*this.selWest)/1000;
	    this.eastTextElement.value = Math.round(1000*this.selEast)/1000;
	    this.southTextElement.value = Math.round(1000*this.selSouth)/1000;
        
	}

	this.zoomIn = function(){
		var overlayNorth = this.viewNorth;
		var overlaySouth = this.viewSouth;
		var overlayEast = this.viewEast;
		var overlayWest = this.viewWest;
		var overlayImageHeight = this.viewHeight;
		var overlayImageWidth = this.viewWidth;
		this.setView(this.selNorth, this.selWest, this.selSouth, this.selEast);
		this.setMap(this.imageElement.src, this.mapNorth, this.mapWest, this.mapSouth, this.mapEast, this.mapImageHeight, this.mapImageWidth);
		this.setSelection(this.selNorth, this.selWest, this.selSouth, this.selEast);
		// Overlay zoom stuff....
		var viewResolution = this.viewHeight / (this.viewNorth-this.viewSouth);
		var overlayResolution = overlayImageHeight / (overlayNorth-overlaySouth);		
		var overlayZoom = viewResolution / overlayResolution;
		var overlayHeight = Math.round(overlayImageHeight * overlayZoom);
		var overlayWidth = Math.round(overlayImageWidth * overlayZoom);
		
	    var overlayTop = (this.viewNorth-overlayNorth)/(overlayNorth-overlaySouth)*overlayHeight;
	    var overlayLeft = (overlayWest-this.viewWest)/(overlayEast-overlayWest)*overlayWidth;

        this.setGeometry(this.overlayElement,overlayTop,overlayLeft,
        				 overlayHeight,overlayWidth,
        				 [-overlayTop+1,this.viewWidth-overlayLeft+1,
        				   this.viewHeight-overlayTop+1,-overlayLeft+1]);
		gui.refreshOverlay();
	}
	
	this.zoomOut = function(){
		var overlayNorth = this.viewNorth;
		var overlaySouth = this.viewSouth;
		var overlayEast = this.viewEast;
		var overlayWest = this.viewWest;
		var overlayImageHeight = this.viewHeight;
		var overlayImageWidth = this.viewWidth;
		this.setView((this.viewNorth*3-this.viewSouth)/2, 
					 (this.viewWest*3-this.viewEast)/2, 
					 (this.viewSouth*3-this.viewNorth)/2, 
					 (this.viewEast*3-this.viewWest)/2);
		this.setMap(this.imageElement.src, this.mapNorth, this.mapWest, this.mapSouth, this.mapEast, this.mapImageHeight, this.mapImageWidth);
		this.setSelection(this.selNorth, this.selWest, this.selSouth, this.selEast);
		// Overlay zoom stuff....
		var viewResolution = this.viewHeight / (this.viewNorth-this.viewSouth);
		var overlayResolution = overlayImageHeight / (overlayNorth-overlaySouth);		
		var overlayZoom = viewResolution / overlayResolution;
		var overlayHeight = Math.round(overlayImageHeight * overlayZoom);
		var overlayWidth = Math.round(overlayImageWidth * overlayZoom);
		
	    var overlayTop = (this.viewNorth-overlayNorth)/(overlayNorth-overlaySouth)*overlayHeight;
	    var overlayLeft = (overlayWest-this.viewWest)/(overlayEast-overlayWest)*overlayWidth;

        this.setGeometry(this.overlayElement,overlayTop,overlayLeft,
        				 overlayHeight,overlayWidth,
        				 [-overlayTop+1,this.viewWidth-overlayLeft+1,
        				   this.viewHeight-overlayTop+1,-overlayLeft+1]);
		gui.refreshOverlay();
	}
	
	this.overlayLoad = function(event){
		var srcElement = document.getElementById("overlayImage")
	    if(typeof(srcElement.eventObject) == "undefined") {
	    	return;
	    }
	    var self = srcElement.eventObject;
		self.overlayTop = 1;
		self.overlayLeft = 1; 
		//var debugElement = document.getElementById("debug");
		//debugElement.innerHTML = srcElement.src;
        self.setGeometry(self.overlayElement,self.overlayTop,self.overlayLeft,
        			self.viewHeight,self.viewWidth, 
    				[-self.overlayTop+1,self.viewWidth-self.overlayLeft+1,
    					self.viewHeight-self.overlayTop+1,-self.overlayLeft+1]);
    	self.setGeometry(self.busyElement,1,1,0,0);
	}
	
	this.mouseDown = function(event) {
	    if(!event) var event = window.event;
	    gui.cancelEvent(event);
	    gui.getMouseXY(event);
	    gui.srcElement = (event.target) ? event.target : event.srcElement;
	    if(gui.srcElement == null) return false;
	    if(typeof(gui.srcElement.eventObject) != "undefined") {
	    	var self = gui.srcElement.eventObject;
	    }
	    else {
		   	return false;
		}
	    document.onmousemove=self.mouseMove;
	    document.onmouseup=self.mouseUp;
	    return false;
	}
	
	this.mouseMove = function(event) {
	    if(!event) var event = window.event;
	    if(gui.srcElement == null) return false;
	    if(typeof(gui.srcElement.eventObject) != "undefined") {
	    	var self = gui.srcElement.eventObject;
	    }
	    else {
	    	return false;
	    }	    	
	    if(gui.srcElement.isView) {
	    	return self.mapMouseMove(event);
	    }
	    else if (gui.srcElement.isSelector) {
	    	return self.selectMouseMove(event);
	    }
	}

	this.mouseOver = function(event) {
		mapUnderMouse = true;
	}
	
	this.mouseOut = function(event)  {
		mapUnderMouse = false;
	}

	this.dragStart = function(event)  {
		return false;
	}

	this.selectStart = function(event)  {
		return false;
	}

	this.mapMouseMove = function(event) {
	    if(!event) var event = window.event;
	    if(!gui.srcElement) return;
	    //if(!mapUnderMouse) return;
	    gui.getMouseXYnow(event);
	    //alert("In mapMouseMove");
	    if(gui.srcElement.isView) {
	        this.mapTop += gui.mouseYnow-gui.mouseY;
	        this.mapLeft += gui.mouseXnow-gui.mouseX;
	        this.setGeometry(this.imageElement,this.mapTop,this.mapLeft,null,null,
	        				[-this.mapTop+1,this.viewWidth-this.mapLeft+1,
	        					this.viewHeight-this.mapTop+1,-this.mapLeft+1]);
	        					
	        this.overlayTop += gui.mouseYnow-gui.mouseY;
	        this.overlayLeft += gui.mouseXnow-gui.mouseX;	        					
	        this.setGeometry(this.overlayElement,this.overlayTop,this.overlayLeft,null,null,
	        				[-this.overlayTop+1,this.viewWidth-this.overlayLeft+1,
	        					this.viewHeight-this.overlayTop+1,-this.overlayLeft+1]);
	        gui.mouseX = gui.mouseXnow;
	        gui.mouseY = gui.mouseYnow;
	    }
	    return false;
	}

	this.selectMouseMove = function(event) {
	    gui.getMouseXYnow(event);
        var oldTop = this.selTop;
        var oldRight = this.selRight;
        var oldBottom = this.selBottom;
        var oldLeft = this.selLeft;
        if(gui.srcElement == this.northElement || 
        		gui.srcElement == this.northeastElement || 
        		gui.srcElement == this.northwestElement) {
            this.selTop = Math.min(this.viewHeight, Math.max(0, this.selTop + gui.mouseYnow-gui.mouseY));
        }
        if (gui.srcElement == this.eastElement || 
        		gui.srcElement == this.northeastElement || 
        		gui.srcElement == this.southeastElement){
            this.selRight = Math.max(0, Math.min(this.viewWidth, this.selRight + gui.mouseXnow-gui.mouseX));
        }
        if (gui.srcElement == this.southElement || 
        		gui.srcElement == this.southeastElement || 
        		gui.srcElement == this.southwestElement){
            this.selBottom = Math.max(0, Math.min(this.viewHeight, this.selBottom + gui.mouseYnow-gui.mouseY));
        }
        if (gui.srcElement == this.westElement || 
        		gui.srcElement == this.southwestElement || 
        		gui.srcElement == this.northwestElement){
            this.selLeft = Math.min(this.viewWidth, Math.max(0, this.selLeft + gui.mouseXnow-gui.mouseX));
        }
        if(this.selLeft > this.selRight) {
            var temp = this.selLeft;
            this.selLeft = this.selRight;
            this.selRight = temp;
        }
        if(this.selTop > this.selBottom) {
            var temp = this.selTop;
            this.selTop = this.selBottom;
            this.selBottom = temp;
        }
        this.setGeometry(this.northElement, this.selTop, this.selLeft, null, null, [0, this.selRight-this.selLeft, 2, 0]);
        this.setGeometry(this.westElement, this.selTop, this.selLeft, null, null, [0, 2, this.selBottom-this.selTop, 0]);
        this.setGeometry(this.southElement, this.selBottom, this.selLeft, null, null, [0, this.selRight-this.selLeft, 2, 0]);
        this.setGeometry(this.eastElement, this.selTop, this.selRight, null, null, [0, 2, this.selBottom-this.selTop, 0]);
        this.setGeometry(this.northwestElement, this.selTop-1, this.selLeft-1);
        this.setGeometry(this.northeastElement, this.selTop-1, this.selRight-3);
        this.setGeometry(this.southwestElement, this.selBottom-3, this.selLeft-1);
        this.setGeometry(this.southeastElement, this.selBottom-3, this.selRight-3);
        if(oldTop != this.selTop || 
        		oldRight != this.selRight || 
        		oldBottom != this.selBottom || 
        		oldLeft != this.selLeft) {
            gui.mouseX = gui.mouseXnow;
            gui.mouseY = gui.mouseYnow;
        }
	    return false;
	}
	
	this.mouseUp = function(event) {
	    var self = null;
	    var wasView = false;
	    if(gui.srcElement != null && 
	    		typeof(gui.srcElement.eventObject) != "undefined") {
	    	self = gui.srcElement.eventObject;
	    	wasView = typeof(gui.srcElement.isView) != "undefined";
	    }
	    gui.cancelMouseUp(event);
	
	    self.viewNorth = self.mapNorth+(self.mapNorth-self.mapSouth)*self.mapTop/self.mapHeight;
	    self.viewWest = self.mapWest-(self.mapEast-self.mapWest)*self.mapLeft/self.mapWidth;
	    self.viewEast = self.viewWest+(self.mapEast-self.mapWest)*self.viewWidth/self.mapWidth;
	    self.viewSouth = self.viewNorth-(self.mapNorth-self.mapSouth)*self.viewHeight/self.mapHeight;

	    self.selNorth = self.viewNorth-(self.mapNorth-self.mapSouth)*self.selTop/self.mapHeight;
	    self.selWest = self.viewWest+(self.mapEast-self.mapWest)*self.selLeft/self.mapWidth;
	    self.selEast = self.viewWest+(self.mapEast-self.mapWest)*self.selRight/self.mapWidth;
	    self.selSouth = self.viewNorth-(self.mapNorth-self.mapSouth)*self.selBottom/self.mapHeight;
	
	    self.northTextElement.value = Math.round(1000*self.selNorth)/1000;
	    self.westTextElement.value = Math.round(1000*self.selWest)/1000;
	    self.eastTextElement.value = Math.round(1000*self.selEast)/1000;
	    self.southTextElement.value = Math.round(1000*self.selSouth)/1000;
	
  	    if(self.callback != null) {
	    	self.callback(wasView);
	    }
	    	
	    return false;
	}
	
	this.setupElement = function(element, doEvents, backgroundColor, cursor, zIndex, isSelector, isView) {
	    //alert("Setting up " + element.id);
		element.style.position="absolute";
		if(doEvents != null && doEvents) {
	        element.onmousemove=this.mouseMove;
	        element.onmousedown=this.mouseDown; 
	        element.onmouseup=this.mouseUp;
	        element.onmouseover=this.mouseOver;
	        element.onmouseout=this.mouseOut;
	        element.ondragstart=this.dragStart;
	        element.onselectstart=this.selectStart;
	        element.galleryimg=false; 
            element.eventObject = this;
	    }	
		if(backgroundColor != null) {element.style.backgroundColor=backgroundColor;}
		if(cursor != null) {element.style.cursor="pointer";}
		if(zIndex != null){
		  if(typeof(element.style.zIndex) != "undefined"){
			element.style.zIndex=zIndex;
		  }
		}
		if(isSelector != null && isSelector==true) {element.isSelector = function(){;}}
		if(isView != null && isView==true) {element.isView = function(){;}}
	}
	
	this.setupElement(this.borderElement,false,"#000000",null,-4,false);
	this.setupElement(this.imageElement,true,null,"pointer",-3,false,true);
	this.setupElement(this.overlayElement,true,null,"pointer",-2,false,true);
	this.overlayElement.onload = this.overlayLoad;
	this.overlayElement.onafterupdate = this.overlayLoad;
	this.overlayElement.onerror = this.overlayLoad;
	this.setupElement(this.busyElement,true,null,"pointer",-1,false,true);
	this.setGeometry(this.busyElement,1,1,0,0);
	this.setupElement(this.viewElement,true,"transparent",null,null,false,true);
	this.setupElement(this.northElement,true,null,"crosshair",null,true);
	this.setupElement(this.westElement,true,null,"crosshair",null,true);
	this.setupElement(this.southElement,true,null,"crosshair",null,true);
	this.setupElement(this.eastElement,true,null,"crosshair",null,true);
	this.setupElement(this.northwestElement,true,null,"crosshair",null,true);	
	this.setupElement(this.northeastElement,true,null,"crosshair",null,true);
	this.setupElement(this.southwestElement,true,null,"crosshair",null,true);
	this.setupElement(this.southeastElement,true,null,"crosshair",null,true);

}
