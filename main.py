import os
from discord.ext import commands
from dotenv import load_dotenv
import db
from sqlalchemy.orm import sessionmaker

from models import Configuration, Rules

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='o/')

engine = db.load_database()
Session = sessionmaker(bind=engine)
session = Session()


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='radd', help='Adding new rules')
async def rule_add(context, mess):
    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    rule = Rules(mess, context.message.author.name +'#' + context.message.author.discriminator,
                 current_position.SettingValue)
    session.add(rule)
    current_position.SettingValue = int(current_position.SettingValue) + 1
    session.commit()
    response = "Rule added"
    await context.send(response)


# @bot.command(name='rdel', help='Deleting new rules')
# async def rule_delete(context, id):
#     db_connection = sqlite3.connect('./db.sqlite')
#     db_connection.execute('DELETE FROM Rules WHERE position =?', id)
#     db_connection.commit()
#     response = "Rule deleted"
#     await context.send(response)


# def recalculate_positions():
#     db_connection = sqlite3.connect('./db.sqlite')
#     rules = db_connection.execute('SELECT id, position FROM Rules').fetchall()
#     for v in rules:
#         print(v)
#     db_connection.commit()


bot.run(TOKEN)
