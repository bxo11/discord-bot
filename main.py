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

global rules_channel


@bot.event
async def on_ready():
    global rules_channel
    rules_channel = session.query(Configuration).filter(
        Configuration.SettingName == 'RulesChannel').first().SettingValue
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('------')


@bot.command(name='radd', help='Adding new rule')
async def rule_add(context, mess):
    global rules_channel
    if rules_channel != context.channel.name:
        print("Wrong channel")
        return

    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    rule = Rules(mess, context.message.author.name + '#' + context.message.author.discriminator,
                 current_position.SettingValue)
    session.add(rule)
    current_position.SettingValue = int(current_position.SettingValue) + 1
    session.commit()
    print("Rule added")
    await show_regulations(context)


@bot.command(name='rdel', help='')
async def rule_delete(context, position):
    global rules_channel
    if rules_channel != context.channel.name:
        print("Wrong channel")
        return

    current_position = session.query(Configuration).filter(Configuration.SettingName == 'CurrentRulePosition').first()
    rule_to_delete = session.query(Rules).filter(Rules.Position == position).first()

    if rule_to_delete is None:
        await context.send('Wrong position')
        return

    session.delete(rule_to_delete)
    current_position.SettingValue = int(current_position.SettingValue) - 1
    session.commit()
    print('Rule deleted')
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
    global rules_channel
    if rules_channel != context.channel.name:
        print("Wrong channel")
        return

    await context.channel.purge(limit=10)
    list_of_rules = session.query(Rules).all()

    i = 1
    while i < len(list_of_rules):
        embed = discord.Embed(title="Regulamin")
        for elem in list_of_rules[i - 1:]:
            text = str(elem.Position) + ". " + elem.Text
            embed.add_field(name='\u200b', value=text, inline=False)
            i += 1
            if i % 26 == 0:
                break
        await context.send(embed=embed)


bot.run(TOKEN)
