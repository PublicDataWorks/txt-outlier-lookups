import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# Constants
BROADCAST_SOURCE_PHONE_NUMBER = os.getenv("PHONE_NUMBER", "source_phone_number")
IMPACT_LABEL_IDS = [
    "804b1066-c77f-4000-85af-ad77c4f1bb76", # Outlier Staff Use/accountability gap
    "01b68845-c2c3-4882-8d38-1dba9cf49b5b", # Outlier Staff Use/crisis averted
    "7527944e-5305-4af0-9ff2-ac69226053b9", # Outlier Staff Use/future keyword
    "5f704c60-185c-45db-a1c9-c3dcbc31f8b2", # Outlier Staff Use/problem addressed
    "12b4950e-22ff-4994-9238-18b7edd64e68", # Outlier Staff Use/source
    "bbe46c64-0637-4407-be02-b2c58bf8c98a", # Outlier Staff Use/unsatisfied
    "17885c20-2b30-44f1-a57c-2bfc402ef758", # Outlier Staff Use/user satisfaction
]
REPORTER_LABEL_IDS = [
    "0cf16332-2d8f-424b-af6e-07d62399cfc3", # Automatic/Follow-up needed
    "123338fc-695d-48f2-aeac-4470f37206eb", # Automatic/Reporter requested
]

