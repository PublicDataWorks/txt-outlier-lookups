import os
from dotenv import load_dotenv
from services.analytics.service import AnalyticsService

# Load environment variables from .env file
load_dotenv()

# Initialize the AnalyticsService
ana = AnalyticsService()

# Run the send_weekly_report function
ana.send_weekly_report()
