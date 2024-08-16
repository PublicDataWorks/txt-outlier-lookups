from loguru import logger
from subprocess import PIPE, Popen


def fetch_data():
    logger.info("Starting Rental data fetch...")
    try:
        process = Popen(["bash ./cron/rental.sh"], shell=True, stdin=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(f"Rental script output: {stdout.decode()}")
        if stderr:
            logger.error(f"Rental script error: {stderr.decode()}")
    except Exception as e:
        logger.error("Error fetching rental data:", e)
