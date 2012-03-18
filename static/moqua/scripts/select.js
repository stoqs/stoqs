// this is a wrapper for a select element containing option elements

function Select(selectId) {
	
	// private
	var element = document.getElementById(selectId);

	// replacementArray is an array of ojects with value="foo", label="bar"
	// defaultEmpty is the first item in the list if replacementArray is empty
	// defaultList is the first item in the list if replacementArray is not empty
    // if retainValue is true, the item in replacementArray with a value equal to the
    //    currently selected value is selected -- if no match, then the first option
    //    is selected.  If false, then no option is selected.
    // returns: true if selected value retained. false if changed
	this.replaceOptions = function(replacementArray, defaultEmpty, defaultList, retainValue) {
		var selectedValue = this.getSelectedValue();	
		element.length=0;
		var selected = false;
		if(replacementArray != null && replacementArray.length > 0) {
			if(defaultList!=null && defaultList.length > 0)  {
				element.options[0] = new Option(defaultLabel);
			}
			for(var i=0; i < replacementArray.length; ++i) {
				var newOption = new Option(replacementArray[i].label);
				newOption.value = replacementArray[i].value;
				if(retainValue && !selected && newOption.value == selectedValue) {
					selected = true;
					newOption.selected=true;
				}
				element.options[element.length] = newOption;
			}
		}
		else {
			if(defaultEmpty!=null && defaultEmpty.length > 0)  {
				element.options[0] = new Option(defaultEmpty);
			}
		}
		if(retainValue && !selected && element.length > 0) {
			element.options[0].selected = true;
		}
		return selected;
	}
	
	this.getSelectedValue = function() {
		for(var i = 0; i < element.length; ++i) {
			if(element.options[i].selected==true) {
				return element.options[i].value;
			}
		}
	}
	
	this.getSelectedIndex = function() {
		for(var i = 0; i < element.length; ++i) {
			if(element.options[i].selected==true) {
				return i;
			}
		}
	}

	this.setSelectedValue = function(value) {
		for(var i = 0; i < element.length; ++i) {
			if(element.options[i].value == value) {
				element.options[i].selected==true;
				break;
			}
		}
	}
	
	this.setSelectedIndex = function(index) {
		if(element.length > index) {
			element.options[index].selected==true;
		}
	}
}
	