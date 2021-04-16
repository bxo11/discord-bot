import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


def load_database():
    engine = create_engine(DATABASE_URL, echo=True)
    return engine
