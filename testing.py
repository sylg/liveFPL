import requests
from bs4 import BeautifulSoup
from helpers import *
from settings import *
import re

messages = {'Penalties missed': ' just missed a Penalty!',
			'Penalties saved': ' just saved a Penalty!',
			'Goals scored': ' just scored a Goal!',
			'Assists': ' just got an assist.',
			'Yellow cards': ' just got an assist.',
			'Red cards': ' has been sent off.',
			'Saves': ' just made 3 saves, +1pt.',
			'Own goals': ' just scored an OWN GOAL!',
			'Bonus': ' just received %s bonus points!'
		}

def get_gw_eventold():
	url = "http://fantasy.premierleague.com/fixtures/"
	response = requests.get(url)
	html = response.text
	soup = BeautifulSoup(html,'lxml')
	table = soup.find('tbody')
	for actions in table.find_all('dt'):
		r.setnx("events_status", True)
		nextNode = actions
		while True:
			nextNode = nextNode.next_sibling
			try:
				tag_name = nextNode.name
			except AttributeError:
				tag_name =""
			if tag_name == "dd":
				playername = nextNode.text
				pid = nextNode.a['href'].strip('#')
				if playername.find('(') != -1:
					rep = playername[playername.find('(')+1:playername.find(')')]
					playername = playername[:playername.find('(')-1]
				else:
					rep = 1
				rp.sadd(actions.string, pid)
				rp.hsetnx(pid+":old",'playername',playername)
				rp.hsetnx(pid+":old",'pid',pid)
				rp.hset(pid+":old",actions.string,int(rep)-1)
			else:
				break


def get_teams_in_h2hleague(leagueid):
	url = 'http://fantasy.premierleague.com/my-leagues/%s/standings/' % leagueid
	response = requests.get(url)
	if response.status_code == 200:
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		table = soup.find(class_="ismTable ismH2HFixTable")
		if len(table.find_all('tr')) <= 25:
			print "Scrapping... H2H league %s"%leagueid
			for match in table.find_all('tr'):
				r.incr('match:%s'%leagueid)
				try:
					home_team_id = int(match.find_all('a')[0]['href'].strip('/').split('/')[1])
					away_team_id = int(match.find_all('a')[3]['href'].strip('/').split('/')[1])
				except IndexError:
					print "We got a match with an average in league%s"%leagueid
					if match.find(class_="ismHome").text.strip() == 'Average':
						print "average home"
						home_team_id = "Average"
						away_team_id = int(match.find_all('a')[1]['href'].strip('/').split('/')[1])
					else:
						home_team_id = int(match.find_all('a')[1]['href'].strip('/').split('/')[1])
						away_team_id = "Average"
get_teams_in_h2hleague(378050)