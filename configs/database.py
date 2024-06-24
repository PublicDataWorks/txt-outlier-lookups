import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(override=True)
db_url = os.environ.get("DATABASE_URL")

engine = create_engine(
    db_url,
    pool_size=15,
    max_overflow=0,
    pool_pre_ping=True,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)

Session = sessionmaker(bind=engine)
