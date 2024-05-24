import os
import atexit
import logging
from subprocess import PIPE, Popen
from zipfile import ZipFile

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import find_dotenv, load_dotenv
from .sftp_client import SFTPServerClient

# Load environment variables
load_dotenv(find_dotenv())

# SFTP Credentials
host = os.getenv("SFTP_HOST")
username = os.getenv("SFTP_USERNAME")
password = os.getenv("SFTP_PASSWORD")
port = int(os.getenv("SFTP_PORT", 22))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_data():
    logger.info("Starting data fetch...")
    sftp_client = SFTPServerClient(host, port, username, password)
    try:
        sftp_client.connect()
        sftp_client.download_file(
            "/download/mi_wayne_detroit.sql.zip", "download/mi_wayne_detroit.sql.zip"
        )
        sftp_client.disconnect()

        zip_file_path = "download/mi_wayne_detroit.sql.zip"
        extracted_folder = "download"
        with ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extracted_folder)

        try:
            process = Popen(["./property.sh"], shell=True, stdin=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            if stdout:
                logger.info(f"Script output: {stdout.decode()}")
            if stderr:
                logger.error(f"Script error: {stderr.decode()}")
        except Exception as e:
            logger.error("Error running script:", e)
    except Exception as e:
        logger.error("Error fetching data:", e)


# Scheduler setup
scheduler = BackgroundScheduler()


def start_scheduler():
    scheduler.start()
    fetch_data()  # Run the job once when the server starts
    atexit.register(lambda: scheduler.shutdown())
