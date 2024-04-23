import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
# set up database
db_url = os.environ.get("DATABASE_URL")

engine = create_engine(db_url)

Session = sessionmaker(bind=engine)
