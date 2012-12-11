//Push update for ticker
var pusher = new Pusher('b2c9525770d59267a6a2');
var channel = pusher.subscribe('prod_ticker');
var datat
channel.bind('ticker', function(data) {
	console.log(data)
	$.each(data, function(i, player){
		eventMsg =  '<li class="pushmsg"><p><span class="player-name" pid ="'+player.pid+'">'+player.playername+'</span>'+player.msg+'</p></li>'
		$(eventMsg).prependTo('#update').hide();
		$('li').show(600);
	});
	// playerHiglight();
	tickerOverflow();
	// var audio = $("#ding")[0];
	// if (sound == true){
	// 	audio.play();
	// }
});

// SOUND
var sound = true;
$('#sound').click(function(){
	if (sound == true){
		$(this).removeClass("icon-volume-up").addClass("icon-volume-off")
		sound = false;
	}
	else{
		$(this).removeClass("icon-volume-off").addClass("icon-volume-up")
		sound = true;
	}
});

// Fix tickerOverlofw
function tickerOverflow() {
	if ($('#update li').length >= 5) {
		$('.ticker-container').attr('style', 'overflow-y:scroll;');
	}
	if ($('#update li').length >= 1) {
		$('#ticker h4').html('Latest Updates');
	}
};

// //Hover playername highlight team
// function playerHiglight(){
// 	$('#update li').hover(function(){
// 		playerId = $(this).find('span').attr("pid");
// 		$("#xtable tbody td[data-lineup*='"+playerId+"']").parent().css("background-color","#d9edf7");
// 		},
// 		function(){
// 			$("#xtable tbody td[data-lineup*='"+playerId+"']").parent().css("background-color","");
// 	});
// };


// //Hover playername highlight team
// function playerHiglightH2h(){
// 	$('#update li').hover(function(){
// 		playerId = $(this).find('span').attr("pid");
// 		$(".team").each(function(){
// 			lineup = $(this).attr('data-lineup').split(',')
// 			$.each(lineup,function(i,id){
// 				if (parseInt(id) == parseInt(playerId)){
// 					console.log("tru")
// 					$(this).addClass('highlight')
// 				}
// 			});
// 		});
// 	}
// 	);
// }
