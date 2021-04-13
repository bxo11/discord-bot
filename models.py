from sqlalchemy import Column, String, INTEGER, DATETIME, VARCHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Rules(Base):
    __tablename__ = 'Rules'
    Id = Column('Id', INTEGER, primary_key=True)
    Text = Column('Text', VARCHAR(100))
    Author = Column('Author', VARCHAR(50))
    Position = Column('Position', INTEGER)
    DateAdded = Column('DateAdded', DATETIME, default=func.now())

    def __init__(self, text, author, position):
        self.Text = text
        self.Author = author
        self.Position = position


class Configuration(Base):
    __tablename__ = 'Configuration'
    SectionName = Column('SectionName', VARCHAR(50))
    SettingName = Column('SettingName', VARCHAR(50), primary_key=True)
    SettingValue = Column('SettingValue', VARCHAR(1000))
    SettingType = Column('SettingType', INTEGER)

    def __init__(self, sec_n, set_n, set_v, set_t):
        self.SectionName = sec_n
        self.SettingName = set_n
        self.SettingValue = set_v
        self.SettingType = set_t
