var gui = {

	// Gui variables
	
	mouseX : null,
	mouseY : null,
	mouseXnow : null,
	mouseYnow : null,
	srcElement : null,
	doingSync : false,
	timeSlider : null,
	depthSlider : null,
	variableTree : null,
	datasetTree : null,
	
	// Gui elements
	
	//statusElement : null,
	
	// Gui methods
		
	cancelEvent : function(event) {
	    if(!event) var event = window.event;
	    if(typeof(event.cancelBubble) != "undefined") {
	        event.cancelBubble = true;
	    }
	    if(typeof(event.cancelDrag) != "undefined") {
	        event.cancelDrag = true;
	    }
	    if(typeof(event.returnValue) != "undefined") {
	        event.returnValue = false;
	    }
	    if(typeof(event.preventDefault) != "undefined") {
	        event.preventDefault();
	    }
	    if(typeof(event.stopPropagation) != "undefined") {
	        event.stopPropagation();
	    }
	    return false;
	},
	
	getMouseXY : function(event) {
	    if(!event) var event = window.event;
	    if(event.pageX || event.pageY) {
	        this.mouseX = parseInt(event.pageX);
	        this.mouseY = parseInt(event.pageY);
	    }
	    else if (event.clinetX || event.clientY) {
	        this.mouseX = event.clientX + document.body.scrollLeft;
	        this.mouseY = event.clientY + document.body.scrollTop;
	    }
	},
	
	getMouseXYnow : function(event) {
	    if(!event) var event = window.event;
	    if(event.pageX || event.pageY) {
	        this.mouseXnow = parseInt(event.pageX);
	        this.mouseYnow = parseInt(event.pageY);
	    }
	    else if (event.clinetX || event.clientY) {
	        this.mouseXnow = event.clientX + document.body.scrollLeft;
	        this.mouseYnow = event.clientY + document.body.scrollTop;
	    }
	},
	
	cancelMouseUp : function(event) {
	    this.srcElement = null;
	    if(!event) var event = window.event;
	    this.cancelEvent(event);
	    document.onmouseup=null;
	    document.onmousemove=null;
	},
	
	standardClick : function (treeNode) {
	},
	
	submit_it : function(event) {
	    if(!event) var event = window.event;
	    this.srcElement = (event.target) ? event.target : event.srcElement;
	    var submit_id = this.srcElement.id.split('_')[0];
	    var submit_element = document.getElementById(submit_id);
	    if(submit_element!=null) {
	        submit_element.click();
	    }
	},
	
	syncScroll : function(event) {
	    if(this.doingSync) return;
	    this.doingSync = true;
	    if(!event) var event = window.event;
	    this.srcElement = (event.target) ? event.target : event.srcElement;
	    var scrollTop = 0;
	    if(typeof(this.srcElement.scrollTop) != "undefined") {
	        scrollTop = this.srcElement.scrollTop;
	    }
	    else {
	        var div = this.srcElement.parentNode;
	        scrollTop = div.scrollTop;
	    }
	    var dsetDiv = document.getElementById('dsetDiv');
	    if(dsetDiv!=null){
	    	dsetDiv.scrollTop = scrollTop;
	    }
	    var dsetDivTime = document.getElementById('dsetDivTime');
	    if(dsetDivTime!=null){
	    	dsetDivTime.scrollTop = scrollTop;
	    }
	    var dsetDivDepth = document.getElementById('dsetDivDepth');
	    if(dsetDivDepth!=null){
	    	dsetDivDepth.scrollTop = scrollTop;
	    }
	    this.doingSync = false;
	},	
	
	refreshOverlay : function(){
    	var image_src = "update?get=trajectory&contentType=image/gif";
    	image_src += "&datasets=" + datasetTree.getCheckedDatasetNames();
    	image_src += "&highlight=" + datasetTree.getHighlightedDatasetNames();
    	image_src += "&tlo=" + timeSlider.getStart() + "&thi=" + timeSlider.getEnd();
		image_src += "&zlo=" + depthSlider.getStart() + "&zhi=" + depthSlider.getEnd();
		image_src += "&ylo=" + moquaMap.viewSouth + "&yhi=" + moquaMap.viewNorth;
		image_src += "&xlo=" + moquaMap.viewWest + "&xhi=" + moquaMap.viewEast;
		image_src += "&height=" + moquaMap.viewHeight + "&width=" + moquaMap.viewWidth;
		image_src += "&random=" + Math.random();
    	moquaMap.overlayElement.src = image_src;
    	moquaMap.setGeometry(moquaMap.busyElement,1,1,32,32);
    }, 
    
    zoomInMap : function(event){
    	moquaMap.zoomIn();
    },
    
    zoomOutMap : function(event){
    	moquaMap.zoomOut();
    },
    
    zoomInTime : function(event){
    	timeSlider.zoomIn();
    },
    
    zoomOutTime : function(event){
    	timeSlider.zoomOut();
    },
    
    zoomInDepth : function(event){
    	depthSlider.zoomIn();
    },
    
    zoomOutDepth : function(event){
    	depthSlider.zoomOut();
    }
    	
}
