var xmlhttp = {

	xmlRequestArray : new Array(),
	
	// Remote call generator
	doCallBack : function(serverObjectUrl, serverMethodName, returnContentType, clientEventHandler, clientEventHandlerParams, isAsynchronous, serverParams)
	{
		var xmlRequest = this.getXmlRequestObject();
		if(xmlRequest != null)
		{
			var url = serverObjectUrl + (serverObjectUrl != null && serverObjectUrl.length > 0 ? "/" : "" ) + serverMethodName;
			xmlRequest.open("POST", url, isAsynchronous);
	 		xmlRequest.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
	  	 	xmlRequest.setRequestHeader("ReturnContentType", returnContentType);
	   	 	try
	   	 	{
	   	 		if(serverParams != null)
	    		{
	    	 		var params = new String();
	   	  			for(i=0; serverParams.length > i; ++i)
	   	  			{
	   	  	 			if(params.length > 0)
	   	   			 		params = params.concat("&");
	   	  				params = params.concat(serverParams[i].pName + "=" + serverParams[i].pValue);
	   	  			}
	    	  		xmlRequest.send(params);
	   	  		}
	   	  		else {
	   	  			xmlRequest.send(null);
	   	  		}
				if(isAsynchronous)
				{
					var index = this.xmlRequestArray.length;
	 				this.xmlRequestArray[index] = {xmlRequest: xmlRequest, index : index};
	   	 			this.xmlRequestArray[index].xmlRequest.onreadystatechange = this.makeOnReadyStateChangeHandler(this.xmlRequestArray[index], clientEventHandler, clientEventHandlerParams);
				}
				else
				{
					clientEventHandler(xmlRequest.responseText, clientEventHandlerParams);
				}
			}
			catch (e)
			{
				alert(e);
			}
		}
	},

	getXmlRequestObject : function() {
		// Do we support the request natively (eg, Mozilla, Opera, Safari, Konqueror)
		if (window.XMLHttpRequest != null) {
			return new XMLHttpRequest ();
		} else {
			// Look for a supported IE version
			// List of Microsoft XMLHTTP versions - newest first
			var MSXML_XMLHTTP_PROGIDS = new Array (
				'MSXML2.XMLHTTP.5.0',
				'MSXML2.XMLHTTP.4.0',
				'MSXML2.XMLHTTP.3.0',
				'MSXML2.XMLHTTP',
				'Microsoft.XMLHTTP'
			);
			for (i = 0; MSXML_XMLHTTP_PROGIDS.length > i; i++) {
				try {
					return new ActiveXObject (MSXML_XMLHTTP_PROGIDS[i]);
				}
				catch (e) {}
			}
		}
	},
		
	// Helper function to remove processed asynchronous xmlRequests from the xmlRequestArray array
	removeArrayItemByIndex : function(array, index)
	{ 
	    return array.slice(0,index-1).concat(array.slice(index+1)); 
	},

	makeOnReadyStateChangeHandler : function(object, clientEventHandler, clientEventHandlerParams)
	{
		return function()
		{
	 		if (object.xmlRequest.readyState == 4 && (object.xmlRequest.status == 200 || object.xmlRequest.status == 201))
	 		{	
	 			clientEventHandler(object.xmlRequest.responseText, clientEventHandlerParams);
	 	  		xmlhttp.xmlRequestArray = xmlhttp.removeArrayItemByIndex(xmlhttp.xmlRequestArray, object.index);
	 		}
	 	}
	}	
}

