import requests
from bs4 import BeautifulSoup
import unicodedata
from settings import *
import json

def scrapteam(teamid,currentgw):
	url = "http://fantasy.premierleague.com/entry/%s/event-history/%s/"%(teamid,currentgw)
	response = requests.get(url)
	team = {}
	send = False
	while not send:
		if response.status_code == 200:
			print "Scrapping team %s got code %s"%(teamid,response.status_code )
			lineup = {}
			html = response.text
			soup = BeautifulSoup(html,'lxml')

			#find Team Info

			teamname = unicodedata.normalize('NFKD',soup.find(class_='ismSection3').string).encode('ascii','ignore')
			oldtotal = int(soup.find(class_='ismModBody').find(class_='ismRHSDefList').dd.string)
			oldgwpts = int(soup.find(class_='ismModBody').find(class_='ismRHSDefList').find_all('dd')[3].a.string)
			transfers = str(soup.find(class_='ismSBDefList').find_all('dd')[1].string.replace(" ","").replace('\n',''))

			#find lineup
			for player in soup.find_all(class_="ismPlayerContainer"):
				playername = str(player.find(class_="ismPitchWebName").string.strip())
				pid = player.find('a',class_="ismViewProfile")['href'].strip('#')

				points = player.find('a', class_="ismTooltip").string.strip()
				#if player hasn't played yet. Convert his points to 0 and mark him as not played
				if not is_number(points):
					points = 0
					played = False
				else:
					points = str(points)
					played = True
				#check if he's the captain
				if player.find(class_='ismCaptainOn'):
					captain = True
				else:
					captain = False
				#check if he's the Vice-captain
				if player.find(class_='ismViceCaptainOn'):
					vc = True
				else:
					vc = False
				#check if he's on the bench
				if player.find_parents(class_='ismBench'):
		 			bench = True
				else:
					bench = False
				lineup[playername] = {'pts':points, 'captain':captain,'vc':vc,'bench':bench,'played':played,'pid':pid}

			#Calcultating Current GW Points
			currentgwpts = 0
			for player in lineup:
				if lineup[player]['bench'] == False:
					currentgwpts += int(lineup[player]['pts'])

			teamtotal = oldtotal - oldgwpts + currentgwpts
			team['lineup'] = lineup
			team['totalpts'] = teamtotal
			team['gwpts'] = currentgwpts
			team['transfers'] = transfers
			team['id'] = teamid
			team['teamname'] = teamname

			send = True
	return team


def get_gw_event():
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
				rp.hsetnx(pid+":fresh",'playername',playername)
				rp.hsetnx(pid+":fresh",'pid',pid)
				rp.hset(pid+":fresh",actions.string,rep)

			else:
				break

def get_teams_in_classicleague(leagueid):
	url = 'http://fantasy.premierleague.com/my-leagues/%s/standings/' % leagueid
	response = requests.get(url)
	if response.status_code == 200:
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		table = soup.find(class_="ismTable ismStandingsTable")
		if len(table.find_all('tr')) <= 25:
			print "Scrapping...league %s"%leagueid
			for team in table.find_all('tr')[1:]:
				team_id = int(team.a['href'].strip('/').split('/')[1])
				if not r.sismember('league:%s'%leagueid, team_id):
					r.sadd('league:%s'%leagueid, team_id)
		else:
			print "Too big. Skip."
			r.hset('league:%s:info'%leagueid,"players", 0)

		r.hset('league:%s:info'%leagueid,"players", r.scard('league:%s'%leagueid))
	else:
		print "Error got status code:%s" % response.status_code
		print "got error %s when trying to get the teams in league %s."%(response.status_code, leagueid)


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
						home_team_id = "Average"
						away_team_id = int(match.find_all('a')[1]['href'].strip('/').split('/')[1])
					else:
						home_team_id = int(match.find_all('a')[1]['href'].strip('/').split('/')[1])
						away_team_id = "Average"

				r.rpush('match:%s:%s'%(leagueid,r.get('match:%s'%leagueid)),home_team_id, away_team_id)
				if not r.sismember('league:%s'%leagueid, home_team_id):
					r.sadd('league:%s'%leagueid, home_team_id)
				if not r.sismember('league:%s'%leagueid, away_team_id):
					r.sadd('league:%s'%leagueid, away_team_id)
		else:
			print "Too big. Skip."
			r.hset('league:%s:info'%leagueid,"players", 0)
		r.hset('league:%s:info'%leagueid,"players", r.scard('league:%s'%leagueid))
	else:
		print "Error got status code:%s" % response.status_code
		print "got error %s when trying to get the teams in league %s."%(response.status_code, leagueid)


def get_leagues(teamid,currentgw):
	url = "http://fantasy.premierleague.com/entry/%s/event-history/%s/" % (teamid, currentgw)
	response = requests.get(url)
	if response.status_code == 200:
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		classic = soup.find_all(class_="ismLeagueTable")[0].find('tbody')
		h2h = soup.find_all(class_="ismLeagueTable")[1].find('tbody')

		#classic Leagues
		for league in classic.find_all('tr'):
			leaguename = unicodedata.normalize('NFKD',league.a.string.strip()).encode('ascii','ignore')
			leagueurl = league.a.get('href')
			league_id = int(leagueurl.strip('/').split('/')[1])
			if not r.sismember('team:%s:leagues'%teamid,league_id):
				r.sadd('team:%s:leagues'%teamid,league_id)
				r.hmset('league:%s:info'%league_id,{'name':leaguename, 'type':'classic' })

		#H2H Leagues
		if len(h2h.find_all('a')) != 0:
			for league in h2h.find_all('tr'):
				leaguename = unicodedata.normalize('NFKD',league.a.string.strip()).encode('ascii','ignore')
				leagueurl = league.a.get('href')
				league_id = str(leagueurl.strip('/').split('/')[1])
				if not r.sismember('team:%s:leagues'%teamid,league_id):
					r.sadd('team:%s:leagues'%teamid,league_id)
					r.hmset('league:%s:info'%league_id,{'name':leaguename, 'type':'h2h'})
		else:
			print "team %s has no H2H leagues"%teamid

	else:
		rp.incr('team:%s:errorcounter'%teamid)
		print "Error got status code:%s . retrying to get leagues...for team: %s"%(response.status_code,teamid)
		if int(rp.get('team:%s:errorcounter'%teamid)) == 5:
			raise
		else:
			get_leagues(teamid,currentgw)


def new_team(teamid,currentgw):
	try:
		get_leagues(teamid, currentgw)
	except:
		print "Error: Team %s doens't exists on FPL."%teamid

	for league in r.smembers('team:%s:leagues'%teamid):
		if r.hget('league:%s:info'%league,'type') == 'classic':
			get_teams_in_classicleague(league)
		elif r.hget('league:%s:info'%league,'type') == 'h2h':
			get_teams_in_h2hleague(league)
		else:
			print "not a h2h or classic league ( %s )"%league



### Check if string is number or not
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False



### PUSH Functions & data

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

def push_leagues(team_id):
	returned_data = {}
	for league in r.smembers('team:%s:leagues'%team_id):
		if r.hget('league:%s:info'%league,"players") != 0:
			returned_data[league] = r.hgetall('league:%s:info'%league)
	p[team_id].trigger('league', {'message': returned_data })


### DICT DIFFERER
def dict_diff(dict_a, dict_b):
    return dict([
        (key, dict_b.get(key, dict_a.get(key)))
        for key in set(dict_a.keys()+dict_b.keys())
        if (
            (key in dict_a and (not key in dict_b or dict_a[key] != dict_b[key])) or
            (key in dict_b and (not key in dict_a or dict_a[key] != dict_b[key]))
        )
    ])


