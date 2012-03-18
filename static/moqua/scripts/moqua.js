var moqua = {

	checkEnabled : false,
	
	rangeCheck : function(doRefreshOverlay) {
	    if(!moqua.checkEnabled) { return; }
	    var userTime = new Array;
	    var timeStart = document.getElementById("timeStart");
	    var timeEnd = document.getElementById("timeEnd");
	    if(timeStart !=null){
		    var timeString = timeStart.value;
		    var re = /[:\- ]/;
		    var timeVals = timeString.split(re);
		    timeVals[1]-=1;
		    eval("userTime[0] = new Date(" + timeVals + ").getTime()-timeSlider.date0;");
		    //alert(timeSlider.formatValue(userTime[0]));
		    timeString = timeEnd.value;
		    timeVals = timeString.split(re);
		    timeVals[1]-=1;
		    eval("userTime[1] = new Date(" + timeVals + ").getTime()-timeSlider.date0;");
		    //alert(timeSlider.formatValue(userTime[1]));
		}
	    var userDepth = new Array;
	    var depthStart = document.getElementById("depthStart");
	    var depthEnd = document.getElementById("depthEnd");
	    if(depthStart != null && depthEnd != null) {
		    userDepth[0] = parseFloat(depthStart.value);
		    userDepth[1] = parseFloat(depthEnd.value);
		}
	    var userLat = new Array;
	    userLat[0] = parseFloat(document.getElementById("inputSouth").value);
	    userLat[1] = parseFloat(document.getElementById("inputNorth").value);
	    var userLong = new Array;
	    userLong[0] = parseFloat(document.getElementById("inputWest").value);
	    userLong[1] = parseFloat(document.getElementById("inputEast").value);
	    if(variableTree!=null){
	    	variableTree.getRootNode().setUnderlined(false);
	    }
	    datasetTree.getRootNode().setUnderlined(false);
	    var varNodesToUnderline = new Array();
	    var dsetNodesToUnderline = new Array();
	    for(var i_dset = 1; i_dset < datasetTree.allTreeNodes.length; ++i_dset) {
	        var dsetNode = datasetTree.allTreeNodes[i_dset];
	        if(dsetNode.yLimits != null) {
	            var doUnderline = (userLat[0] <= dsetNode.yLimits[1]) && 
	                               (userLat[1] >= dsetNode.yLimits[0]) && 
	                               (userLong[0] <= dsetNode.xLimits[1]) && 
	                               (userLong[1] >= dsetNode.xLimits[0]); 
	            if(dsetNode.tLimits != null && userTime.length != 0) {
	                doUnderline = doUnderline &&
	                                (userTime[0] <= dsetNode.tLimits[1]) && 
	                                (userTime[1] >= dsetNode.tLimits[0]);
	            }
	            if(dsetNode.zLimits != null && userDepth.length != 0) {
	                doUnderline = doUnderline &&
	                                (userDepth[0] <= dsetNode.zLimits[1]) && 
	                                (userDepth[1] >= dsetNode.zLimits[0]);
	            } 
	            //else {
	            //    doUnderline = doUnderline &&
	            //                    (userDepth[0] <= 0) && 
	            //                    (userDepth[1] >= 0);
	        	//}
	            if(doUnderline) {
	                dsetNodesToUnderline.push(dsetNode);
	                if(typeof(dsetNode.variables) != "undefined" ) {
	                	for(i_var = 0; i_var < dsetNode.variables.length; ++i_var) {
	                		varNode = dsetNode.variables[i_var].varNode;
							varNodesToUnderline.push(varNode);
						}
					}
	            }
	            //else alert("doUnderline = false for " + dsetNode.name + " t:" + dsetNode.tLimits + " z:" + dsetNode.zLimits + " y:" + dsetNode.yLimits + " x:" + dsetNode.xLimits );
	        }
	    }
	    dsetNodesToUnderline = util.uniqueSort(dsetNodesToUnderline,util.compareNode);
	    for(var i_node = 0; i_node < dsetNodesToUnderline.length ; ++i_node) {
            dsetNodesToUnderline[i_node].setUnderlined(true);
	    }
	    if(variableTree!=null){
		    varNodesToUnderline = util.uniqueSort(varNodesToUnderline,util.compareNode);
		    for(var i_node = 0; i_node < varNodesToUnderline.length ; ++i_node) {
		        varNodesToUnderline[i_node].setUnderlined(true);
		    }
	    }
	    
	    if(doRefreshOverlay){
	    	gui.refreshOverlay();
	    }
	},
	
	updateDataSliceEnabled : false,

	updateSelectDataSlice : function(){
		if(!moqua.updateDataSliceEnabled || variableTree==null) return;
		//alert(variableTree.getSelected().join(","));
		if(datasetTree.getSelected() == null || datasetTree.getSelected().length != 1) {
			moqua.setSelectDataSlice("{}","");
		} else {
			xmlhttp.doCallBack("","update", "application/json", moqua.setSelectDataSlice, "", true, 
				[{pName:"get",pValue:"views"},
				 {pName:"variables",pValue:variableTree.getSelected().join(",")},
				 {pName:"variableCount",pValue:variableTree.getSelected().length},
				 {pName:"contentType",pValue:"application/json"}]);
		}
	},
	
	setSelectDataSlice : function(responseText, params){
		var foo = JSON.parse(responseText);//eval("("+responseText+")");//
		//alert(foo.toSource());
		if(!viewSelect.replaceOptions(foo.views,"Select Data Type(s) & 1 Source","",true)) {
			outputSelect.replaceOptions(null,"First Select Data Slice","",false);
		}
	}
}