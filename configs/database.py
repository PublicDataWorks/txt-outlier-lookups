import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(override=True)
# set up database
db_url = os.environ.get("DATABASE_URL")

engine = create_engine(db_url, pool_size=15, max_overflow=0, pool_pre_ping=True)

Session = sessionmaker(bind=engine)
