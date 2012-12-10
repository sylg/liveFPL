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

@periodic_task(run_every=crontab(minute='*',day_of_week='fri,sat,sun,mon,thu'),ignore_result=True)
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
				r.flushdb()
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
	print "getting team data for Classic league %s"%leagueid
	returned_data = {}
	for team in r.smembers('league:%s'%leagueid):
		data = scrapteam(team,r.get('currentgw'))
		returned_data[team] = data
		p['%s-prod'%leagueid].trigger('classic', data )
	r.set('scrapcache:%s'%leagueid, json.dumps(returned_data) )
	r.expire('scrapcache:%s'%leagueid,360)

@celery.task(ignore_result=True)
def get_h2hdata(leagueid):
	print "getting team data for H2H league %s"%leagueid
	returned_data = {}
	i = 1
	while i <= int(r.get('match:%s'%leagueid)):
		match = r.lrange('match:%s:%s'%(leagueid,i),0,-1)
		home_id = match[0]
		away_id = match[1]
		currentgw = r.get('currentgw')
		if r.exists('average_gwpts'):
			average_gwpts = r.get('average_gwpts')
		else:
			average_gwpts = 0

		if home_id == 'Average':
			home = {'lineup': [0], 'totalpts': 0,'gwpts': average_gwpts,'transfers': "None",'id':0, 'teamname': 'Average'}
			away = scrapteam(away_id, currentgw)
		elif away_id == 'Average':
			home = scrapteam(away_id, currentgw)
			away = {'lineup': [0], 'totalpts': 0,'gwpts': average_gwpts,'transfers': "None",'id':0, 'teamname': 'Average'}
		else:
			home = scrapteam(home_id, currentgw)
			away = scrapteam(away_id, currentgw)

		data = {'home': home, 'away':away}
		returned_data[i] = data
		p['%s-prod'%leagueid].trigger('h2h', data )
		i +=1
	r.set('scrapcache:%s'%leagueid, json.dumps(returned_data) )
	r.expire('scrapcache:%s'%leagueid,360)


# TICKER RELATED TASKS
@periodic_task(run_every=crontab(minute='*',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def update_ticker():
	print "checking if there is a event..."
	get_gw_event()
	push_event = []
	#Start Dict differ
	if r.get('events_status'):
		events = ['Penalties missed','Penalties saved', 'Goals scored','Assists', 'Yellow cards','Red cards', 'Saves','Own goals','Bonus' ]
		for event in events:
			if rp.exists(event):
				for players in rp.smembers(event):
					if rp.exists(players+':old'):
						playername = rp.hget(players+':fresh','playername')
						fresh = rp.hgetall(players+':fresh')
						old = rp.hgetall(players+':old')
						dictdiff = dict_diff(old,fresh)
						if dictdiff:
							for key in dictdiff:
								if key in messages:
									if key == "Saves" and int(dictdiff[key]) % 3 == 0:
										push_event.append({ 'playername':playername, 'pid':players, 'msg':messages[key]})
									elif key == "Bonus":
										push_event.append({ 'playername':playername, 'pid':players, 'msg':messages[key]%dictdiff[key]})
									else:
										push_event.append({ 'playername':playername, 'pid':players, 'msg':messages[key]})
	#Send new events to clients
	print "There's new event, Pushing..."
	if push_event:
		p[ticker_channel].trigger('ticker',push_event)
		#update the league open in the client
	#backup events sent for reuse.
	for event in push_event:
		r.rpush('events', json.dumps(event))
	#rename fresh to old for next scrap
	print "renaming..."
	for event in events:
		if rp.exists(event):
			for players in rp.smembers(event):
				if rp.exists(players+':fresh'):
						rp.rename(players+':fresh',players+':old')



@periodic_task(run_every=crontab(minute='*',hour='10-22',day_of_week='sat,sun,mon,thu'), ignore_result=True)
def update_live_leagues():
	if rp.exists('pushcounter') and int(rp.get('pushcounter')) > 0:
		get_classicdata.delay('48483')




