from flask import Flask, request, render_template, jsonify
import redis
import os
from helpers import *
from tasks import *
import json
import random

app = Flask(__name__)

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/getleagues")
def new_team():
	team_id = str(request.args.get('team_id'))
	if r.exists('scraptimer:%s'%team_id) and len(r.smembers('team:%s:leagues'%team_id)) > 0:
		print "team %s already in DB. Don't scrap time remaning on timer: %s"%(team_id, r.ttl('scraptimer:%s'%team_id))
		returned_data = {}
		for league in r.smembers('team:%s:leagues'%team_id):
			returned_data[league] = r.hgetall('league:%s:info'%league)
		print jsonify(returned_data)
		return jsonify(returned_data)
	else:
		print "new user (%s). Scrapping data"%team_id
		add_data_db.delay(team_id)
		r.set('scraptimer:%s'%team_id, 'true')
		r.expire('scraptimer:%s'%team_id, 3000)
		return "None"

@app.route("/classic")
def classic():
	team_id = str(request.args.get('team_id'))
	league_id = str(request.args.get('league_id'))
	leaguename = r.hget('league:%s:info'%league_id,'name')
	leagues = []
	for league in r.smembers('team:%s:leagues'%team_id):
		leagues.append([league,r.hgetall('league:%s:info'%league)])
	if r.exists('scrapcache:%s'%league_id):
		return_data = json.loads(r.get('scrapcache:%s'%league_id))
		data = "old"
	else:
		return_data = 0
		data = "fresh"
		get_classicdata.delay(league_id)
	size = r.scard('league:%s'%league_id)
	livefpl_status = r.get('livefpl_status')

	#Get Random Opta tweet
	tweets = []
	for tweet in r.hgetall('opta_tweet'):
		tweets.append([tweet,r.hget('opta_tweet',tweet)])

	#Get Already pushed event to prepoluate ticker
	i = 1
	event_count = r.get('events')
	events = []
	while i <= int(event_count):
		print i
		events.insert(0,r.hgetall('tickerevent:%s'%i))
		i += 1

	return render_template("classic.html",events=events,tweets=tweets,leaguename=leaguename,leagues=leagues,league_id=league_id,currentgw=r.get('currentgw'),return_data=return_data,size=size,data=data,livefpl_status=livefpl_status)

if __name__ == '__main__':
	# Bind to PORT if defined, otherwise default to 5000.
	port = int(os.environ.get('PORT', 5000))
	app.run(host='0.0.0.0', port=port, debug=True)