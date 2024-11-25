from loguru import logger
from subprocess import PIPE, Popen


def fetch_data():
    logger.info("Starting Rental data fetch...")
    try:
        process = Popen(["bash ./cron/rental.sh"], shell=True, stdin=PIPE, stderr=PIPE)
        _, stderr = process.communicate()
        if process.returncode == 0:
            logger.info("Rental data import completed successfully")
        else:
            logger.error(f"Rental script error (code {process.returncode}): {stderr.decode()}")
    except Exception as e:
        logger.error("Error fetching rental data:", e)
