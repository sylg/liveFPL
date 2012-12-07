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

@periodic_task(run_every=crontab(minute='*',hour='7-22',day_of_week='fri,sat,sun,mon,thu'),ignore_result=True)
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

		#Current GW & Clean players DB for ticker
		currentgw = str(re.findall(r"\d{1,2}", soup.find(class_="ismMegaLarge").string)[0])
		if r.exists('currentgw'):
			if currentgw != r.get('currentgw'):
				rp.flushdb()
				print "Done Flushing the dbs for new GW"
		r.set('currentgw',currentgw)

@periodic_task(run_every=crontab(minute='0', hour='0', day_of_week='sat'),ignore_result=True)
def fill_playerdb():
	i = 1
	no_more = 0
	while i <= 650 and no_more <= 5:
		url = "http://fantasy.premierleague.com/web/api/elements/%s/" %i
		response = requests.get(url)
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
	print "Done updating Player Database"

#TEAM AND LEAGUE SCRAPPING

@celery.task(ignore_result=True)
def add_data_db(teamid):
	new_team(teamid,r.get('currentgw'))
	push_leagues(teamid)

@celery.task(ignore_result=True)
def get_classicdata(leagueid):
	print "getting team data for league %s"%leagueid
	returned_data = {}
	for team in r.smembers('league:%s'%leagueid):
		data = scrapteam(team,r.get('currentgw'))
		returned_data[team] = data
		p[leagueid].trigger('classic', data )
	r.set('scrapcache:%s'%leagueid, json.dumps(returned_data) )
	r.expire('scrapcache:%s'%leagueid, 50)

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
	if r.exists('fixture_ids') and r.get('livefpl_status') == 'Live':
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
		current_mp = 0
		old_mp = 0
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
		rp.incr('pushcounter')
		rp.expire('pushcounter',50)
		push_data(diff_update,current_mp)


@periodic_task(run_every=crontab(minute='*',hour='10-22',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def update_live_eagues():
	if int(rp.get('pushcounter')) > 0:
		get_classicdata.delay('48483')




