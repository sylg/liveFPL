from flask import Flask, request, render_template, jsonify
import redis
import os
from helpers import *
from tasks import *


app = Flask(__name__)

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/getleagues")
def new_team():
	team_id = str(request.args.get('team_id'))
	if r.exists('scraptimer:%s'%team_id):
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
	get_classicdata.delay(league_id)
	leaguename = r.hget('league:%s:info'%league_id,'name')
	leagues = []
	for league in r.smembers('team:%s:leagues'%team_id):
		leagues.append([league,r.hgetall('league:%s:info'%league)])

	return render_template("classic.html", leaguename=leaguename,leagues=leagues,league_id=league_id,currentgw=12)



@app.route('/test')
def test():
	get_classicdata.delay(48483)
	return "prout"


if __name__ == '__main__':
	# Bind to PORT if defined, otherwise default to 5000.
	port = int(os.environ.get('PORT', 5000))
	app.run(host='0.0.0.0', port=port, debug=True)