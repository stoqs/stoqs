// This is a wrapper for a collection of radio buttons sharing the same name

function Radio(radioName) {
	
	this.elements = document.getElementsByName(radioName);
	this.length = 0;
	if(typeof(this.elements.length) != "undefined" ) {
		this.length = this.elements.length;
	}

	this.setChecked = function(){
		this.setCheckedIndex(0);
	}

	this.setCheckedId = function(id){
		if(this.length) {
			for(var i=0; i<this.length; ++i){
				if(this.elements[i].id==id){
					this.elements[i].checked=true;
				}	
			}
		}
		else {
			if(this.elements.id==id){
				this.elements.checked=true;
			}
		}
	}
	
	this.getCheckedId = function(){
		if(this.length) {
			for(var i=0; i<this.length; ++i){
				if(this.elements[i].checked){
					return this.elements[i].id;
				}	
			}
		}
		else {
			if(this.elements.checked){
				return this.elements.id;
			}
		}
		return null;
	}
	
	this.setCheckedValue = function(value){
		if(this.length) {
			for(var i=0; i<this.length; ++i){
				if(this.elements[i].value==value){
					this.elements[i].checked=true;
				}	
			}
		}
		else {
			if(this.elements.value==value){
				this.elements.checked=true;
			}
		}
	}
	
	this.getCheckedValue = function(){
		if(this.length) {
			for(var i=0; i<this.length; ++i){
				if(this.elements[i].checked){
					return this.elements[i].value;
				}	
			}
		}
		else {
			if(this.elements.checked){
				return this.elements.value;
			}
		}	
		return null;
	}
	
	this.setCheckedIndex = function(index){
		if(this.length) {
			if(this.length>index && index>=0){
				this.elements[index].checked=true;
			}
		}
		else {
			if(index==0){
				this.elements.checked=true;
			}
		}	
	}
	
	this.getCheckedIndex = function(){
		if(this.length) {
			for(var i=0; i<this.length; ++i){
				if(this.elements[i].checked){
					return i;
				}	
			}
		}
		else {
			if(this.elements.checked){
				return 0;
			}
		}
		return null;
	}
}
