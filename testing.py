import requests
from bs4 import BeautifulSoup
from helpers import *
from settings import *
import json
from flask import jsonify
from twython import Twython


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
	print "done tweet"
get_opta_tweet()