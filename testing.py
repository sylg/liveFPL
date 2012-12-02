import requests
from bs4 import BeautifulSoup
from helpers import *
from settings import *
import json
from flask import jsonify



message = { 'A': ' just got an assist.',
			  'GS': ' just scored a Goal!',
			  'YC': ' just received a Yellow Card!',
			  'RC': ' has been sent off.',
			  'PS': ' just saved a Penalty!',
			  'PM': ' just missed a Penalty!',
			  'OG': ' just scored an OWN GOAL!',
			  'S': ' just made 3 saves, +1pt.',
}

test1 = {'456': {'playername': 'Pienaar', 'GC': '1', 'MP': '19'}, '219': {'playername': 'Berbatov', 'MP': '19'}, '115': {'playername': 'Jelavic', 'GC': '1', 'MP': '19'}, '130': {'playername': 'Duff', 'MP': '19'}, '137': {'playername': 'Kacaniklic', 'MP': '19'}, '138': {'playername': 'Diarra', 'MP': '19'}, '118': {'playername': 'Schwarzer', 'S': '3', 'MP': '19', 'TP': '2'}, '95': {'playername': 'Jagielka', 'GC': '1', 'MP': '19'}, '94': {'playername': 'Heitinga', 'GC': '1', 'MP': '19'}, '140': {'A': '1', 'playername': 'Ruiz', 'MP': '19', 'TP': '4'}, '566': {'playername': 'Mirallas', 'GC': '1', 'MP': '19'}, '123': {'playername': 'Hughes', 'MP': '19'}, '124': {'playername': 'Hangeland', 'MP': '19'}, '125': {'playername': 'Baird', 'MP': '19'}, '127': {'playername': 'Riise', 'MP': '19'}, '128': {'playername': 'Riether', 'MP': '19'}, '103': {'playername': 'Osman', 'GC': '1', 'MP': '19'}, '399': {'OG': '1', 'TP': '-1', 'playername': 'Howard', 'S': '1', 'GC': '1', 'MP': '19'}, '106': {'playername': 'Neville', 'GC': '1', 'MP': '19'}, '107': {'playername': 'Coleman', 'GC': '1', 'MP': '19'}, '97': {'playername': 'Baines', 'GC': '1', 'MP': '19'}, '105': {'playername': 'Fellaini', 'GC': '1', 'MP': '19'}}


def push_data(dico,current_mp):
	push_data = []
	print "pushing data"
	print dico
	for player in dico:
		if 'TP' in dico[player]:
			for key in dico[player]:
				if key in messages and dico[player][key] != 0:
					r.incr('events')
					eventid = r.get('events')
					event = { 'playername':dico[player]['playername'],
								'pid':player,
								'message':message[key],
								'time':current_mp,
								'TP':dico[player]['TP']
					 }
					if key == "S" and int(dico[player][key]) % 3 == 0:
						push_data.append(event)
						r.hmset('tickerevent:%s'%eventid,{ 'playername':dico[player]['playername'],'pid':player,'message':message[key],'time':current_mp,'TP':dico[player]['TP']})
					else:
						push_data.append(event)
						r.hmset('tickerevent:%s'%eventid,{ 'playername':dico[player]['playername'],'pid':player,'message':message[key],'time':current_mp,'TP':dico[player]['TP']})
	p[ticker_channel].trigger('ticker', {'event':push_data })


push_data(test1,6)