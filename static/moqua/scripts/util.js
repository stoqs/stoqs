var util = {

	compareNum : function (a,b){
	    return a===b?0:(a<b?-1:1);
	},
		
	compareNode : function(node1,node2) {
		if(node1 == null) {
			if(node2 == null) return 0;
			return -1;
		}
		if(node2 == null) {
			return 1;
		}
    	var id1 = node1.id;
    	var id2 = node2.id;
    	return id1===id2?0:(id1<id2?-1:1);
  	},
		
	toTimeString : function(timeCode, truncate) {
	    theDate = new Date(timeCode);
	    var year = (theDate.getYear()+(theDate.getYear() < 1000 ? 1900 : 0)) + "-";
	    var month = "0" + (theDate.getMonth()+1) + "-";
	    var day = "0" + theDate.getDate();
	    var hours = "0" + theDate.getHours() + ":";
	    var minutes = "0" + theDate.getMinutes() + ":";
	    var seconds = "0" + theDate.getSeconds();
	    
	    var outString = year + month.substring(month.length-3,month.length) + 
	                   day.substring(day.length-2,day.length);
	    if(!truncate || hours!="00:" || minutes!="00:" || seconds!="00") {
	        outString += " " + hours.substring(hours.length-3,hours.length) +
	                        minutes.substring(minutes.length-3,minutes.length) +
	                        seconds.substring(seconds.length-2,seconds.length);
	    }
	    return outString;
	},
	
	uniqueSort : function(inputArray,compare_function,minUnique) {
		if(minUnique==null) minUnique = 1;
	    inputArray.sort(compare_function);
	    var outputArray = new Array();
	    var lastElement = null;
		unique = 0;
	    for(i=0; i < inputArray.length; ++i) {
	        var element = inputArray[i];
	        if(compare_function(lastElement, element) == 0) {
	        	unique += 1;
	        }
	        else {
	        	unique = 1;
	        }
	        if(unique == minUnique) {
	            outputArray.push(element);
	        }
	        lastElement = element;
		}			
	    return outputArray;
	}
}
