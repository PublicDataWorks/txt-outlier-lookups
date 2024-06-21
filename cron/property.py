import os
import logging
import shutil
from subprocess import PIPE, Popen
from zipfile import ZipFile

from dotenv import find_dotenv, load_dotenv
from .sftp_client import SFTPServerClient

load_dotenv(find_dotenv())

host = os.getenv("SFTP_HOST")
username = os.getenv("SFTP_USERNAME")
password = os.getenv("SFTP_PASSWORD")
port = int(os.getenv("SFTP_PORT", 22))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_data():
    logger.info("Starting data fetch...")
    temp_dir = "/tmp"
    zip_file_path = os.path.join(temp_dir, "mi_wayne_detroit.sql.zip")
    sftp_client = SFTPServerClient(host, port, username, password)
    try:
        # sftp_client.connect()
        # sftp_client.download_file(
        #     "/download/mi_wayne_detroit.sql.zip", zip_file_path
        # )
        # sftp_client.disconnect()

        with ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        try:
            current_directory = os.getcwd()
            print(f"Current working directory: {current_directory}")
            process = Popen(["./cron/property.sh"], shell=True, stdin=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            if stdout:
                logger.info(f"Script output: {stdout.decode()}")
            if stderr:
                logger.error(f"Script error: {stderr.decode()}")
        except Exception as e:
            logger.error("Error running script:", e)
    except Exception as e:
        logger.error("Error fetching data:", e)
