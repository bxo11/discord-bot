import os

import discord
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
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('------')


@bot.command(name='radd', help='Adding new rules')
async def rule_add(context, mess):
    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    rule = Rules(mess, context.message.author.name + '#' + context.message.author.discriminator,
                 current_position.SettingValue)
    session.add(rule)
    current_position.SettingValue = int(current_position.SettingValue) + 1
    session.commit()
    response = "Rule added"
    await context.send(response)
    await show_regulations(context)


@bot.command(name='rdel', help='Deleting new rules')
async def rule_delete(context, position):
    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    rule_to_delete = session.query(Rules).filter(Rules.Position == position).first()

    if rule_to_delete is None:
        await context.send('Wrong position')
        return

    session.delete(rule_to_delete)
    current_position.SettingValue = int(current_position.SettingValue) - 1
    session.commit()
    await context.send('Rule deleted')
    recalculate_positions()
    await show_regulations(context)


def recalculate_positions():
    list_of_rules = session.query(Rules).all()
    temp = 1
    for elem in list_of_rules:
        elem.Position = temp
        temp += 1

    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    current_position.SettingValue = temp
    session.commit()


@bot.command(name='rshow', help='')
async def show_regulations(context):
    embed = discord.Embed(title="Regulamin")
    list_of_rules = session.query(Rules).all()
    i = 1
    for elem in list_of_rules:
        text = str(i) + ". " + elem.Text
        embed.add_field(name='\u200b', value=text, inline=False)
        i += 1

    await context.send(embed=embed)


bot.run(TOKEN)
