import requests
from bs4 import BeautifulSoup
from helpers import *
from settings import *
import json
from flask import jsonify


def fill_playerdb():
	i = 1
	no_more = 0
	while i <= 622 and no_more <= 5:
		print i
		url = "http://fantasy.premierleague.com/web/api/elements/%s/" %i
		response = requests.get(url)
		print response.status_code
		if response.status_code == 200:
			json = response.json
			web_name = json['web_name']
			position = json['type_name']
			teamname = json['team_name']
	 		rdb.hmset(i,{'web_name':web_name, 'position':position,'teamname':teamname})
	 		rdb.rpush('player_ids', i)
	 	else:
	 		print "got error %s while scrapping player json"%response.status_code
	 		no_more +=1
	 		if no_more == 5:
	 			print "too much connection error ( 5 )"
		i += 1
fill_playerdb()