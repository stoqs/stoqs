function TimeSlider() {
	var self = new DualSlider(1059696000000,1062374400000,233,9,744,
	                       "timeRail","timeLeft","timeRight",
	                       "timeStart","timeEnd","timeMin","timeMax",
	                       moqua.rangeCheck);
	// Used in formatValue over-ride
	self.date0 = new Date().getTimezoneOffset()*60000;

	// Over-rides moqua_slider.formatValue
	self.formatValue = function(value)
	{
		return util.toTimeString(value + this.date0, true);
	}

    return self
}

function DepthSlider() {

	var self = new DualSlider(0,1000,233,9,991,
	                       "depthRail","depthLeft","depthRight",
	                       "depthStart","depthEnd","depthMin","depthMax",
	                       moqua.rangeCheck);

    return self

}

function DualSlider(min,max,width,elWidth,offset,
                      railId,leftId,rightId,startId,endId,minId,maxId,
                      callback) {

	// Semi-static variables
	this.min = min;
	this.max = max;
	this.width = width;
	this.elWidth = elWidth;
	this.offset = offset;
	this.railId = railId;
	this.leftId = leftId;
	this.rightId = rightId;
	this.startId = startId;
	this.endId = endId;
	this.minId = minId;
	this.maxId = maxId;
	this.callback = callback;

	// Dynamic variables
	this.left = 0;
	this.right = width-elWidth;
	this.start = min;
	this.end = max;
	this.underMouse = false;
	
	// Initialization
	this.railElement = document.getElementById(railId);
	this.leftElement = document.getElementById(leftId);
	this.rightElement = document.getElementById(rightId);
	this.startElement = document.getElementById(startId);
	this.endElement = document.getElementById(endId);
	this.minElement = document.getElementById(minId);
	this.maxElement = document.getElementById(maxId);

	// Methods	
	
	this.setStart = function(start) {
		if(start <= this.end) {
			this.setPosition(start,this.end);
		}
		else {
			this.setPosition(start,start);
		}				
	}
	
	this.getStart = function() {
		return this.start;
	}

	this.setEnd = function(end) {
		if(end >= this.start) {
			this.setPosition(this.start,end);
		}
		else {
			this.setPosition(end,end);
		}
	}
	
	this.getEnd = function() {
		return this.end;
	}

	this.setPosition = function(start,end) {
		this.start = Math.min(Math.max(this.min,start),this.max);
		this.end = Math.min(Math.max(this.min,end),this.max);
		if(this.end<this.start) {
			var temp = this.end;
			this.end = this.start;
			this.start = temp;
		}
	    this.left = (this.start-this.min)/(this.max-this.min)*(this.width-this.elWidth*2);
	    this.right = (this.end-this.min)/(this.max-this.min)*(this.width-this.elWidth*2)+this.elWidth;
        this.leftElement.style.left = this.left + "px";
        this.rightElement.style.left = this.right + "px";
	    this.startElement.value = this.formatValue(this.start);
	    this.endElement.value = this.formatValue(this.end);
	    if(this.callback) {
	    	this.callback(true);
	    }
	    return false;
	}
	
	this.setLimits = function(min,max)
	{
		this.min = min;
		this.max = max;
		if(this.start < this.min){
			this.start = this.min;
		} else if(this.start > this.max){
			this.start = this.max;
		}
		if(this.end < this.min){
			this.end = this.min;
		} else if(this.end > this.max){
			this.end = this.max;
		}
		// Now we regenerate the bars with the new limits...
		datasetTree.regenerateTimeLines();
		
		// And reposition the slider
		this.setPosition(this.start,this.end);
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
	    if(gui.srcElement != self.railElement ) {
	        document.onmousemove=self.mouseMove;
	        document.onmouseup=self.mouseUp;
	    }
	    else {
	        self.left = Math.max(0, Math.min(self.width-self.elWidth*2, gui.mouseX-self.elWidth*2-self.offset));
	        self.right = Math.max(9, Math.min(self.width-self.elWidth, gui.mouseX-self.elWidth-self.offset));
	        self.leftElement.style.left = self.left + "px";
	        self.rightElement.style.left = self.right + "px";
	        self.mouseUp(event)
	    }
	    return false;
	}
	
	this.mouseMove = function(event) {
	    if(!event) var event = window.event;
	    if(gui.srcElement == null) return false;
	    gui.getMouseXYnow(event);
	    if(typeof(gui.srcElement.eventObject) != "undefined") {
	    	var self = gui.srcElement.eventObject;
	    }
	    else {
	    	return false;
	    }	    	
	    if(gui.srcElement != self.railElement) {
	        var oldRight = self.right;
	        var oldLeft = self.left;
	        if (gui.srcElement == self.rightElement){
	            self.right = Math.max(self.left+self.elWidth, Math.min(self.width-self.elWidth, self.right + gui.mouseXnow-gui.mouseX));
	        }
	        else if (gui.srcElement == self.leftElement){
	            self.left = Math.max(0, Math.min(self.right-self.elWidth, self.left + gui.mouseXnow-gui.mouseX));
	        }
	        self.leftElement.style.left = self.left + "px";
	        self.rightElement.style.left = self.right + "px";
	        if(oldRight != self.right || oldLeft != self.left) {
	            gui.mouseX = gui.mouseXnow;
	            gui.mouseY = gui.mouseYnow;
	        }
	    }    
	    return false;
	}
		
	this.mouseUp = function(event) {
	    var self = null;
	    if(gui.srcElement != null && 
	    		typeof(gui.srcElement.eventObject) != "undefined") {
	    	var self = gui.srcElement.eventObject;
	    }
	    gui.cancelMouseUp(event);
	    if(self !=null) {
		    self.start = self.min+(self.max-self.min)*self.left/(self.width-self.elWidth*2);
		    self.end = self.min+(self.max-self.min)*(self.right-self.elWidth)/(self.width-self.elWidth*2);
		    self.startElement.value = self.formatValue(self.start);
		    self.endElement.value = self.formatValue(self.end);
		    if(self.callback != null) {
		    	self.callback(true);
		    }
		}
	    return false;
	}
	
	this.mouseOver = function(event) {
		this.underMouse = true;
	}

	this.mouseOut = function(event) {
		this.underMouse = false;
	}

	this.dragStart = function(event) {
		return false;
	}

	this.selectStart = function(event) {
		return false;
	}
	
	this.formatValue = function(value)
	{
		return Math.round(value*10)/10;
	}
	
	this.zoomIn = function(){
		this.setLimits(this.start,this.end);
	}

	this.zoomOut = function(){
		this.setLimits((this.min*3-this.max)/2,(this.max*3-this.min)/2);
	}
		
	this.setupElement = function(element, top, left) {
		element.style.position="absolute";
		element.style.top=top+"px";
		element.style.left=left+"px";
		element.style.cursor="pointer";
        element.onmousedown=this.mouseDown; 
        element.onmousemove=this.mouseMove;
        element.onmouseup=this.mouseUp;
        element.onmouseover=this.mouseOver;
        element.onmouseout=this.mouseOut;
        element.ondragstart=this.dragStart;
        element.onselectstart=this.selectStart;
        element.galleryimg=false; 	
        element.eventObject = this;
	}
	
	this.setupElement(this.railElement,1,0);
	this.setupElement(this.leftElement,0,this.left);
	this.setupElement(this.rightElement,0,this.right);
}
