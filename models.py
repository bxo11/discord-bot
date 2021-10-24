import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, BigInteger, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship

from db import engine

Base = declarative_base()


class Guilds(Base):
    __tablename__ = 'guilds'
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False, unique=True)
    date_time_added = Column(DateTime, default=datetime.utcnow)
    rules = relationship("Rules")
    rules_actions = relationship("RulesActions")
    configuration = relationship("Configuration")

    def __init__(self, guild_id):
        self.guild_d = guild_id


class Rules(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)
    text = Column(String(255), default='')
    author = Column(String(50))
    position = Column(Integer, nullable=False)
    date_time_added = Column(DateTime, default=datetime.utcnow)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, text, author, position, guild_id):
        self.text = text
        self.author = author
        self.position = position
        self.guild_id = guild_id


class RulesActionsType(enum.Enum):
    add = 'add'
    delete = 'delete'


class RulesActions(Base):
    __tablename__ = 'rules_actions'
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, nullable=False)
    action = Column(Enum(RulesActionsType), nullable=False)
    author = Column(String(50))
    text = Column(String(255), default='')
    guild_id = Column(BigInteger, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, message_id, action, author, text, guild_id):
        self.message_id = message_id
        self.action = action
        self.author = author
        self.text = text
        self.guild_id = guild_id


class ConfigurationSectionType(enum.Enum):
    other = "other"
    regulation = 'regulation'
    tasks = 'tasks'


class Configuration(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key=True)
    section_name = Column(Enum(ConfigurationSectionType), nullable=False)
    setting_name = Column(String(50), nullable=False, unique=True)
    setting_value = Column(String(50), nullable=False)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, section_name, setting_name, setting_value, guild_id):
        self.section_name = section_name
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.guild_id = guild_id


if __name__ == '__main__':
    Base.metadata.create_all(engine)
