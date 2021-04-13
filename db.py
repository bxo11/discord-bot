from sqlalchemy import create_engine


def load_database():
    engine = create_engine('sqlite:///db.sqlite', echo=True)
    return engine
