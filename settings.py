import redis
import pusher
import os
from datetime import timedelta
from celery.schedules import crontab

## PUSHER ##
############
pusher.app_id = "28247"
pusher.key = "b2c9525770d59267a6a2"
pusher.secret = "12d6efe3c861e6ce372a"
p = pusher.Pusher()

#Ticker Channel

ticker_channel = 'prod_ticker'
#ticker_channel = 'dev_ticker'


## REDIS ##
###########

#Heroku

redis_url = 'redis://:zkknD6CFj3XEBhbh7cYseHdr6HuOe3laFqTKAmDqrjfBE8jXPOnL86qcGnfX1HuU@node-fe03b4d4d9564505a.openredis.com:10727'
redis_celery_url = "redis://:zkknD6CFj3XEBhbh7cYseHdr6HuOe3laFqTKAmDqrjfBE8jXPOnL86qcGnfX1HuU@node-fe03b4d4d9564505a.openredis.com:10727"
r = redis.from_url(redis_url, db=0)
rp = redis.from_url(redis_url, db=1)
rdb = redis.from_url(redis_url, db=2)


#Localhost

# redis_url = 'redis://localhost:6379'
# redis_celery_url = 'redis://localhost:6379'
# r = redis.StrictRedis(host='localhost', port=6379, db=0)
# rp = redis.StrictRedis(host='localhost', port=6379, db=1)
# rdb = redis.StrictRedis(host='localhost', port=6379, db=2)


#Requests Stuff

headers = {'User-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
payload = {'action': 'https://users.premierleague.com/PremierUser/redirectLogin','email': 'baboo2@yopmail.com','password': 'bibi2000'}



#Period Task timer

timer = crontab(minute='*', hour='10-22',day_of_week='saturday,sunday,monday,tuesday,wednesday,thursday')
timerslow = timedelta(seconds=100)
timer = timedelta(seconds=20)