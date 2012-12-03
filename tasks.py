import redis
import requests
from bs4 import BeautifulSoup
from celery import Celery
from celery.decorators import periodic_task
from settings import *
from helpers import *
import requests
import json
import re
from twython import Twython
import unicodedata
from datetime import timedelta

celery = Celery('tasks', broker=redis_celery_url, backend=redis_celery_url)

#GENERAL INFO SCRAPPING

@periodic_task(run_every=crontab(minute='1',hour='10-22',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def get_opta_tweet():
	print "getting latest opta tweets"
	print "Does tweet dict exist?"
	print r.exists('opta_tweet')
	if not r.exists('opta_tweet'):
		t = Twython(app_key='nfxOwOrDiKuyG4AQzT3iSw',
		            app_secret='6ogL1EZ7qNDmwvgz7zSCEe8b9AZ9pyjtEMB2ebwUWQs',
		            oauth_token='32849299-qCdJK4y9uaDw03NWeVWuInydqYospWCSCQOfvxhjc',
		            oauth_token_secret='ReLXHkrwrKIdyqSAbjAOMXbJ8CmsNZS9dvvYJ5q4')
		auth_tokens = t.get_authorized_tokens()
		opta_timeline = t.getUserTimeline(screen_name="optajoe",count="50")
		for tweet in opta_timeline:
			text = unicodedata.normalize('NFKD', tweet['text']).encode('ascii','ignore')
			tweet_url = "http://twitter.com/Optajoe/status/%s"%tweet['id_str']
			r.hset('opta_tweet',tweet_url,text)
			r.expire('opta_tweet', 86400)

@periodic_task(run_every=crontab(minute='*',hour='10-22',day_of_week='sat,sun,mon,thu'),ignore_result=True)
def livefpl_status():
	with requests.session() as c:
		c.post('https://users.premierleague.com/PremierUser/redirectLogin', data=payload)
		response = c.get('http://fantasy.premierleague.com/')
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		if "Live" in [str(td.string) for td in soup.find_all('td', {'class':'ismInProgress'})]:
			r.set('livefpl_status','Live')
		else:
			r.set('livefpl_status','Offline')
		currentgw = str(re.findall(r"\d{1,2}", soup.find(class_="ismMegaLarge").string)[0])
		r.set('currentgw',currentgw)

@periodic_task(run_every=crontab(minute='0', hour='0', day_of_week='sat'),ignore_result=True)
def fill_playerdb():
	i = 0
	no_more = 0
	while i <= 622 and no_more <= 5:
		url = "http://fantasy.premierleague.com/web/api/elements/%s/" %i
		response = requests.get(url)
		if response.status_code == 200:
			json = response.json
			web_name = json['web_name']
			position = json['type_name']
			teamname = json['team_name']
	 		rdb.hmset(i,{'web_name':web_name, 'position':position,'teamname':teamname})
	 		rdb.rpush('player_ids', i)
	 	elif response.status_code == 500:
	 		no_more +=1
		i += 1
	print "Done updating Player Database"



#TEAM AND LEAGUE SCRAPPING

@celery.task(ignore_result=True)
def add_data_db(teamid):
	new_team(teamid,r.get('currentgw'))
	push_leagues(teamid)

@celery.task(ignore_result=True)
def get_classicdata(leagueid):
	print "getting team data for %s"%leagueid
	returned_data = {}
	for team in r.smembers('league:%s'%leagueid):
		data = scrapteam.delay(team,r.get('currentgw'))
		returned_data[team] = data.get()
		p[leagueid].trigger('classic', data.get() )
	r.set('scrapcache:%s'%leagueid, json.dumps(returned_data) )
	r.expire('scrapcache:%s'%leagueid, 50)

@celery.task()
def scrapteam(teamid,currentgw):
	url = "http://fantasy.premierleague.com/entry/%s/event-history/%s/"%(teamid,currentgw)
	response = requests.get(url)
	if response.status_code == 200:
		print "Success! Scrapping data for %s"%teamid
		team = {}
		lineup = {}
		html = response.text
		soup = BeautifulSoup(html,'lxml')

		#find Team Info
		teamname = str(soup.find(class_='ismSection3').string)
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
		return team
	else:
		print "got error %s when trying to scrap team %s"%(response.status_code, teamid)


# TICKER RELATED TASKS
@periodic_task(run_every=crontab(minute='*',hour='10-22',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def get_fixture_ids():
	url = 'http://fantasy.premierleague.com/fixtures/'
	response = requests.get(url)
	html = response.text
	soup = BeautifulSoup(html,'lxml')
	for ids in soup.find_all('a',text="Detailed stats"):
		fixture_id = ids['data-id']
		if fixture_id not in r.lrange('fixture_ids',0,-1):
			r.lpush('fixture_ids', fixture_id)

@periodic_task(run_every=crontab(minute='*',hour='10-22',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def create_scrapper():
	if r.llen('fixture_ids') != 0 and r.get('livefpl_status') == 'Live':
		for ids in r.lrange('fixture_ids',0, -1):
			scrap_fixture.delay(ids)


@celery.task(ignore_result=True)
def scrap_fixture(fixture_id):
	#Scrap URL
	url = 'http://fantasy.premierleague.com/fixture/%s/' %fixture_id
	response = requests.get(url)
	html = response.text
	soup = BeautifulSoup(html, 'lxml')
	#Scrap Team lineup
	for teams in soup.find_all('table'):
		teamname = str(teams.find('caption').string)
		for players in teams.find('tbody').find_all('tr'):
			pid = 0
			playername = str(players.td.string.strip())
			#Convert Webname to Player ID format
			for ids in rdb.lrange('player_ids',0,-1):
				if playername == rdb.hget(ids, 'web_name') and teamname == rdb.hget(ids, 'teamname'):
					pid = ids
			if pid not in rp.lrange('lineups:%s' %fixture_id, 0, -1):
				rp.rpush('lineups:%s' %fixture_id, pid)
			#Store freshly scrapped data
			rp.hset('%s:fresh'%pid,'TEAMNAME',str(teamname))
			keys = ['MP', 'GS', 'A', 'CS', 'GC', 'OG', 'PS', 'PM', 'YC', 'RC','S', 'B', 'ESP', 'TP']
			i = 1
			for key in keys:
				rp.hset('%s:fresh'%pid, key, int(players.find_all('td')[i].string.strip()))
				i += 1
	#Getting the current playtime
	mp_pool = []
	if rp.exists('current_mp:%s'%fixture_id):
		current_mp = rp.get('current_mp:%s'%fixture_id)
		old_mp = current_mp
	else:
		current_mp = None
		old_mp = None
	for pid in rp.lrange('lineups:%s'%fixture_id, 0, -1):
		mp = rp.hget('%s:fresh'%pid,'MP')
		mp_pool.append(mp)
	for mp in mp_pool:
		if int(mp) > int(current_mp):
			current_mp = mp
	rp.set('current_mp:%s'%fixture_id,current_mp)
	print "for fixture %s, the current MP is %s ( old was %s)"%(fixture_id,current_mp, old_mp)
	#Counting to check if fixture is finished or not.
	if old_mp == current_mp:
		r.incr('counter:%s'%fixture_id)
	#Begin Differential between new and old scrap. Then push
	diff_update = {}
	number_of_player = rp.llen('lineups:%s'%fixture_id)
	for pid in rp.lrange('lineups:%s'%fixture_id, 0, -1):
		if rp.exists('%s:old'%pid):
			old = rp.hgetall('%s:old'%pid)
			fresh = rp.hgetall('%s:fresh'%pid)
			dictdiff = dict_diff(old,fresh)
			if dictdiff:
				dictdiff['playername'] = rdb.hget(pid,'web_name')
				diff_update[pid] = dictdiff
		else:
			rp.rename('%s:fresh'%pid,'%s:old'%pid)
	if diff_update:
		print "I need to push stuff"
		push_data(diff_update,current_mp)









