
function VariableTree(treeName, treeStruct) {
	
	var rootNode = new TreeNode(treeStruct.id, treeStruct.name);
	var self = new Tree(treeName, rootNode);
	self.checkEnabled  =  false;

	self.makeVariableBranches = function (treeStruct,parentNode) {
		if (typeof(treeStruct.children) != "undefined")
		for (var i = 0; i < treeStruct.children.length; ++i) {
			if(typeof treeStruct.children[i].error != "undefined") {
				alert(treeStruct.children[i].error);
				return;
			}
			var childNode = 
				new TreeNode(treeStruct.children[i].id, treeStruct.children[i].name);
			if(typeof treeStruct.children[i].error != "undefined") {
				alert(treeStruct.children[i].error);
				return;
			}
			if(typeof treeStruct.children[i].datasets != "undefined") {
				childNode.datasets = treeStruct.children[i].datasets;				
			}
			if(typeof treeStruct.children[i].varName != "undefined") {
				childNode.varName = treeStruct.children[i].varName;				
				childNode.addCheckbox('name="CB' + treeStruct.children[i].varName + '"');
			}
			else
			{
				childNode.addCheckbox('');
			}
			childNode.setCheckHandler(treeName + ".varCheck");
			childNode.setHandler(treeName + ".varSelect");
			parentNode.addChild(childNode);
			self.makeVariableBranches(treeStruct.children[i],childNode);
		}
	}
	
	self.varCheck = function(treeNode) {     
	    if(!this.checkEnabled) { return; }
		moqua.updateSelectDataSlice();
 	    var nodesToOpen = new Array();
 	    var checkedCount = 0;
	    for(var i_var = 0; i_var < this.allTreeNodes.length; ++i_var) {
	        var varNode = this.allTreeNodes[i_var];
	        if(typeof(varNode.datasets) != "undefined") {
	            var checked = varNode.getCheckState() == 1;
	            if(checked) {
	            	checkedCount += 1;
	            	for(i_dset = 0; i_dset < varNode.datasets.length; ++i_dset) {
	                	nodesToOpen.push(varNode.datasets[i_dset].dsetNode);
	                }
	            }
	        }
	    }
	    if(criteriaRadio.getCheckedValue()=="any") {
	    	checkedCount = 1;
	    }
	    nodesToOpen = util.uniqueSort(nodesToOpen,util.compareNode,checkedCount);
	    datasetTree.getRootNode().setGrayed(true);
	    for(var i_node = 0; i_node < nodesToOpen.length ; ++i_node) {
	        nodesToOpen[i_node].setGrayed(false);
	    }
	}

	self.varSelect = function(varNode) {     
	    if(!this.checkEnabled) { return; }
	    var oldSelectedTreeNodeID = this.selectedTreeNodeID;
	    this.unHighlightNodes();
	    this.selectedTreeNodeID = oldSelectedTreeNodeID;
   	    this.focusSelection();
		datasetTree.unHighlightNodes();
		this.varSelectRecursive(varNode)
	}
	self.varSelectRecursive = function(varNode) {     
        if(typeof(varNode.datasets) != "undefined") {
           	for(var i_dset = 0; i_dset < varNode.datasets.length; ++i_dset) {
               	if(typeof(varNode.datasets[i_dset].dsetNode) != "undefined") {
               		datasetTree.highlightNode(varNode.datasets[i_dset].dsetNode);
               	}
            }
        }
        if(varNode.hasChildren()) {
           	for(var i_child = 0; i_child < varNode.children.length; ++i_child) {
           		this.varSelectRecursive(varNode.children[i_child]);
            }
        }
	}
	
	self.getSelected = function(){
		var selected = new Array();
	    for(var i_var = 0; i_var < this.allTreeNodes.length; ++i_var) {
	        var varNode = this.allTreeNodes[i_var];
	        if(typeof(varNode.datasets) != "undefined") {
	            if(varNode.getCheckState() == 1) {
	            	for(i_dset = 0; i_dset < varNode.datasets.length; ++i_dset) {
	                	if(typeof(varNode.datasets[i_dset].dsetNode) != "undefined") {
		                	var dsetNode = varNode.datasets[i_dset].dsetNode;
		                	if(dsetNode.getCheckState() == 1) {
		                		selected.push(varNode.datasets[i_dset].varId);
	    	            	}
	    	            }
	                }
	            }
	        }
	    }
	    return selected;
	}

	self.makeVariableBranches(treeStruct,self.getRootNode());
	self.showTree('',document.getElementById('varDiv'));
	return self;		
}

function DatasetTree(treeName, treeStruct) {
	//alert("Making " + treeName);
	var rootNode = new TreeNode(treeStruct.id, treeStruct.name);
	var self = new Tree(treeName, rootNode);
	self.checkEnabled = false;
	
	self.makeTimeLine = function(values, minVal, maxVal, left, fullWidth, id, image) {
		if(values == null) return '';
		var width = fullWidth-left-3;
		var valPerPx = (maxVal-minVal)/width;
		var leftpx = Math.floor((values[0]-minVal)/valPerPx);
		var rightpx = Math.ceil((values[1]-minVal)/valPerPx);
		if(leftpx < -left) leftpx = -left;
		if(rightpx > width) rightpx = width;
		if(rightpx >= 0 && leftpx <= width && rightpx > leftpx) {
			retval = '<img style="position:absolute;' + 
							   'left:' + (left + leftpx) + 'px;' + 
							   'top:5px;height:10px;' +
							   'width:' + (rightpx-leftpx+1) + 'px;" ' + 
							   'id="' + id + '" src="' + image + '"/>';
		} else {
			retval = '<img style="position:absolute;' + 
							   'left:0px;' + 
							   'top:5px;height:10px;' +
							   'width:0px;" ' + 
							   'id="' + id + '" src="' + image + '"/>';
		}
		return retval;
	}

	self.changeTimeLine = function(values, minVal, maxVal, left, fullWidth, id) {
		if(values == null) return ;
		var element = document.getElementById(id);
		if(element != null) {
			var width = fullWidth-left-3;
			var valPerPx = (maxVal-minVal)/width;
			var leftpx = Math.floor((values[0]-minVal)/valPerPx);
			var rightpx = Math.ceil((values[1]-minVal)/valPerPx);
			if(leftpx < -left) leftpx = -left;
			if(rightpx > width) rightpx = width;
			if(rightpx >= 0 && leftpx <= width && rightpx > leftpx) {
				element.style.left = left + leftpx + 'px';
				element.style.width = rightpx-leftpx+1 + 'px';
			}
		}
	}

	self.makeDatasetBranches = function (treeStruct,parentNode) {
		if (typeof(treeStruct.children) != "undefined") {
			var minT = 1e35; 
			var maxT = -1e35;
			var minZ = 1e35;
			var maxZ = -1e35;
			for (var i = 0; i < treeStruct.children.length; ++i) {
				if(typeof treeStruct.children[i].error != "undefined") {
					alert(treeStruct.children[i].error);
					return;
				}
				var childNode = 
					new TreeNode(treeStruct.children[i].id, treeStruct.children[i].name);
				if(typeof treeStruct.children[i].tLo != "undefined") {
					childNode.tLimits = [treeStruct.children[i].tLo,treeStruct.children[i].tHi];								
				}
				if(typeof treeStruct.children[i].zLo != "undefined") {
					childNode.zLimits = [treeStruct.children[i].zLo,treeStruct.children[i].zHi];
				}
				if(typeof treeStruct.children[i].yLo != "undefined") {
					childNode.yLimits = [treeStruct.children[i].yLo,treeStruct.children[i].yHi];
				}
				if(typeof treeStruct.children[i].xLo != "undefined") {
					childNode.xLimits = [treeStruct.children[i].xLo,treeStruct.children[i].xHi];
				}
				if(typeof treeStruct.children[i].dsetName != "undefined") {
					childNode.dsetName = treeStruct.children[i].dsetName;				
					childNode.addCheckbox('name="CB' + treeStruct.children[i].dsetName + '"');
				}
				else
				{
					childNode.addCheckbox('');
				}
				childNode.setCheckHandler(treeName + ".dsetCheck");
				childNode.setHandler(treeName + ".dsetSelect");
				var dsetId = treeStruct.children[i].id;
				if(typeof(treeStruct.children[i].variables) != "undefined") {
					childNode.variables = treeStruct.children[i].variables;				
					for(var j = 0; j < childNode.variables.length; ++j) {
						var varId = childNode.variables[j].id;
						var varCatId = childNode.variables[j].varId;
						if(variableTree!=null){
							var varNode = variableTree.getTreeNode(varCatId);
							for(var k = 0; k < varNode.datasets.length; ++k) {
								if(varNode.datasets[k].id == dsetId) {
									varNode.datasets[k].dsetNode = childNode;
									varNode.datasets[k].varId = varId;
								}
							}
							childNode.variables[j].varNode = varNode;
						}
					}
				}
				parentNode.addChild(childNode);
				self.makeDatasetBranches(treeStruct.children[i], childNode);
				if(typeof(childNode.tLimits) != "undefined") {
					if(childNode.tLimits[0] != null && childNode.tLimits[0] < minT) {
						minT = childNode.tLimits[0];
					}
					if(childNode.tLimits[1] != null && childNode.tLimits[1] > maxT) {
						maxT = childNode.tLimits[1];
					}
					if(typeof(timeSlider)!="undefined"){
						childNode.setExtra(0,this.makeTimeLine(childNode.tLimits,timeSlider.min,timeSlider.max,timeSlider.elWidth,timeSlider.width,'time' + dsetId,'images/time.gif'));
					}
				}
				if(typeof(childNode.zLimits) != "undefined") {
					if(childNode.zLimits[0] != null && childNode.zLimits[0] < minZ) {
						minZ = childNode.zLimits[0];
					}
					if(childNode.zLimits[1] != null && childNode.zLimits[1] > maxZ) {
						maxZ = childNode.zLimits[1];
					}
					if(typeof(depthSlider) != "undefined") {
						childNode.setExtra(1,this.makeTimeLine(childNode.zLimits,depthSlider.min,depthSlider.max,depthSlider.elWidth,depthSlider.width,'depth' + dsetId,'images/depth.gif'));
					}
				}			
			}
			if(minT<maxT) {
				parentNode.tLimits = [minT,maxT];
			}
			if(minZ<maxZ) {
				parentNode.zLimits = [minZ,maxZ];
			}
		}
	}
	
	self.regenerateTimeLines = function(){
	    for(var i_dset = 1; i_dset < this.allTreeNodes.length; ++i_dset) {
	        var dsetNode = this.allTreeNodes[i_dset];
	        if(typeof(dsetNode.tLimits) != "undefined") {
		        this.changeTimeLine(dsetNode.tLimits,timeSlider.min,timeSlider.max,timeSlider.elWidth,timeSlider.width,'time' + dsetNode.id);
	        }
	        if(typeof(dsetNode.zLimits) != "undefined") {
		        this.changeTimeLine(dsetNode.zLimits,depthSlider.min,depthSlider.max,depthSlider.elWidth,depthSlider.width,'depth' + dsetNode.id);
	        }
	    }
	}
	
	self.dsetCheck = function(treeNode) {
	    if(!this.checkEnabled) { return; }
		moqua.updateSelectDataSlice();
 	    var nodesToOpen = new Array();
   	    var checkedCount = 0;
	    for(var i_dset = 1; i_dset < this.allTreeNodes.length; ++i_dset) {
	        var dsetNode = this.allTreeNodes[i_dset];
	        if(typeof(dsetNode.variables) != "undefined") {
	            var checked = dsetNode.getCheckState() == 1;
	            if(checked) {
	            	checkedCount += 1;
	            	for(i_var = 0; i_var < dsetNode.variables.length; ++i_var) {
	                	nodesToOpen.push(dsetNode.variables[i_var].varNode);
	                }
	            }
	        }
	    }
	    if(typeof(criteriaRadio)=="undefined" || criteriaRadio.getCheckedValue()=="any") {
	    	checkedCount = 1;
	    }
	    nodesToOpen = util.uniqueSort(nodesToOpen,util.compareNode,checkedCount);
	    if(variableTree != null){
	    	variableTree.getRootNode().setGrayed(true);
	    	for(var i_node = 0; i_node < nodesToOpen.length ; ++i_node) {
		        nodesToOpen[i_node].setGrayed(false);
		    }
	    }
	    gui.refreshOverlay();
	}

	self.dsetSelect = function(dsetNode) {     
	    if(!this.checkEnabled) { return; }
	    var oldSelectedTreeNodeID = this.selectedTreeNodeID;
	    this.unHighlightNodes();
	    this.selectedTreeNodeID = oldSelectedTreeNodeID;
   	    this.focusSelection();
   	    if(variableTree!=null){
			variableTree.unHighlightNodes();
		}
		this.dsetSelectRecursive(dsetNode);
		gui.refreshOverlay();
	}
	self.dsetSelectRecursive = function(dsetNode) {     
        if(typeof(dsetNode.variables) != "undefined" && variableTree!=null) {
           	for(var i_var = 0; i_var < dsetNode.variables.length; ++i_var) {
           		//alert("dsetNode " + dsetNode.getID() + " has variables.");
               	if(typeof(dsetNode.variables[i_var].varNode) != "undefined") {
               		variableTree.highlightNode(dsetNode.variables[i_var].varNode);
               	}
            }
        }
        if(dsetNode.hasChildren()) {
        	//alert("dsetNode " + dsetNode.getID() + " has children.");
           	for(var i_child = 0; i_child < dsetNode.children.length; ++i_child) {
           		this.dsetSelectRecursive(dsetNode.children[i_child]);
            }
        }
	}

	self.getCheckedDatasetNames = function() {
		var names="";
	    for(var i_dset = 1; i_dset < this.allTreeNodes.length; ++i_dset) {
        	var dsetNode = this.allTreeNodes[i_dset];
        	var checked = dsetNode.getCheckState() == 1;
        	if(checked && typeof(dsetNode.dsetName) != "undefined") {
            	if(names.length > 0) {
            		names += ",";
            	}
            	names += dsetNode.dsetName;
            }
        }
        return names;
    }

	self.getHighlightedDatasetNames = function() {
		var names="";
	    for(var i_dset = 1; i_dset < this.allTreeNodes.length; ++i_dset) {
        	var dsetNode = this.allTreeNodes[i_dset];
        	var highlighted = dsetNode.titleElement.className == 'treetitleselected';
        	if(highlighted && typeof(dsetNode.dsetName) != "undefined") {
            	if(names.length > 0) {
            		names += ",";
            	}
            	names += dsetNode.dsetName;
            } ;
        }
        return names;
    }

	treeStruct.node = self.getRootNode();
	self.makeDatasetBranches(treeStruct,rootNode);
	self.dsetDivTime = document.getElementById('dsetDivTime');
	self.dsetDivDepth = document.getElementById('dsetDivDepth');
	self.extraContainers = new Array();
	
	self.getSelected = function(){
		var selected = new Array();
	    for(var i_dset = 0; i_dset < this.allTreeNodes.length; ++i_dset) {
	        var dsetNode = this.allTreeNodes[i_dset];
	        if(typeof(dsetNode.variables) != "undefined") {
	            if(dsetNode.getCheckState() == 1) {
	            	for(i_var = 0; i_var < dsetNode.variables.length; ++i_var) {
	                	if(typeof(dsetNode.variables[i_var].varNode) != "undefined") {
		                	var varNode = dsetNode.variables[i_var].varNode;
		                	if(varNode.getCheckState() == 1) {
		                		selected.push(dsetNode.variables[i_var].dsetId);
	    	            	}
	    	            }
	                }
	            }
	        }
	    }
	    return selected;
	}

	if(self.dsetDivTime != null) {
		self.extraContainers[self.extraContainers.length] = self.dsetDivTime;
	}
	if(self.dsetDivDepth != null) {
		self.extraContainers[self.extraContainers.length] = self.dsetDivDepth;
	}
	self.showTree('',document.getElementById('dsetDiv'));
	return self;		
}
