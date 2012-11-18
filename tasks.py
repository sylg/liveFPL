import redis
import requests
from bs4 import BeautifulSoup
from celery import Celery
from celery.schedules import crontab
from celery.decorators import periodic_task

celery = Celery('tasks', broker='redis://localhost:6379', backend='redis://localhost:6379')


@celery.task(ignore_result=True)
def scrapper(fixture_id):
	url = "http://fantasy.premierleague.com/fixture/%s/"%fixture_id