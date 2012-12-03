import requests
from bs4 import BeautifulSoup
import unicodedata
from settings import *


def get_teams_in_league(leagueid):
	url = 'http://fantasy.premierleague.com/my-leagues/%s/standings/' % leagueid
	response = requests.get(url)
	if response.status_code == 200:
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		table = soup.find(class_="ismTable ismStandingsTable")
		if len(table.find_all('tr')) <= 25:
			print "Scrapping...league %s"%leagueid
			for team in table.find_all('tr')[1:]:
				teamname = unicodedata.normalize('NFKD', team.find('a').string).encode('ascii','ignore')
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
		get_teams_in_league(leagueid)


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
		print "Error got status code:%s . retrying to get leagues...for team: %s"%(response.status_code,teamid)
		get_leagues(teamid,currentgw)


def new_team(teamid,currentgw):
	get_leagues(teamid, currentgw)
	for league in r.smembers('team:%s:leagues'%teamid):
		if r.hget('league:%s:info'%league,'type') == 'classic':
			get_teams_in_league(league)
		else:
			"not scrapping, it's a not supported H2H league"



### Check if string is number or nor
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False



### PUSH FUNCTION

messages = { 'A': ' just got an assist.',
			  'GS': ' just scored a Goal!',
			  'YC': ' just received a Yellow Card!',
			  'RC': ' has been sent off.',
			  'PS': ' just saved a Penalty!',
			  'PM': ' just missed a Penalty!',
			  'OG': ' just scored an OWN GOAL!',
			  'S': ' just made 3 saves, +1pt.',
}

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
								'time':current_mp
					 }
					if key == "S" and int(dico[player][key]) % 3 == 0:
						push_data.append(event)
						r.hmset('tickerevent:%s'%eventid,{ 'playername':dico[player]['playername'],'pid':player,'message':messages[key],'time':current_mp})
					else:
						push_data.append(event)
						r.hmset('tickerevent:%s'%eventid,{ 'playername':dico[player]['playername'],'pid':player,'message':messages[key],'time':current_mp})
	p[ticker_channel].trigger('ticker', {'event': json.dumps(push_data) })

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




