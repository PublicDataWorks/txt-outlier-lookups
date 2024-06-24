import logging
import random

from sqlalchemy import text
from configs.database import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_job(schedule, command, job_name=None):
    if job_name is None:
        job_name = "job-" + str(random.randint(1, 1000000))
    with Session() as session:
        query = text(f"SELECT cron.schedule(:job_name, :schedule, :command)")
        params = {"job_name": job_name, "schedule": schedule, "command": command}

        session.execute(query, params)
        session.commit()
