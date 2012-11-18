from celery.schedules import crontab
from settings import *

CELERY_TIMEZONE = 'Europe/London'


BROKER_URL = redis_celery_url

# List of modules to import when celery starts.
CELERY_IMPORTS = ("tasks")

# Using the database to store task state and results.
CELERY_RESULT_BACKEND = redis_celery_url