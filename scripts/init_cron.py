import logging
import os

from dotenv import load_dotenv
from libs.pgcron import create_job

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BACKEND_URL = os.environ.get("BACKEND_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def init_monthly_fetch_property():
    logger.info('Initializing monthly fetch property cron job')
    command = f"""\
SELECT net.http_get(
    url:='{BACKEND_URL}/fetch_property',
    headers:= '{{"Content-Type": "application/json", "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}"}}'::jsonb
) AS request_id;
"""
    create_job('0 0 1 * *', command)
    logger.info('Monthly fetch property initialized')


def init_monthly_fetch_rental():
    logger.info('Initializing monthly fetch rental cron job')
    command = f"""\
SELECT net.http_get(
    url:='{BACKEND_URL}/fetch_rental',
    headers:= '{{"Content-Type": "application/json", "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}"}}'::jsonb
) AS request_id;
"""
    create_job('0 0 1 * *', command)
    logger.info('Monthly fetch rental initialized')


def init_weekly_report():
    logger.info('Initializing weekly report cron job')
    command = f"""\
SELECT net.http_get(
    url:='{BACKEND_URL}/weekly_report',
    headers:= '{{"Content-Type": "application/json", "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}"}}'::jsonb
) AS request_id;
"""
    create_job('0 9 * * 1 ', command)  # every week on Monday morning at 5am ET
    logger.info('Monthly fetch rental initialized')


init_monthly_fetch_property()
init_monthly_fetch_rental()
init_weekly_report()
