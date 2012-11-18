import redis
import requests
from bs4 import BeautifulSoup
from celery import Celery
from settings import *
from helpers import *

celery = Celery('tasks', broker='redis://localhost:6379', backend='redis://localhost:6379')


@celery.task(ignore_result=True)
def add_data_db(teamid):
	new_team(teamid,12)
	push_leagues(teamid)



@celery.task(ignore_result=True)
def get_classicdata(leagueid):
	print "getting team data for %s"%leagueid
	returned_data = {}
	for team in r.smembers('league:%s'%leagueid):
		data = scrapteam.delay(team,12)
		returned_data[team] = data.get()
	p[leagueid].trigger('classic', returned_data )

@celery.task()
def scrapteam(teamid,currentgw):
	url = "http://fantasy.premierleague.com/entry/%s/event-history/%s/"%(teamid,currentgw)
	response = requests.get(url)
	retry_counter = 5 
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
			points = player.find('a', class_="ismTooltip").string.strip()
			#if player hasn't played yet. Convert his points to 0 and mark him as not played
			if not points.isdigit():
				points = 0
				played = True
			else:
				played = False
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
			lineup[playername] = {'pts':points, 'captain':captain,'vc':vc,'bench':bench,'played':played}

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
		print "got error %s when trying to scrap team %s trying %s more time"%(response.status_code, teamid, retry_counter)
		retry_counter = retry_counter - 1
		scrapteam.delay(teamid,currentgw)






