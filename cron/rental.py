import logging
from subprocess import PIPE, Popen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_data():
    try:
        process = Popen(["./cron/rental.sh"], shell=True, stdin=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(f"Script output: {stdout.decode()}")
        if stderr:
            logger.error(f"Script error: {stderr.decode()}")
    except Exception as e:
        logger.error("Error fetching data:", e)
