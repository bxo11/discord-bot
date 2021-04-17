import logging
import os
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


@bot.event
async def on_ready():
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('------')


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if not payload.member.guild_permissions.administrator:
        return
    mess_id: int = payload.message_id
    action: models.RulesActions = session.query(models.RulesActions).filter(
        models.RulesActions.MessageId == mess_id).first()

    if action.Action == "add":
        rule: models.Rules = models.Rules(action.Text, str(payload.member), get_current_position())
        session.add(rule)
        change_current_position('+', 1)

    elif action.Action == "delete":
        try:
            rule_to_delete: models.Rules = session.query(models.Rules).filter(
                models.Rules.Position == action.Text).first()
            if rule_to_delete is None:
                channel = payload.channel_id
                session.delete(action)
                await channel.send('Wrong position')
                return
            session.delete(rule_to_delete)
            change_current_position('-', 1)
            recalculate_positions()
        except:
            session.rollback()
            channel = payload.channel_id
            await channel.send('Wrong position type')

    session.delete(action)
    session.commit()


@bot.command(name='radd', help='Adding new rule')
async def rule_add(ctx: commands.Context, mess: str):
    rules_action_channel = get_rules_action_channel()
    if rules_action_channel != ctx.channel.name:
        await ctx.send("Wrong channel, use this command on " + rules_action_channel + " channel")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "add", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    print("Rule action added")


@bot.command(name='rdel', help='Adding new rule')
async def rule_delete(ctx: commands.Context, mess: str):
    rules_action_channel = get_rules_action_channel()
    if rules_action_channel != ctx.channel.name:
        await ctx.send("Wrong channel, use this command on " + rules_action_channel + " channel")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "delete", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    print("Rule action added")


@bot.command(name='raddnow', help='Adding new rule')
@commands.has_permissions(administrator=True)
async def rule_add_now(ctx: commands.Context, mess: str):
    rules_channel = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Wrong channel, use this command on " + rules_channel + " channel")
        return

    rule: models.Rules = models.Rules(mess, str(ctx.message.author), get_current_position())
    session.add(rule)
    change_current_position('+', 1)
    session.commit()
    print("Rule added")
    await show_regulations(ctx)


@bot.command(name='rdelnow', help='')
@commands.has_permissions(administrator=True)
async def rule_delete_now(ctx: commands.Context, position: int):
    rules_channel = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Wrong channel, use this command on " + rules_channel + " channel")
        return

    rule_to_delete: models.Rules = session.query(models.Rules).filter(models.Rules.Position == position).first()

    if rule_to_delete is None:
        await ctx.send('Wrong position')
        return

    session.delete(rule_to_delete)
    change_current_position('-', 1)
    session.commit()
    print('Rule deleted')
    recalculate_positions()
    await show_regulations(ctx)


def get_rules_action_channel():
    rules_action_channel = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RulesActionChannel').first()
    return rules_action_channel.SettingValue


def get_rules_channel():
    rules_channel = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RulesChannel').first()
    return rules_channel.SettingValue


def get_current_position():
    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    return current_position.SettingValue


def change_current_position(operation: chr, value: int):
    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    if operation == '+':
        current_position.SettingValue = int(current_position.SettingValue) + value
    elif operation == '-':
        current_position.SettingValue = int(current_position.SettingValue) - value
    session.commit()


def recalculate_positions():
    list_of_rules: list = session.query(models.Rules).all()
    iterator: int = 1
    for elem in list_of_rules:
        elem.Position = iterator
        iterator += 1

    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    current_position.SettingValue = iterator
    session.commit()


@bot.command(name='rshow', help='')
async def show_regulations(ctx: commands.Context):
    rules_channel: str = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Wrong channel, use this command on " + rules_channel + " channel")
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
