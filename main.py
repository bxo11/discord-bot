import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

import db
from sqlalchemy.orm import sessionmaker

import models

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

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
    rules_channel = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RulesChannel').first().SettingValue
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('------')


@bot.command(name='radd', help='Adding new rule')
async def rule_add(ctx: commands.Context, mess: str):
    global rules_channel
    if rules_channel != ctx.channel.name:
        print("Wrong channel")
        return

    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    rule: models.Rules = models.Rules(mess, ctx.message.author.name + '#' + ctx.message.author.discriminator,
                                      current_position.SettingValue)
    session.add(rule)
    current_position.SettingValue = int(current_position.SettingValue) + 1
    session.commit()
    print("Rule added")
    await show_regulations(ctx)


@bot.command(name='rdel', help='')
async def rule_delete(ctx: commands.Context, position: int):
    global rules_channel
    if rules_channel != ctx.channel.name:
        print("Wrong channel")
        return

    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    rule_to_delete: models.Rules = session.query(models.Rules).filter(models.Rules.Position == position).first()

    if rule_to_delete is None:
        await ctx.send('Wrong position')
        return

    session.delete(rule_to_delete)
    current_position.SettingValue = int(current_position.SettingValue) - 1
    session.commit()
    print('Rule deleted')
    recalculate_positions()
    await show_regulations(ctx)


def recalculate_positions():
    list_of_rules: list = session.query(models.Rules).all()
    temp: int = 1
    for elem in list_of_rules:
        elem.Position = temp
        temp += 1

    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    current_position.SettingValue = temp
    session.commit()


@bot.command(name='rshow', help='')
async def show_regulations(ctx: commands.Context):
    global rules_channel
    if rules_channel != ctx.channel.name:
        print("Wrong channel")
        return

    amount_of_fields_in_embed = 5
    amount_of_rules_in_embed_field = 20
    await ctx.channel.purge(limit=10)
    list_of_rules: list = session.query(models.Rules).all()

    position = 0
    while position < len(list_of_rules):
        embed = discord.Embed(title="Regulamin")
        for i in range(amount_of_fields_in_embed):
            if position >= len(list_of_rules):
                break
            text = ""
            for j in range(amount_of_rules_in_embed_field):
                if position >= len(list_of_rules):
                    break
                elem: models.Rules = list_of_rules[position]
                text += str(elem.Position) + ". " + elem.Text + "\n"
                position += 1
            embed.add_field(name='\u200b', value=text, inline=False)
        await ctx.send(embed=embed)


bot.run(TOKEN)
