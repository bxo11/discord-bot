import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, BigInteger, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship

from db import engine, Session

Base = declarative_base()


class Guilds(Base):
    __tablename__ = 'guilds'
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False, unique=True)
    date_time_added = Column(DateTime, default=datetime.utcnow)
    rules = relationship("Rules", cascade="all,delete", backref="parent")
    rules_actions = relationship("RulesActions", cascade="all,delete", backref="parent")
    configuration = relationship("Configuration", cascade="all,delete", backref="parent")

    def __init__(self, guild_id):
        self.guild_id = guild_id


class Rules(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)
    text = Column(String(255), default='')
    author = Column(String(50), default='')
    date_time_added = Column(DateTime, default=datetime.utcnow)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, text, author, guild_id):
        self.text = text
        self.author = author
        self.guild_id = guild_id


class RulesActionsType(enum.Enum):
    add = 1
    delete = 2


class RulesActions(Base):
    __tablename__ = 'rules_actions'
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, nullable=False)
    action = Column(Enum(RulesActionsType), nullable=False)
    author = Column(String(50), default='')
    text = Column(String(255), default='')
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, message_id, action, author, text, guild_id):
        self.message_id = message_id
        self.action = action
        self.author = author
        self.text = text
        self.guild_id = guild_id


class ConfigurationType(enum.Enum):
    int = 1
    string = 2
    date = 3


class Configuration(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key=True)
    type = Column(Enum(ConfigurationType), nullable=False)
    setting_name = Column(String(50), nullable=False)
    setting_value = Column(String(50), default='')
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)

    def __init__(self, type, setting_name, setting_value, guild_id):
        self.type = type
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.guild_id = guild_id


default_config_list = [('date', 'RegulationsLastModification'),
                       ('int', 'RulesChannel'),
                       ('int', 'RulesActionChannel')]


def fill_empty_configuration(guild_id):
    with Session() as session, session.begin():
        new_guild = Guilds(guild_id)
        session.add(new_guild)

    with Session() as session, session.begin():
        new_guild = session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
        for s in default_config_list:
            setting: Configuration = Configuration(type=s[0], setting_name=s[1], setting_value='',
                                                   guild_id=new_guild.id)
            session.add(setting)


def remove_guild(guild_id):
    with Session() as session, session.begin():
        guild = session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
        session.delete(guild)


# run this file to create empty database
if __name__ == '__main__':
    Base.metadata.create_all(engine)
