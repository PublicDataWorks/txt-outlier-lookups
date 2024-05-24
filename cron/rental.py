import os
from subprocess import PIPE, Popen

import requests
from apscheduler.schedulers.background import BlockingScheduler


def fetch_data():
    try:
        Popen(["./rental.sh"], shell=True, stdin=PIPE, stderr=PIPE)
    except Exception as e:
        print(e)


scheduler = BlockingScheduler()
scheduler.add_job(fetch_data, "interval", weeks=4)
scheduler.start()
