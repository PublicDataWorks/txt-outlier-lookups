import os
from subprocess import PIPE, Popen
from zipfile import ZipFile

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import find_dotenv, load_dotenv
from sftp_client import SFTPServerClient

load_dotenv(find_dotenv())

host = os.getenv("SFTP_HOST")
username = os.getenv("SFTP_USERNAME")
password = os.getenv("SFTP_PASSWORD")
port = os.getenv("SFTP_PORT")


def fetch_data():
    # remote server credentials
    sftp_client = SFTPServerClient(host, port, username, password)

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
        Popen(["./property.sh"], shell=True, stdin=PIPE, stderr=PIPE)
    except Exception as e:
        print(e)


scheduler = BackgroundScheduler()
scheduler.add_job(fetch_data, "interval", weeks=4)
scheduler.start()
