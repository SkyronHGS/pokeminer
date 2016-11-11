/*
	Inspired by Devsome
	More inspiration for this branch from imDevinC and modrzew
*/

const Discord = require("discord.js");
var request = require("request");
var fs = require("fs");
var XMLHttpRequest = require("xmlhttprequest").XMLHttpRequest;

// Loading my Configs
var config = require("./config_bot.json");

const clientBot = new Discord.Client();

var joinUrl = "https://discordapp.com/oauth2/authorize?client_id=" + config.app_id + "&scope=bot&permissions=";

// required for listing pokemon names
var locale = require("./locales/pokemon."+config.locale+".json");
// tracks already sighted pokemon
var alreadySeen = [];

clientBot.on("ready", function () {
	console.log("\n[INFO]\tTo add me visit this url:\n\t" + joinUrl + "\n\n");
	console.log("[INFO]\tReady to begin!");
    config.connectionMessagesChannelIDs.forEach(function(entry) {
        const channel = clientBot.channels.find('id', entry);
        if (channel) {
            channel.sendMessage("I'm online now!");
        } else {
            console.log('Error: Bot not allowed in channel');
        }
    });
});

clientBot.on('disconnected', function() {
	console.log("Disconnted ? Let me reconnect asap...");
	clientBot.loginWithToken(config.token);
});

clientBot.on("error", function (error) {
	console.log("Caught error: " + error);
});

// CMD+C at terminal
process.on("SIGINT", function () {
	console.log("\n Whoa wait, let me logout first...");
    config.connectionMessagesChannelIDs.forEach(function(entry) {
        const channel = clientBot.channels.find('id', entry);
        if (channel) {
        	channel.sendMessage("I'm disconnecting!");
        } else {
        	console.log('Error: Bot not allowed in channel');
        }
    });
    clientBot.destroy().then(function(){
        process.exit();
    });
});

function reloadConfig() {
	config = require("./config_bot.json");
}

function isMod(msg)
{
	var roles = msg.member.roles;
    if (roles.exists("name", config.modName))
    {
        return true;
    }
    else
    {
        msg.channel.sendMessage("Permission denied");
    }
    return false;
}

function helpMessage(msg)
{
    var commands = [];
    commands.push("General Use:");
    commands.push("!HELP");
    commands.push("!ECHO");
    commands.push("!LIST");
    commands.push("!LISTRARE");
    commands.push("!LISTFAV");
    commands.push("!LISTFAVIVTHRESH");
    commands.push("!LISTGENIVTHRESH");
    commands.push("!POKEDEX 16/pidgey");
    commands.push("");
    commands.push(config.modName + " Only:");
    commands.push("!ADD 16/pidgey");
    commands.push("!ADDRARE 16/pidgey");
    commands.push("!ADDFAV 16/pidgey");
    commands.push("!REMOVE 16/pidgey");
    commands.push("!REMOVERARE 16/pidgey");
    commands.push("!REMOVEFAV 16/pidgey");
    commands.push("!SETFAVIVTHRESH 82");
    commands.push("!SETGENIVTHRESH 97");
    commands.push("!CLEARCHAT 98");
    msg.channel.sendMessage(commands);
}

function clearChat(msg)
{
    if (isMod(msg))
    {
        if (msg.contentAll.length > 1)
        {
            var numberToDelete = parseInt(msg.contentAll[1]) + 2;
            if (!isNaN(numberToDelete))
            {
                var wasLargerThanOneHundred = false;
                if (numberToDelete > 100)
                {
                    wasLargerThanOneHundred = true;
                    numberToDelete = 100;
                }
                msg.channel.sendMessage("Clearing chat");
                msg.channel.fetchMessages({limit: numberToDelete})
                .then(function(messages)
                      {
                      msg.channel.bulkDelete(messages);
                      })
                .catch(function(error) {
                       msg.channel.sendMessage("Error clearing chat");
                       });
                if (wasLargerThanOneHundred)
                {
                    msg.channel.sendMessage("Can't clear more than 98 messages at a time!");
                }
            }
            else
            {
                msg.channel.sendMessage("Not a valid number");
            }
        }
        else {
            msg.channel.sendMessage("No parameter detected");
        }
    }
}

clientBot.on("message", function (msg) {
	if(msg.author.id != clientBot.user.id && msg.content[0] == '!' && msg.channel.type === 'text')
    {
		var messageContentAll = msg.content.toUpperCase().split(" ");
        msg.contentAll = messageContentAll;
		var command = messageContentAll[0];
		var userRoles = msg.member.roles;

		if(command == "!ECHO")
		{
			msg.channel.sendMessage("I hear you!");
		}
		else if (command === "!HELP")
		{
			helpMessage(msg);
		}
		else if (command === "!CLEARCHAT")
		{
			clearChat(msg);
		}
		else if (command === "!POKEDEX")
		{
			printPokemon(msg);
		}
		else if (command === "!LIST")
		{
			list(msg);
		}
		else if (command === "!LISTRARE")
		{
			listRare(msg);
		}
		else if (command === "!ADD")
		{
			add(msg);
		}
		else if (command === "!ADDRARE")
		{
			addRare(msg);
		}
		else if (command === "!REMOVE")
		{
		remove(msg);
		}
		else if (command === "!REMOVERARE")
		{
			removeRare(msg);
		}
		else if (command === "!LISTFAV")
		{
			listFav(msg);
		}
		else if (command === "!ADDFAV")
		{
			addFav(msg);
		}
		else if (command === "!REMOVEFAV")
		{
			removeFav(msg);
		}
		else if (command === "!SETFAVIVTHRESH")
		{
			setIVThresh(msg, "FAV");
		}
		else if (command === "!LISTFAVIVTHRESH")
		{
			listIVThresh(msg, "FAV");
		}		
		else if (command === "!SETGENIVTHRESH")
		{
			setIVThresh(msg, "GEN");
		}
		else if (command === "!LISTGENIVTHRESH")
		{
			listIVThresh(msg, "GEN");
		}		
		else
		{
			msg.channel.sendMessage("Invalid Command");
		}
	}
});

function setIVThresh(msg, favOrGen) {
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var number = parseInt(msg.contentAll[1]);
			if (number <= 100 && number >= 0 && number != NaN)
			{
				var config = require( __dirname + '/config_bot.json' );
				var type = "";
				if (favOrGen == "FAV")
				{
					type = "Favorite"
					config.favoriteIVRequirement = number;
				}
				else if (favOrGen == "GEN")
				{
					type = "General"
                        	        config.generalIVRequirement = number;
                	        }
				fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				delete require.cache[ __dirname + '/config_bot.json' ]
				msg.channel.sendMessage(type + " IV threshold set successfully to " + msg.contentAll[1] + "%");
				reloadConfig();
			}
			else {
                        	msg.channel.sendMessage("IV threshold must be 0-100");
                	}
		}
		else {
			msg.channel.sendMessage("No parameter detected");
		}
	}
	
}
function listIVThresh(msg, favOrGen) {
	var config = require( __dirname + '/config_bot.json' );
	var type = "";
	var number = "-1";
	if (favOrGen == "FAV")
	{
		type = "Favorite";
		number = config.favoriteIVRequirement.toString();
	}
        else if (favOrGen == "GEN")
        {
		type = "General";
		number = config.generalIVRequirement.toString();
        }
	var result = type + " IV Threshold: " + number + "%";
	msg.channel.sendMessage(result);
}

function list(msg)
{
	var config = require( __dirname + '/config_bot.json' );
	var result = [];
	result.push("All pokemon being notified for:");
	for (var i = 0; i < config.pokeShow.length; i++)
	{
		var pokemonInfo = getPokemonInfoFromNumber(config.pokeShow[i]);
		if (pokemonInfoValid(pokemonInfo))
		{
			result.push(pokemonInfo[0].toString() + ": " + pokemonInfo[1]);
		}
		else
		{
			console.log("error listing");
		}
	}
	msg.channel.sendMessage(result);
}
function listFav(msg)
{
	var config = require( __dirname + '/config_bot.json' );
	var result = [];
	result.push("All favorite pokemon being notified for:");
	for (var i = 0; i < config.pokeShowFaves.length; i++)
	{
		var pokemonInfo = getPokemonInfoFromNumber(config.pokeShowFaves[i]);
		if (pokemonInfoValid(pokemonInfo))
		{
			result.push(pokemonInfo[0].toString() + ": " + pokemonInfo[1]);
		}
		else
		{
			console.log("error listing");
		}
	}
	msg.channel.sendMessage(result);
}
function listRare(msg)
{
	var config = require( __dirname + '/config_bot.json' );
	var result = [];
	result.push("All rare pokemon being notified for:");
	for (var i = 0; i < config.pokeShowRare.length; i++)
	{
		var pokemonInfo = getPokemonInfoFromNumber(config.pokeShowRare[i]);
		if (pokemonInfoValid(pokemonInfo))
		{
			result.push(pokemonInfo[0].toString() + ": " + pokemonInfo[1]);
		}
		else
		{
			console.log("error listing");
		}
	}
	msg.channel.sendMessage(result);
}
function add(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var config = require( __dirname + '/config_bot.json' );
			var array = config.pokeShow;
				
			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];

				if (array.indexOf(newItem) == -1) {
						array.push(newItem);   
					msg.channel.sendMessage("Added to notify list: " + pokemonString);
					array = sortPokemonArray(array);
					fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				} else {
					msg.channel.sendMessage("Already present in notify list: " + pokemonString);
				}
			}
			else
			{
				msg.channel.sendMessage("Error adding");	
			}
			delete require.cache[ __dirname + '/config_bot.json' ]
		}
		else {
			msg.channel.sendMessage("No parameter detected");
		}
	}
}
function addFav(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var config = require( __dirname + '/config_bot.json' );
			var array = config.pokeShowFaves;
				
			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];

				if (array.indexOf(newItem) == -1) {
						array.push(newItem);   
					msg.channel.sendMessage("Added to favorite list: " + pokemonString);
					array = sortPokemonArray(array);
					fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				} else {
					msg.channel.sendMessage("Already present in favorite list: " + pokemonString);
				}
			}
			else
			{
				msg.channel.sendMessage("Error adding");	
			}
			delete require.cache[ __dirname + '/config_bot.json' ]
		}
		else {
			msg.channel.sendMessage("No parameter detected");
		}
	}
}

function addRare(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var config = require( __dirname + '/config_bot.json' );
			var array = config.pokeShow;

			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];

				if (array.indexOf(newItem) == -1) {
					array.push(newItem);
					msg.channel.sendMessage("Added to notify list: " + pokemonString);
					array = sortPokemonArray(array);
					fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				} else {
					msg.channel.sendMessage("Already present in notify list: " + pokemonString);
				}

				array = config.pokeShowRare;
				if (array.indexOf(newItem) == -1) {
					array.push(newItem);
					msg.channel.sendMessage("Added to rare notify list: " + pokemonString);
					array = sortPokemonArray(array);
					fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				} else {
					msg.channel.sendMessage("Already present in rare notify list: " + pokemonString);
				}
			}
			else
			{
				msg.channel.sendMessage("Error adding");
			}
			delete require.cache[ __dirname + '/config_bot.json' ]
		}
		else {
			msg.channel.sendMessage("No parameter detected");
		}
	}
}

function remove(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var config = require( __dirname + '/config_bot.json' );
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];
				var array = config.pokeShow;
				var i = array.indexOf(newItem);
				if (i == -1) 
				{
						msg.channel.sendMessage("Unable to remove, was not present: " + pokemonString);
				} 
				else 
				{
					array.splice(i, 1);
					msg.channel.sendMessage("Removed from notify list: " + pokemonString);
				}

				array = config.pokeShowRare;
				var j = array.indexOf(newItem);
				if (j == -1) 
				{
						//msg.channel.sendMessage("Unable to remove, was not present: " + pokemonString);
				} 
				else 
				{
					array.splice(j, 1);
					msg.channel.sendMessage("Removed from rare notify list: " + pokemonString);
				}
				if (i != -1 || j != -1)
					fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));

				delete require.cache[ __dirname + '/config_bot.json' ]
			} else {
				msg.channel.sendMessage("Error removing from notify list");
			}				
		}
		else {
			msg.channel.sendMessage("No parameter detected");
		}
	}
}

function removeRare(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var config = require( __dirname + '/config_bot.json' );
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];
				var array = config.pokeShowRare;
				var i = array.indexOf(newItem);
				if (i == -1) {
						msg.channel.sendMessage("Unable to remove, was not present: " + pokemonString);
				} else {
						array.splice(i, 1);
						msg.channel.sendMessage("Removed from rare notify list: " + pokemonString);
						msg.channel.sendMessage("Still exists in notify list: " + pokemonString);
						fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				}
				delete require.cache[ __dirname + '/config_bot.json' ]
			} else {
				msg.channel.sendMessage("Error removing from notify list");
			}
		}
	}
	else {
		msg.channel.sendMessage("No parameter detected");
	}
}
function removeFav(msg)
{
	if (isMod(msg))
	{
		if (msg.contentAll.length > 1)
		{
			var pokemonInfo = getPokemonInfoFromNumber(msg.contentAll[1]);
			if (pokemonInfoValid(pokemonInfo))
			{
				var config = require( __dirname + '/config_bot.json' );
				var newItem = parseInt(pokemonInfo[0]);
				var pokemonString = pokemonInfo[0] + ": " + pokemonInfo[1];
				var array = config.pokeShowFaves;
				var i = array.indexOf(newItem);
				if (i == -1) {
						msg.channel.sendMessage("Unable to remove, was not present: " + pokemonString);
				} else {
						array.splice(i, 1);
						msg.channel.sendMessage("Removed from favorite list: " + pokemonString);
						fs.writeFileSync( __dirname + '/config_bot.json' , JSON.stringify(config));
				}
				delete require.cache[ __dirname + '/config_bot.json' ]
			} else {
				msg.channel.sendMessage("Error removing from favorite list");
			}
		}
	}
	else {
		msg.channel.sendMessage("No parameter detected");
	}
}
  
function printPokemon(msg)
{
	if (msg.contentAll.length > 1)
	{
		var pokemonName = "";
		for (var i = 1; i < msg.contentAll.length; i++)
		{
			pokemonName += msg.contentAll[i];
			if (i < msg.contentAll.length - 1)
			{
				pokemonName += " ";
			}
		 }
		 var pokemonInfo = getPokemonInfoFromName(pokemonName);
		 if (pokemonInfoValid(pokemonInfo))
		 {
			msg.channel.sendMessage(pokemonInfo[0] + ": " + pokemonInfo[1]);
		 }
		 else
		 {
			msg.channel.sendMessage("No match found");
		 }
	 }
	 else
	 {
		msg.channel.sendMessage("No parameter detected");
	 }
}
        
function pokemonInfoValid(pokemonInfo)
{
    var valid = true;
    if (pokemonInfo[0] == -1 && pokemonInfo[1] === "")
    {
        valid = false;
    }
    return valid;
}

function getPokemonInfoFromName(pokemonName, specialNum)
{
    var number = -1;
    var name = "";
    for (var i = 0; i < locale.length; i++)
    {
        var tempPokemonName = locale[i].ename.toUpperCase();
        if (tempPokemonName === pokemonName)
        {
            number = locale[i].id;
            name = locale[i].ename;
            break;
        }
    }
    var pokemonInfo = [number, name];
    if (!pokemonInfoValid(pokemonInfo) && typeof specialNum === 'undefined')
    {
        pokemonInfo = getPokemonInfoFromNumber(pokemonName, 1);
    }
    return pokemonInfo;
}

function getPokemonInfoFromNumber(pokedexNumber, specialNum)
{
    var name = "";
    var number = -1;
    for (var i = 0; i < locale.length; i++)
    {
        var tempPokedexNumber = locale[i].id;
        if (tempPokedexNumber == pokedexNumber)
        {
            name = locale[i].ename;
            number = locale[i].id;
            break;
        }
    }
    var pokemonInfo = [number, name];
    if (!pokemonInfoValid(pokemonInfo) && typeof specialNum === 'undefined')
    {
        pokemonInfo = getPokemonInfoFromName(pokedexNumber, 1);
    }
    return pokemonInfo;
}

function sortPokemonArray(pokemonArray)
{
    pokemonArray.sort(function(a, b){
		var pokedexNum1 = parseInt(a);
		var pokedexNum2 = parseInt(b);

		if (pokedexNum1 < pokedexNum2) //sort string ascending
		return -1;
		if (pokedexNum1 > pokedexNum2)
		return 1;
		return 0; //default return value (no sorting)
		});
    return pokemonArray;
}

function newPokemonSighted(pokemon, forIVChannel) {
    var diff = new Date(pokemon.disappear_time * 1000) - Date.now();
    console.log("Disappear time:" + pokemon.disappear_time);
    diff = Math.floor(diff / 1000);
    diff = Math.floor(diff / 60);
    min_diff = diff % 60;    
    
    var currentTime = new Date();
    var expiresAtTime = new Date(0);
    expiresAtTime.setTime(pokemon.disappear_time*1000);
    var cEnding = "AM";
    var cHours = currentTime.getHours();
    var cMin = (currentTime.getMinutes()<10?'0':'') + currentTime.getMinutes();
    var cSec = (currentTime.getSeconds()<10?'0':'') + currentTime.getSeconds();
    if (cHours >= 12)
    {
        cEnding = "PM";
        if (cHours > 12)
        {
            cHours = cHours - 12;
        }
    }
    if (cHours == 0)
    {
        cHours = "12";
    }
    
    var eEnding = "AM";
    var eHours = expiresAtTime.getHours()+1;
    var eMin = (expiresAtTime.getMinutes()<10?'0':'') + expiresAtTime.getMinutes();
    var eSec = (expiresAtTime.getSeconds()<10?'0':'') + expiresAtTime.getSeconds();
    if (eHours >= 12)
    {
        eEnding = "PM";
        if (eHours > 12)
        {
            eHours = eHours - 12;
        }
    }
    if (eHours == 0)
    {
        eHours = "12";
    }
    var currentTimeStr = cHours+":"+cMin+":"+cSec + " " + cEnding;
    
    var expiresAtTimeString = eHours+":"+eMin+":"+eSec + " " + eEnding;
    console.log("expires");
    console.log(pokemon.disappear_time);
    var locationString = "http://maps.google.com/maps?z=12&t=m&q=loc:" + pokemon.lat + "+" + pokemon.lng;
//    var message = currentTimeStr + " : " + pokemon.name + ' (' + pokemon.ATK_IV + '.' + pokemon.DEF_IV + '.' + pokemon.STA_IV + ') found! Disappears in ' + min_diff + ' minutes at '+ expiresAtTimeString +'. \n'+ locationString  +'';
    var message = currentTimeStr + " : " + pokemon.name + ' (' + pokemon.ATK_IV + '.' + pokemon.DEF_IV + '.' + pokemon.STA_IV + ') found!\n'+ locationString  +'';
    
    var channel;

    if (forIVChannel == true)
    {
	channel = clientBot.channels.find('id', config.ivsChannelID);
    }
    else
    {
        channel = clientBot.channels.find('id', config.sightingsChannelID);
    }
    
    channel.sendFile( __dirname + "/bot/img/"+ pokemon.pokemon_id +".png" , pokemon.pokemon_id +".png", message, (err, msg) => {
                     if (err) {
                     channel.sendMessage("I do not have the rights to send a **file** :cry:!");
                     }
                     });
    console.log(pokemon.pokemon_id);
    if(config.pokeShowRare.indexOf(pokemon.pokemon_id) >= 0 ) {
        // found
        triggerIFTTT();
    }
}

function checkPokemon() {
    request('http://' + config.getServer + '/discord', (err, res, body) => {
            if (err) {
            console.log(err);
            return;
            }
            if (200 != res.statusCode) {
            console.log('Invalid response code: ' + res.statusCode);
            return;
            }
            parsePokemon(JSON.parse(body));
            });
}

function triggerIFTTT()
{
    console.log("Triggering IFTTT");
    for (key in config.maker_keys)
    {
        var theUrl = "https://maker.ifttt.com/trigger/ultra_rare_pokemon/with/key/" + config.maker_keys[key];
        console.log(theUrl);
	var xmlHttp = new XMLHttpRequest();
        xmlHttp.open("GET", theUrl, true); // true for asynchronous
        xmlHttp.send(null);
    }
}

function parsePokemon(results) {
    var config = require("./config_bot.json");
    if (!Object.keys(results) || Object.keys(results).length < 1) {
        return;
    }
    foundPokemon = [];
    for (pokemon in results) {
	//console.log("checking: " + results[pokemon].name + " " + results[pokemon].ATK_IV + "." + results[pokemon].DEF_IV + "." + results[pokemon].STA_IV);
	var sentForIVs = checkForIVsAndSendIfNeeded(results[pokemon]);
        var askedToShow = config.pokeShow.indexOf(results[pokemon].pokemon_id) >= 0
	if(askedToShow || sentForIVs) {
            // found
        } else {
            continue; // not found
        }
        foundPokemon.push(results[pokemon].key);
        if (alreadySeen.indexOf(results[pokemon].key) > -1) {
		continue;
        }
        
	if (askedToShow)
	{
        	newPokemonSighted(results[pokemon], false);
        }
	alreadySeen.push(results[pokemon].key);
    }
    
    clearStalePokemon(foundPokemon);
}

function checkForIVsAndSendIfNeeded(pokemon) {
	if (alreadySeen.indexOf(pokemon.key) > -1) {
                return true;
        }
	var percentage = 100.0* (pokemon.ATK_IV+pokemon.DEF_IV+pokemon.STA_IV)/45;
	//console.log("calc: " + percentage.toString());
	if (percentage >= config.generalIVRequirement) {
		newPokemonSighted(pokemon, true);
		return true;
	}
	else if (config.pokeShowFaves.indexOf(pokemon.pokemon_id) >= 0 && percentage >= config.favoriteIVRequirement) {
		newPokemonSighted(pokemon, true);			
		return true;
	}
	return false;
}

function clearStalePokemon(pokemons) {
    var oldSeen = alreadySeen;
    for (id in oldSeen) {
        var pokemon = pokemons.indexOf(oldSeen[id]);
        if (pokemon > -1) {
            continue;
        }
        
        var index = alreadySeen.indexOf(oldSeen[id]);
        alreadySeen.splice(index, 1);
    }
}

clientBot.login(config.token);

/* checking for new pokemon */
setInterval(() => {
            checkPokemon();
            }, (config.CheckMinutes * 1000) * 10); //checking for Pokemon every x minutes
