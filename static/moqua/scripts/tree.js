/**
*
* Heavily modified my M. Godin, MBARI, to add:
*     intrinsic, cascading persistent checkboxes
*     multiple trees on one web page (this needs to be made more object oriented!)
*     support for cascading grayed selections
*     support for cascading underlined selections
*     many other bug fixes, including Opera 8 compatability
*     Removed buggy drag and editing capabilty.
*     Removed sorting
*     Finally, made object oriented
*
* Original Author of treeview.js: Martin Mouritzen. (martin@nano.dk)
*
*
* (Lack of) Documentation:
*
*
* If a finishedLoading method exists, it will be called when the tree is loaded.
* (good to display a div, etc.).
*
*
* You have to set the variable rootTreeNode (as a TreeNode).
*
*
*/

/**
* The Tree Object
* @param treeName, the variable name that this object is assigned to.
* @param rootTreeNode, the top node of the tree.
*/
function Tree(treeName, rootTreeNode) {

    // Name of the tree.
    this.treeName = treeName;

    // RootNode of the tree.
    this.rootTreeNode = rootTreeNode;
    if(rootTreeNode != null) {
        rootTreeNode.setTree(this);
        rootTreeNode.setRootNode(rootTreeNode);
    }
    
    /***********************************************************************
    * Configuration variables.
    ************************************************************************/

    // Should the rootTreeNode be displayed.
    this.showRootNode = true;    

    // Should the dashed lines between nodes be shown.
    this.showLines = true;

    // This is IMPORTANT... use an unique id for each document you use the tree in. (else they'll get mixed up).
    this.documentID = window.location.href.split('?')[0];

    // Shows/Hides subnodes on startup
    this.showAllTreeNodesOnStartup = false;

    // List of all nodes
    this.allTreeNodes = new Array();

    // Do checkbox clicks cascade down to children?
    this.checkDown = true;

    // Do checkbox clicks cascade up to parents when all children checked?
    this.checkUp = true;

    // This is the path that contains the /images folder
    this.imagePath = '';

    // If this is true, capture keyboard events
    this.captureKeyboard = false;
    
    // Container that contains this tree
    this.container = null; 
    
    // Array of extra containers that contain elements that react like this tree
    this.extraContainers = null;
    
    /************************************************************************
    * The following are instance variables.
    ************************************************************************/

    // selectedTreeNodeID
    this.selectedTreeNodeID = null;
    
    // open/closed/checked states are saved in cookies
    this.states = '';
    this.stateArray = new Array();
    
    this.highlightedNodes = new Array();

    /************************************************************************
    * Methods.
    ************************************************************************/
    
    this.setRootNode = function(rootTreeNode) {
        this.rootTreeNode = rootTreeNode;
        rootTreeNode.setTree(this);
        rootTreeNode.setRootNode(rootTreeNode);
    }
    this.getRootNode = function() {
        return this.rootTreeNode;
    }
    this.addTreeNode = function(node) {
        this.allTreeNodes[this.allTreeNodes.length] = node;
    }
    this.getTreeNode = function(nodeID) {
        for(i=0; i<this.allTreeNodes.length; ++i) {
            if(this.allTreeNodes[i].getID() == nodeID) {
                return this.allTreeNodes[i];
            }
        }
    }
    this.readStates = function() {
        this.states = this.getCookie(treeName + "_" + this.documentID);
        if (this.states != null) {
            var array = this.states.split(';');
            for(var i=0;i<array.length;i++) {
                var singlestate = array[i].split('|');
                this.stateArray[i] = new Array();
                this.stateArray[i]["key"] = singlestate[0];
                this.stateArray[i]["state"]  = singlestate[1];
                this.stateArray[i]["checkState"]  = singlestate[2];
            }
        }
    }
    this.getState = function(nodeID) {
        for(var i=0;i<this.stateArray.length;i++) {
            if (this.stateArray[i]["key"] == nodeID) {
                var state = this.stateArray[i]["state"];
                if (state == null || state == '') {
                    state = 'closed';
                }
                return state;
            }
        }
        return "closed";
    }
    this.getCheckState = function(nodeID) {
        for(var i=0;i<this.stateArray.length;i++) {
            if (this.stateArray[i]["key"] == nodeID) {
                var checkState = this.stateArray[i]["checkState"];
                if (checkState == null || checkState == '') {
                    checkState = -1;
                }
                return checkState;
            }
        }
        return -1;
    }
    this.setState = function(nodeID,newstate) {
        var str = '';
        var found = false;
        for(var i=0;i<this.stateArray.length;i++) {
            if (this.stateArray[i]["key"] == nodeID) {
                this.stateArray[i]["state"] = newstate;
                found = true;
            }
        }
        if (found == false) {
            this.stateArray[this.stateArray.length] = new Array();
            this.stateArray[this.stateArray.length - 1]["key"] = nodeID;
            this.stateArray[this.stateArray.length - 1]["state"] = newstate;
            this.stateArray[this.stateArray.length - 1]["checkState"] = '';
        }
    }
    this.setCheckState = function(nodeID,checkState) {
        var found = false;
        for(var i=0;i<this.stateArray.length;i++) {
            if (this.stateArray[i]["key"] == nodeID) {
                this.stateArray[i]["checkState"] = checkState;
                found = true;
            }
        }
        if (found == false) {
            this.stateArray[this.stateArray.length] = new Array();
            this.stateArray[this.stateArray.length - 1]["key"] = nodeID;
            this.stateArray[this.stateArray.length - 1]["state"] = '';
            this.stateArray[this.stateArray.length - 1]["checkState"] = checkState;
        }
    }
    this.writeStates = function() {
        var str = '';
        var found = false;
        for(var i=0;i<this.stateArray.length;i++) {
            if (this.stateArray[i]["state"] != null) {
                if(this.stateArray[i]["checkState"] != null) {
                    str += this.stateArray[i]["key"] + '|' + this.stateArray[i]["state"] + '|' + this.stateArray[i]["checkState"] + ';';
                }
                else
                {
                    str += this.stateArray[i]["key"] + '|' + this.stateArray[i]["state"] + '|;';
                }
            }
            else if(this.stateArray[i]["checkState"] != null) {
                str += this.stateArray[i]["key"] + '||' + this.stateArray[i]["checkState"] + ';';
            }
        }
        this.setCookie(treeName + "_" + this.documentID,str);
    }
    this.refreshCheckboxes = function() {
        for(var i=0;i<this.stateArray.length;i++) {
            var nodeID = this.stateArray[i]["key"];
            var treeNode = this.getTreeNode(nodeID);
            if(treeNode==null || treeNode==false) {
                continue;
            }
            if(treeNode.hasCheckbox()) {
                if(this.stateArray[i]["checkState"] != null && this.stateArray[i]["checkState"] != '') {
                    treeNode.setCheckState(this.stateArray[i]["checkState"], false);
                }
            }
        }
    }
    this.setElements = function() {
        for(var i=-1;i<this.allTreeNodes.length;i++) {
            var treeNode = i >= 0 ? this.allTreeNodes[i] : this.rootTreeNode;
            var nodeID = treeNode.getID();
            if(treeNode.hasCheckbox()) {
	            treeNode.checkboxElement = document.getElementById(treeNode.getCheckboxId());
            }
            treeNode.titleElement = document.getElementById(this.treeName+'Title'+nodeID);
            treeNode.submenuElement = document.getElementById(this.treeName+'Node' + nodeID + 'sub');
            treeNode.actionimageElement = document.getElementById(this.treeName+'Handler' + nodeID);
            treeNode.iconimageElement = document.getElementById(this.treeName+'Iconimage' + nodeID);
            if(this.extraContainers != null) {
	            for(var j = 0; j < this.extraContainers.length; ++j) {
		            treeNode.extraSubmenuElements[j] = document.getElementById(this.treeName+'Extra'+ j +'TreeNode' + nodeID + 'sub');
	    	    }
	        }
        }
    }
    this.showTree = function(path, container) {
    
        if(path != null)
            this.path = path;

        if(container != null)
            this.container = container;
    
        this.readStates();
        
        if(this.captureKeyboard){
            eval('document.onkeydown=' + this.treeName + '.keyDown');
        }

        window.focus();
        var str = '';
        str = '<div id="'+this.treeName+'Node' + this.rootTreeNode.getID() + '" class="treetitle" style="display:' + (this.showRootNode == true ? 'block' : 'none') + '">';
        str += '<nobr>';
        if (this.rootTreeNode.hasIcon()) {
            str += '<img src="' + this.rootTreeNode.getIcon() + '" style="vertical-align:middle;">';
        }
        else {
            str += '<img src="' + this.path + 'images/white.gif" style="width:1px;height:20px;vertical-align:middle;"/>';        
        }
        str += '<span ID="'+this.treeName+'Title' + this.rootTreeNode.getID() + '" style="height:20px;vertical-align:middle;">&nbsp;' + this.rootTreeNode.getName() + '</span>';
        str += '</nobr></div>';

        var extraCount = 0;
        var extraStrs = null;
        if(this.extraContainers != null){
            extraCount = this.extraContainers.length;
            extraStrs = new Array(extraCount);
            for(var i_extra=0; i_extra < extraCount; ++i_extra){
                extraStrs[i_extra] = '<div id="'+this.treeName+'Extra' + i_extra +  'TreeNode' + this.rootTreeNode.getID() + '" class="treetitle" style="display:' + (this.showRootNode == true ? 'block' : 'none') + '"\>';
                extraStrs[i_extra] += '<img src="' + this.path + 'images/white.gif" style="width:1px;height:20px;vertical-align:middle;"/>';        
                extraStrs[i_extra] += '</div>';
            }   
        }

        // Initially the tree is fully expanded, for Opera compatability
        if (this.rootTreeNode.hasChildren()) {
            for(var i=0;i<this.rootTreeNode.children.length;i++) {
                var nodeContents = this.showTreeNode(this.rootTreeNode.children[i],(i == (this.rootTreeNode.getChildCount() -1)));
                str = str + nodeContents;
                for(var i_extra=0; i_extra < extraCount; ++i_extra){
                    var extraContents = this.showTreeNodeExtra(this.rootTreeNode.children[i],(i == (this.rootTreeNode.getChildCount() -1)),i_extra);
                    extraStrs[i_extra] += extraContents;
                }
            }
        }
        this.container.innerHTML = str;
        for(var i_extra=0; i_extra < extraCount; ++i_extra){
            this.extraContainers[i_extra].innerHTML = extraStrs[i_extra];
        }
        this.setElements();
        if (this.rootTreeNode.hasChildren()) {
            var el = this.rootTreeNode.children[0].titleElement;
            // This forces Opera to recgonize the contents of container
            if(el.focus != null) {
                el.focus();
            }
        }
        if(!this.showAllTreeNodesOnStartup) {
            // This collapses the tree
            for(var i=this.allTreeNodes.length-1;i>=0;--i) {
                this.handleTreeNode(this.allTreeNodes[i].getID(), false);
            }
        }
        // This opens the tree, as needed
        for(var i=0;i<this.stateArray.length;++i) {
            var nodeID = this.stateArray[i]["key"];
            var treeNode = this.getTreeNode(nodeID);
            if(treeNode) {
                var state = this.stateArray[i]["state"];
                if ((state == 'open' && !this.showAllTreeNodesOnStartup) ||
                    (state == 'closed' && this.showAllTreeNodesOnStartup)) {
                    this.handleTreeNode(nodeID,false);
                }
            }
        }
        this.refreshCheckboxes();
        if (window.finishedLoading) {
            this.finishedLoading();
        }
    }
    /**
    * Shows the given node, and subnodes.
    */
    this.showTreeNode = function(treeNode,lastTreeNode) {
        var linestring = treeNode.getLineString();
        var state = this.getState(treeNode.getID());
        var str;
        str = '<div style="height:20px;filter:alpha(opacity=100);" id="'+this.treeName+'Node' + treeNode.getID() + '" onkeydown="' + this.treeName + '.keydown">';
        str += '<nobr>';
        for(var y=0;y<linestring.length;y++) {
            if (linestring.charAt(y) == 'I') {
                str += '<img src="' + this.path + 'images/' + (this.showLines ? 'line' : 'white') + '.gif" style="width:19px;height:20px;vertical-align:middle;">';
            }
            else if (linestring.charAt(y) == 'B') {
                str += '<img src="' + this.path + 'images/white.gif" style="width:19px;height:20px;vertical-align:middle;">';
            }
        }
        if (treeNode.hasChildren()) {
            // If this is the first child of the rootTreeNode, and showRootNode is false, we want to display a different icon.
            if (!this.showRootNode && (treeNode.getParent() == treeNode.getRootNode()) && (treeNode.getParent().getFirstChild() == treeNode)) {
                if (!lastTreeNode) {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (state == 'open' ? (this.showLines ? 'minus_no_root' : 'minus_nolines') : (this.showLines ? 'plus_no_root' : 'plus_nolines')) + '.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
                else {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (state == 'open' ? 'minus_last' : 'plus_last') + '_no_root.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
            }
            else {
                if (!lastTreeNode) {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (state == 'open' ? (this.showLines ? 'minus' : 'minus_nolines') : (this.showLines ? 'plus' : 'plus_nolines')) + '.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
                else {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (state == 'open' ? (this.showLines ? 'minus_last' : 'minus_nolines') : (this.showLines ? 'plus_last' : 'plus_nolines')) + '.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
            }
        }
        else {
            // If this is the first child of the rootTreeNode, and showRootNode is false, we want to display a different icon.
            if (!this.showRootNode && (treeNode.getParent() == treeNode.getRootNode()) && (treeNode.getParent().getFirstChild() == treeNode)) {
                if (!lastTreeNode) {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (this.showLines ? 't_no_root' : 'white') + '.gif" style="width:19px;height:20px;vertical-align:middle;">';
                }
                else {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/white.gif" style="width:19px;height:20px;vertical-align:middle;">';
                }
            }
            else {
                if (!lastTreeNode) {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (this.showLines ? 't' : 'white') + '.gif" style="width:19px;height:20px;vertical-align:middle;">';
                }
                else {
                    str += '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (this.showLines ? 'lastnode' : 'white') + '.gif" style="width:19px;height:20px;vertical-align:middle;">';
                }
            }
        }
        var iconStartImage = treeNode.getIcon();
        if (state != 'closed') {
            if (treeNode.hasChildren()) {
                iconStartImage = treeNode.getOpenIcon();
            }
        }

        if(treeNode.hasCheckbox())
        {
            str += '<input type="checkbox" color="#ffoooo" id="' + treeNode.getCheckboxId() + '" style="vertical-align:bottom;" onclick="' + this.treeName + '.checkboxClick(' + treeNode.getID() + ')" ' + treeNode.getCheckboxParam() + '>';
        }

        if(treeNode.hasIcon())
        {
            str += '<img id="'+this.treeName+'Iconimage' + treeNode.getID() + '" src="' + iconStartImage + '" style="vertical-align:middle;" OnClick="' + this.treeName + '.selectTreeNode(' + treeNode.getID() + ')">';
        }
        str += '&nbsp;<span unselectable="ON" style="vertical-align:middle;" class="treetitle" ID="'+this.treeName+'Title' + treeNode.getID() + '" OnDblClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ')" OnClick="' + this.treeName + '.selectTreeNode(' + treeNode.getID() + ')">';
        str += treeNode.getName();
        str += '</span>';
        str += '</nobr>';
        str += '</div>';

        if (treeNode.hasChildren()) {
            if (state == 'open') {
                str += '<div id="'+this.treeName+'Node' + treeNode.getID() + 'sub" style="display:block;">';
                this.fireOpenEvent(treeNode);
             }
            else {
                //str += '<div id="'+this.treeName+'Node' + treeNode.getID() + 'sub" style="display:' + (showAllTreeNodesOnStartup == true ? 'block;' : 'none;') + ';">';
                str += '<div id="'+this.treeName+'Node' + treeNode.getID() + 'sub" style="display:block;' + ';">';
            }
            var subgroupstr = '';
            var newChar = '';

            if (!lastTreeNode) {
                newChar = 'I';
            }
            else {
                newChar = 'B';
            }
            for(var z=0;z<treeNode.getChildCount();z++) {
                treeNode.children[z].setLineString(linestring + newChar);
            }
            for(var z=0;z<treeNode.getChildCount();z++) {
                subgroupstr += this.showTreeNode(treeNode.children[z],(z == (treeNode.getChildCount() -1)));
            }
            str += subgroupstr;
            str += '</div>';
        }
        else {
            //str += '<div id="'+this.treeName+'Node' + treeNode.getID() + 'sub" style="display:none;">';
            //str += '</div>';
        }
        return str;
    }
    /**
    * Shows the given node's extra container item, and subnodes.
    */
    this.showTreeNodeExtra = function(treeNode,lastTreeNode,extraIndex) {
        var state = this.getState(treeNode.getID());
        var str;
        str = '<div id="'+this.treeName+'Extra'+extraIndex+'TreeNode' + treeNode.getID() + '" style="position:relative;height:20px;">';
        //str += '<nobr>';
        //str += '<img src="' + this.path + 'images/white.gif" style="width:1px;height:20px;vertical-align:middle;"/>';        
        //str += '<span unselectable="ON" style="height:20px;vertical-align:middle;" class="treetitle" ID='+this.treeName+'"Extra'+extraIndex+'Title' + treeNode.getID() + '" >';
        str += treeNode.getExtra(extraIndex);
        //str += '</span>';
        //str += '</nobr>';
        str += '</div>';

        if (treeNode.hasChildren()) {
            if (state == 'open') {
                str += '<div id="'+this.treeName+'Extra'+extraIndex+'TreeNode' + treeNode.getID() + 'sub" style="display:block">';
            }
            else {
                str += '<div id="'+this.treeName+'Extra'+extraIndex+'TreeNode' + treeNode.getID() + 'sub" style="display:block;">';
            }
            var subgroupstr = '';
            for(var z=0;z<treeNode.getChildCount();z++) {
                subgroupstr += this.showTreeNodeExtra(treeNode.children[z],(z == (treeNode.getChildCount() -1)),extraIndex);
            }
            str += subgroupstr;
            str += '</div>';
        }
        else {
            //str += '<div id="'+this.treeName+'Extra'+extraIndex+'TreeNode' + treeNode.getID() + 'sub" style="display:none;">';
            //str += '</div>';
        }
        return str;
    }
        
    this.findSpanChild = function(element) {
        if (element.tagName == 'SPAN') {
            return element;
        }
        else {
            if (element.childTreeNodes) {
                for(var i=0;i<element.childTreeNodes.length;i++) {
                    var value = findSpanChild(element.childTreeNodes[i]);
                    if (value != false) {
                        return value;
                    }
                }
                return false;
            }
        }
    }
    this.selectTreeNode = function(nodeID) {
        var treeNode = this.getTreeNode(nodeID);
        if (this.selectedTreeNodeID != null) {
            if (this.selectedTreeNodeID == nodeID) {
                return;
            }
            //alert("Unfocusing " + this.treeName+'Title' + this.selectedTreeNodeID);
            var oldTreeNodeTitle = document.getElementById(this.treeName+'Title' + this.selectedTreeNodeID);
            oldTreeNodeTitle.className = 'treetitle';
        }
        this.selectedTreeNodeID = nodeID;
        //alert("Focusing " + this.treeName + " node " + nodeID);
        treeNode.titleElement.className = 'treetitleselected';

        if (treeNode.gotHandler()) {
            eval(treeNode.getHandler() + '(' + this.treeName + '.getTreeNode(' + nodeID + '));');
        }
        else if(typeof(this.standardClick) != "undefined") {
            this.standardClick(treeNode);
        }
    }
    this.refreshTreeNode = function(treeNode) {
        var submenu = treeNode.submenuElement; // document.getElementById(this.treeName+'Node' + treeNode.getID() + 'sub');
        var str = '';
        for(var i=0;i<treeNode.getChildCount();i++) {
            var parent = treeNode.getParent();
            if (!parent) {
                treeNode.children[i].setLineString(treeNode.getLineString() + 'B');
            }
            else {
                if (parent.children[parent.children.length - 1] == treeNode) {
                    treeNode.children[i].setLineString(treeNode.getLineString() + 'B');
                }
                else {
                    treeNode.children[i].setLineString(treeNode.getLineString() + 'I');
                }
            }
            str += this.showTreeNode(treeNode.children[i],i == (treeNode.getChildCount() - 1));
        }
        var actionimage = treenode.actionimageElement; //document.getElementById(''+this.treeName+'Handler' + treeNode.getID());
        if (treeNode.getChildCount() == 0) {
            // TreeNode haven't got any children, make sure the right image is displayed.
            if (actionimage.src.indexOf('last') == -1) {
                actionimage.src = this.path + 'images/' + (this.showLines ? 't' : 'white') + '.gif';
            }
            else {
                actionimage.src = this.path + 'images/' + (this.showLines ? 'lastnode' : 'white') + '.gif';
            }
            actionimage.onclick = null;

            // Close the submenu
            if (submenu) {
                submenu.style.display = 'none';
            }
        }
        else {
            // We have children, make sure to display the + and - icon.
            if (actionimage.src.indexOf('plus') != -1) {
                // The TreeNode have already got children, and displays them.
            }
            else if (actionimage.src.indexOf('minus') != -1) {
                // The TreeNode have already got children, and displays them.
            }
            else {
                if (actionimage.src.indexOf('last') == -1) {
                    actionimage.outerHTML = '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/' + (this.showLines ? 'plus' : 'plus_nolines') + '.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
                else {
                    actionimage.outerHTML = '<img id="'+this.treeName+'Handler' + treeNode.getID() + '" src="' + this.path + 'images/plus_last.gif" style="width:19px;height:20px;vertical-align:middle;" OnClick="' + this.treeName + '.handleTreeNode(' + treeNode.getID() + ');">';
                }
            }
        }
        submenu.innerHTML = str;
    }
    this.handleTreeNode = function(nodeID, doEvent) {
        var treeNode = this.getTreeNode(nodeID);
        if (!treeNode.hasChildren()) { // No reason to handle a node without children.
            return;
        }

        var submenu = treeNode.submenuElement; //document.getElementById(this.treeName+'Node' + nodeID + 'sub');
        if(submenu == null) { // extra RootNodes, for example
            return;
        }

        var iconimageholder = treeNode.iconimageElement; //document.getElementById(''+this.treeName+'Iconimage' + nodeID);
        var actionimage = treeNode.actionimageElement; //document.getElementById(''+this.treeName+'Handler' + nodeID);

        // This will be used if showRootNode is set to false.
        var firstChildOfRoot = false;
        if (actionimage!=null && actionimage.src.indexOf('_no_root') != -1) {
            firstChildOfRoot = true;
        }

        if (submenu.style.display == 'none') {
            if(doEvent==null || doEvent==true) {
                this.setState(nodeID,'open');
                this.writeStates();
                this.fireOpenEvent(treeNode);
            }

            submenu.style.display = 'block';

            if(iconimageholder != null) {
                iconimageholder.src = treeNode.getOpenIcon();
            }
            if (actionimage.src.indexOf('last') == -1) {
                actionimage.src = this.path + 'images/' + ((firstChildOfRoot) ? 'minus_no_root' : (this.showLines ? 'minus' : 'minus_nolines')) + '.gif';
            }
            else {
                actionimage.src = this.path + 'images/' + ((firstChildOfRoot) ? 'minus_last_no_root' : (this.showLines ? 'minus_last' : 'minus_nolines')) + '.gif';
            }
        }
        else {
            if(doEvent==null || doEvent==true) {
                this.setState(nodeID,'closed');
                this.writeStates();
            }

            submenu.style.display = 'none';

            if(iconimageholder != null) {
                iconimageholder.src = treeNode.getIcon();
            }
            if (actionimage.src.indexOf('last') == -1) {
                actionimage.src = this.path + 'images/' + ((firstChildOfRoot) ? 'plus_no_root' : (this.showLines ? 'plus' : 'plus_nolines')) + '.gif';
            }
            else {
                actionimage.src = this.path + 'images/' + ((firstChildOfRoot) ? 'plus_last_no_root' : (this.showLines ? 'plus_last' : 'plus_nolines')) + '.gif';
            }
        }
        
        if(this.extraContainers != null){
            var extraCount = this.extraContainers.length;
            for(var i_extra=0; i_extra < extraCount; ++i_extra){
            	if(treeNode.extraSubmenuElements.length > i_extra){
	                var submenu = treeNode.extraSubmenuElements[i_extra];//document.getElementById(''+this.treeName+'Extra'+ i_extra +'TreeNode' + nodeID + 'sub');
	                if(submenu == null) {
	                    contnue;
	                }
	                if (submenu.style.display == 'none') {
	                    submenu.style.display = 'block';
	                }
	                else {
	                    submenu.style.display = 'none';
	                }
	            }
            }
        }
    }
    this.fireOpenEvent = function(treeNode) {
        if (treeNode.gotOpenEventListeners()) {
            for(var i=0;i<treeNode.openeventlisteners.length;i++) {
                eval(treeNode.openeventlisteners[i] + '(' + treeNode.getID() + ');');
            }
        }
    }
    this.unHighlightNodes = function() {
    	this.unfocusSelection();
    	for(var i = 0; i < this.highlightedNodes.length; ++i) {
    		//alert("unHighlighting " + this.treeName + " node " + this.highlightedNodes[i].getID());
    		this.highlightedNodes[i].titleElement.className = 'treetitle';	
    	}	
    	this.highlightedNodes=new Array();
    }
    this.highlightNode = function(treeNode) {
    	this.unfocusSelection();
   	    var parentNode = treeNode.getParent();
        if(parentNode != null && treeNode.titleElement.className != 'treetitlehighlighted')  {
        	//alert("highlighting " + this.treeName + " node " + treeNode.getID());
	        treeNode.titleElement.className = 'treetitlehighlighted';
			this.highlightedNodes.push(treeNode);        
	        if(this.checkUp) {
            	this.highlightNode(parentNode); 
            }
        }
    }
    this.unfocusSelection = function() {
        if (this.selectedTreeNodeID != null) {
            var oldTreeNodeTitle = document.getElementById(this.treeName+'Title' + this.selectedTreeNodeID);
            //alert("unfocusing " + this.treeName+'Title' + this.selectedTreeNodeID);
            oldTreeNodeTitle.className = 'treetitle';
            this.selectedTreeNodeID = null;
        }
    }
    this.focusSelection = function() {
        if (this.selectedTreeNodeID != null) {
            //alert("focusing " + this.treeName+'Title' + this.selectedTreeNodeID);
            var treeNodeTitle = document.getElementById(this.treeName+'Title' + this.selectedTreeNodeID);
            treeNodeTitle.className = 'treetitleselected';
        }
    }
    this.getCookieVal = function(offset) {
        var endstr = document.cookie.indexOf (";",offset);
        if (endstr == -1) {
            endstr = document.cookie.length;
        }
        return unescape(document.cookie.substring(offset,endstr));
    }
    this.getCookie = function(name) {
        var arg = name + "=";
        var alen = arg.length;
        var clen = document.cookie.length;
        var i = 0;
        while (i < clen) {
            var j = i + alen;
            if (document.cookie.substring(i, j) == arg) {
                return this.getCookieVal(j);
            }
            i = document.cookie.indexOf(" ", i) + 1;
            if (i == 0) {
                break;
            }
        }
        return null;
    }
    this.setCookie = function(name, value) {
        var argv = this.setCookie.arguments;
        var argc = this.setCookie.arguments.length;
        var expires = (argc > 2) ? argv[2] : null;
        var path = (argc > 3) ? argv[3] : null;
        var domain = (argc > 4) ? argv[4] : null;
        var secure = (argc > 5) ? argv[5] : false;
        document.cookie = name + "=" + escape (value) + ((expires == null) ? "" : ("; expires=" + expires.toGMTString())) + ((path == null) ? "" : ("; path=" + path)) + ((domain == null) ? "" : ("; domain=" + domain)) + ((secure == true) ? "; secure" : "");
    }
    this.expandTreeNode = function() {
        var state = this.getState(this.selectedTreeNodeID);
        if (state == 'open') {
            var currentTreeNode = this.getTreeNode(this.selectedTreeNodeID);
            if (currentTreeNode.hasChildren()) {
                this.selectTreeNode(currentTreeNode.children[0].getID());
            }
        }
        else {
            this.handleTreeNode(this.selectedTreeNodeID);
        }
    }
    this.subtractTreeNode = function() {
        var state = this.getState(this.selectedTreeNodeID);
        if (state == 'closed') {
            var currentTreeNode = this.getTreeNode(this.selectedTreeNodeID);
            var parent = currentTreeNode.getParent();
            if (parent != null && parent != currentTreeNode.getRootNode()) {
                this.selectTreeNode(parent.getID());
            }
        }
        else {
            this.handleTreeNode(this.selectedTreeNodeID);
        }
    }
    this.selectPrevTreeNode = function() {
        var currentTreeNode = this.getTreeNode(this.selectedTreeNodeID);
        if (currentTreeNode.prevSibling != null) {

            var state = this.getState(currentTreeNode.prevSibling.getID());

            if (state == 'open' && currentTreeNode.prevSibling.hasChildren()) {
                // We have to find the last open child of the previoussiblings children.
                var current = currentTreeNode.prevSibling.children[currentTreeNode.prevSibling.children.length - 1];
                var currentstate = 'open';
                while (current.hasChildren() && (this.getState(current.getID()) == 'open')) {
                    current = current.children[current.children.length - 1];
                }
                this.selectTreeNode(current.getID());
            }
            else {
                this.selectTreeNode(currentTreeNode.prevSibling.getID());
            }
        }
        else {
            if (currentTreeNode.getParent() != null && currentTreeNode.getParent() != currentTreeNode.getRootNode()) {
                this.selectTreeNode(currentTreeNode.getParent().getID());
            }
        }
    }
    this.selectNextTreeNode = function() {
        var currentTreeNode = this.getTreeNode(this.selectedTreeNodeID);

        var state = this.getState(this.selectedTreeNodeID);
        if (state == 'open' && currentTreeNode.hasChildren()) {
            this.selectTreeNode(currentTreeNode.children[0].getID());
        }
        else {
            if (currentTreeNode.nextSibling != null) {
                this.selectTreeNode(currentTreeNode.nextSibling.getID());
            }
            else {
                // Continue up the tree until we either hit null, or a parent which have a child.
                var parent = currentTreeNode;
                while ((parent = parent.getParent()) != parent.getRootNode()) {
                    if (parent.nextSibling != null) {
                        this.selectTreeNode(parent.nextSibling.getID());
                        break;
                    }
                }
            }
        }
    }
    this.checkboxClick = function(nodeID)
    {
        var treeNode = this.getTreeNode(nodeID);
        if (treeNode==null || typeof treeNode=='undefined') {
            return;
        }
        var checkState = treeNode.getCheckState();
        treeNode.setCheckState(checkState, true);
        var parentNode = treeNode.getParent();
        if(parentNode != null) {
            parentNode.checkParents(checkState);
        }
        treeNode.checkChildren(checkState);
        this.writeStates();
        if(treeNode.getCheckHandler() != null) {
            eval( treeNode.getCheckHandler() + '(' + this.treeName + '.getTreeNode(' + treeNode.getID() + '));');
        }
        else if(typeof(standardCheck) != "undefined") {
            this.standardCheck(treeNode);
        }
    }
    this.keyDown = function(event) {
        //alert(this.treeName);        
        if (window.event) {
            event = window.event;
        }
        if (event.keyCode == 38) { // Up
            this.selectPrevTreeNode();
            return false;
        }
        else if (event.keyCode == 40) { // Down
            this.selectNextTreeNode();
            return false;
        }
        else if (event.keyCode == 37) { // left
            this.subtractTreeNode();
            return false;
        }
        else if (event.keyCode == 39) { // right
            this.expandTreeNode();
            return false;
        }
    }
}

/**
* The TreeNode Object
* @param id unique id of this treenode
* @param name The title of this node
* @param icon The icon if this node (Can also be an array with 2 elements, the first one will represent the closed state, and the next one the open state)
*/
function TreeNode(id,name,icon) {
    this.id = id;
    this.children = new Array();
    this.name = (name == null ? 'unset name' : name);
    this.icon = (icon == null ? '' : icon);
    this.parent = null;
    this.handler = null;
    this.extra = null;
    this.checkboxParam = null;
    this.checkHandler = null;
    this.myRootNode = null;
    this.myTree = null;

    this.openeventlisteners = new Array();
    this.linestring = '';
    this.checkable = true;
    this.grayed = false;
    this.underlined = false;

    this.nextSibling = null;
    this.prevSibling = null;

    // Checkbox element associated with this node
    this.checkboxElement = null;
    this.titleElement = null;
    this.submenuElement = null;
    this.actionimageElement = null;
    this.iconimageElement = null;
    this.extraSubmenuElements = new Array();

    this.getID = function() {
        return this.id;
    }
    this.setName = function(newname) {
        this.name = newname;
    }
    this.getName = function() {
        return this.name;
    }
    this.setExtra = function(extraIndex,extraItem) {
        if(this.extra == null) {
            this.extra = new Array();
        }
        this.extra[extraIndex] = extraItem;
    }
    this.getExtra = function(extraIndex) {
        if(this.extra == null) {
            return '';
        }
        if(this.extra.length <= extraIndex) {
            return '';
        }
        return this.extra[extraIndex];
    }
    this.setIcon = function(icon) {
        this.icon = icon;
    }
    this.getIcon = function() {
        if (typeof(this.icon) == 'object') {
            return this.icon[0];
        }
        return this.icon;
    }
    this.getOpenIcon = function() {
        if (typeof(this.icon) == 'object') {
            return this.icon[1];
        }
        return this.icon;
    }
    this.hasIcon = function () {
        return this.icon != '';
    }
    // @param checkboxParam If specified, a checkbox with the given param(s) 
    //        (such as name="foo" or "checked") will be inserted into the checkbox declaration. 
    //        Please note that id, and onClick are already set
    this.addCheckbox = function (checkboxParam) {
        this.checkboxParam = (checkboxParam == null ? 'name="CB' + this.getID() + '"' : checkboxParam);
    }
    this.getCheckboxId = function() {
        if(this.checkboxParam != null) {
            return 'checkbox' + this.getID();
        }
        return null;
    }
    this.getCheckboxParam = function() {
        return this.checkboxParam;
    }
    this.hasCheckbox = function () {
        return this.checkboxParam != null;
    }
    this.setCheckHandler = function(checkHandler) {
        this.checkHandler = checkHandler;
    }
    this.getCheckHandler = function() {
        return this.checkHandler;
    }
    this.setRootNode = function(myRootNode)
    {
        this.myRootNode = myRootNode;
    }
    this.getRootNode = function()
    {
        return this.myRootNode;
    }
    this.setTree = function(myTree)
    {
        this.myTree = myTree;
    }
    this.getTree = function()
    {
        return this.myTree;
    }
    this.addOpenEventListener = function(event) {
        this.openeventlisteners[this.openeventlisteners.length] = event;
    }
    this.gotOpenEventListeners = function() {
        return (this.openeventlisteners.length > 0);
    }

    this.removeChild = function(childTreeNode) {
        var found = false;
        for (var i=0;i<this.children.length;i++) {
            if (found) {
                this.children[i] = this.children[i + 1];
            }
            if (this.children[i] == childTreeNode) {
                if (i == (this.children.length - 1)) {
                    this.children[i] = null;
                }
                else {
                    this.children[i] = this.children[i + 1];
                }
                found = true;
            }
        }
        if (found) {
            this.children.length = this.children.length-1;
        }
    }
    this.hasChildren = function() {
        return (this.children.length > 0);
    }
    this.hasCheckableChildren = function() {
        var someCheckable = false;
        for(var i = 0; i < this.children.length; ++i) {
            if(this.children[i].isCheckable()) {
                someCheckable = true;
                break;
            }
        }
        return someCheckable;
    }
    this.hasUnGrayedChildren = function() {
        var someUnGrayed = false;
        for(var i = 0; i < this.children.length; ++i) {
            if(!this.children[i].isGrayed()) {
                someUnGrayed = true;
                break;
            }
        }
        return someUnGrayed;
    }
    this.hasUnderlinedChildren = function() {
        var someUnderlined = false;
        for(var i = 0; i < this.children.length; ++i) {
            if(this.children[i].isUnderlined()) {
                someUnderlined = true;
                break;
            }
        }
        return someUnderlined;
    }
    this.getChildCount = function() {
        return this.children.length;
    }
    this.getFirstChild = function() {
        if (this.hasChildren()) {
            return this.children[0];
        }
        return null;
    }
    this.gotHandler = function() {
        return this.handler != null;
    }
    this.setHandler = function(handler) {
        this.handler = handler;
    }
    this.getHandler = function() {
        return this.handler;
    }
    this.setParent = function(parent) {
        this.parent = parent;
        this.myRootNode = parent.getRootNode();
        this.myTree = parent.getTree();
    }
    this.getParent = function() {
        return this.parent;
    }
    this.addChild = function(childTreeNode) {
        var possiblePrevTreeNode = this.children[this.children.length - 1]
        if (possiblePrevTreeNode) {
            possiblePrevTreeNode.nextSibling = childTreeNode;
            childTreeNode.prevSibling = possiblePrevTreeNode;
        }
        
        this.myTree.addTreeNode(childTreeNode);
        
        this.children[this.children.length] = childTreeNode;
        childTreeNode.setParent(this);

    }
    this.getLineString = function() {
        return this.linestring;
    }
    this.setLineString = function(string) {
        this.linestring = string;
    }
    this.isCheckable = function() {
        return this.checkable;
    }
    this.setCheckable = function(checkable) {
        this.checkable = checkable;
        this.setParentCheckable(checkable);
        if(this.parent==null || this.parent.getID() == this.myRootNode.getID()) {
            //alert("Calling setChildCheckable()");
            this.setChildCheckable(checkable)
            //showTreeNode(this);
        }
    }
    this.setParentCheckable = function(checkable) {
        if(this.hasCheckbox()) {
             if(this.checkboxElement != null) {
                this.checkable = checkable;
                this.checkboxElement.disabled = !checkable;
            }
        }
        if(this.myTree.checkUp) {
            if(this.parent!=null && this.parent.getID() != this.myRootNode.getID() && this.parent.isCheckable()!=checkable) {
                var someCheckable = this.parent.hasCheckableChildren();
                this.parent.setParentCheckable(someCheckable);
            }
        }
    }
    this.setChildCheckable = function(checkable) {
        if(this.hasCheckbox()) {
            if(this.checkboxElement != null) {
                this.checkable = checkable;
                this.checkboxElement.disabled = !checkable;
            }
        }
        if(this.myTree.checkDown) {
            for(var i = 0; i<this.children.length; ++i) {
                if( this.children[i].isCheckable() != checkable)
                {
                    this.children[i].setChildCheckable(checkable);
                }
            }
        }
    }
    this.isGrayed = function() {
        return this.grayed;
    }
    this.setGrayed = function(grayed) {
        this.setParentGrayed(grayed);
        if(this.parent==null || this.parent.getID() == this.myRootNode.getID()) {
            this.setChildGrayed(grayed);
        }
    }
    this.setParentGrayed = function(grayed) {
        if(this.grayed != grayed) {
            this.grayed = grayed;
            this.titleElement.style.color = grayed ? "gray" : "black";
            //title.style.fontWeight = grayed ? "lighter" : "normal";
            this.titleElement.style.fontStyle = grayed ? "italic" : "normal";            
        }
        if(this.myTree.checkUp) {
            if(this.parent!=null && this.parent.isGrayed()!=grayed) {
                var someUnGrayed = this.parent.hasUnGrayedChildren();
                this.parent.setParentGrayed(!someUnGrayed);
            }
        }
    }
    this.setChildGrayed = function(grayed) {
        if(this.grayed != grayed) {
            this.grayed = grayed;
            this.titleElement.style.color = grayed ? "gray" : "black";
            //title.style.fontWeight = grayed ? "lighter" : "normal";
            this.titleElement.style.fontStyle = grayed ? 'italic' : 'normal';            
        }
        if(this.myTree.checkDown) {
            for(var i = 0; i<this.children.length; ++i) {
                if( this.children[i].isGrayed() != grayed)
                {
                    this.children[i].setChildGrayed(grayed);
                }
            }
        }
    }
    this.isUnderlined = function() {
        return this.underlined;
    }
    this.setUnderlined = function(underlined) {
        this.setParentUnderlined(underlined);
        if(this.parent==null || this.parent.getID() == this.myRootNode.getID()) {
            this.setChildUnderlined(underlined);
        }
    }
    this.setParentUnderlined = function(underlined) {
        if(this.underlined != underlined) {
            this.underlined = underlined;
            this.titleElement.style.textDecoration = underlined ? 'underline' : 'none';            
        }
        if(this.myTree.checkUp) {
            if(this.parent!=null && this.parent.isUnderlined()!=underlined) {
                var someUnderlined = this.parent.hasUnderlinedChildren();
                this.parent.setParentUnderlined(someUnderlined);
            }
        }
    }
    this.setChildUnderlined = function(underlined) {
        if(this.underlined != underlined) {
            this.underlined = underlined;
            this.titleElement.style.textDecoration = underlined ? 'underline' : 'none';            
        }
        if(this.myTree.checkDown) {
            for(var i = 0; i<this.children.length; ++i) {
                if( this.children[i].isUnderlined() != underlined)
                {
                    this.children[i].setChildUnderlined(underlined);
                }
            }
        }
    }
    this.getCheckState = function() {
        if(this.hasCheckbox()) {
            if(this.checkboxElement == null) {
                return false;
            }
            if(typeof(this.checkboxElement.checkState) != 'undefined')
            {
                return this.checkboxElement.checkState
            }
            if(typeof(this.checkboxElement.indeterminate) != 'undefined' && this.checkboxElement.indeterminate) {
                return 2;
            }
            return this.checkboxElement.checked ? 1:0;
        }
        return 0;
     }
    this.setCheckState = function(checkState, updateStates) {
        if(this.hasCheckbox()) {
            if(this.checkboxElement != null) {
                if(typeof(this.checkboxElement.checkState) != 'undefined')
                {
                    this.checkboxElement.checkState = checkState
                }
                else if(typeof(this.checkboxElement.indeterminate) != 'undefined') {
                    this.checkboxElement.checked = checkState == 1;
                    this.checkboxElement.indeterminate = checkState == 2;
                }
                else {
                    this.checkboxElement.checked = checkState == 1;
                }
            }
            if(updateStates == true) {
                this.myTree.setCheckState(this.getID(),checkState);
            }
        }
     }
    this.checkChildren = function(checkState) {
        if(this.myTree.checkDown) {
            if(this.hasChildren()) {
                for (var i = 0; i < this.children.length; ++i) {
                    var childTreeNode = this.children[i];
                    if (childTreeNode==null || !childTreeNode.hasCheckbox()) continue;
                    childTreeNode.setCheckState(checkState, true);
                    childTreeNode.checkChildren(checkState);
                }
            }
        }
    }
    this.checkParents = function(checked) {
        if(this.myTree.checkUp) {
            var allChecked = false;
            var someChecked = false;
            if(this.hasChildren()) {
                allChecked = true;
                for (var i = 0; i < this.children.length; ++i) {
                    var childTreeNode = this.children[i];
                    if (childTreeNode==null || !childTreeNode.hasCheckbox()) continue;
                    if(childTreeNode.getCheckState()  > 0) {
                        someChecked = true;
                    }
                    if(childTreeNode.getCheckState() != 1) {
                        allChecked = false;
                    }
                }
            }
            if(allChecked) {
                this.setCheckState(1, true);
            }
            else if(someChecked) {
                this.setCheckState(2, true);
            }
            else {
                this.setCheckState(0, true);
            }
            parentNode = this.getParent() ;
            if(this != this.myRootNode && this.parentNode != null) {
                parentNode.checkParents();
            }
        }
    }
}
