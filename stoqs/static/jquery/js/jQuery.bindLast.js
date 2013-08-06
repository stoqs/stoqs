;(function($) {
	$.extend($.fn, {
		bindLast: function(event, cbFunc){
			return this.each(function(){
				var highIndex = 1000000;
				var eventData = event.split('.');
				var eventName = eventData[0];
				
				$(this).bind(event, cbFunc);
				
				var events = $(this).data('events'),
					ourIndex = false,
					usedIndicies = {};
				
				$.each(events[eventName], function(index, func){
					if(func === cbFunc){
						ourIndex = index;
					}
					
					usedIndicies[index] = 1;
				});
				
				if(ourIndex !== false){
					while(usedIndicies[highIndex] == 1){
						highIndex++;
					}
					
					events[eventName][highIndex] = events[eventName][ourIndex];
					delete events[eventName][ourIndex]
					
					$(this).data('events', events);
				}
			});
		}
	});
})(jQuery);
