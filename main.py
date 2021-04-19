import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import date
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

bot = commands.Bot(command_prefix='.', help_command=None)

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
    if payload.member == bot.user:
        return
    if not payload.member.guild_permissions.administrator:
        return
    mess_id: int = payload.message_id
    action: models.RulesActions = session.query(models.RulesActions).filter(
        models.RulesActions.MessageId == mess_id).first()
    channel: discord.TextChannel = bot.get_channel(payload.channel_id)

    if action.Action == "add":
        rule: models.Rules = models.Rules(action.Text, str(payload.member), get_current_position())
        session.add(rule)
        change_current_position('+', 1)

    elif action.Action == "delete":
        try:
            rule_to_delete: models.Rules = session.query(models.Rules).filter(
                models.Rules.Position == action.Text).first()
            if rule_to_delete is None:
                session.delete(action)
                await channel.send('Nie ma takiej pozycji')
                return
            session.delete(rule_to_delete)
            change_current_position('-', 1)
            recalculate_positions()
        except:
            session.rollback()
            await channel.send('Zły format danych')

    session.delete(action)
    session.commit()
    update_regulations_last_modification()
    mess_obj: discord.PartialMessage = channel.get_partial_message(mess_id)
    await mess_obj.clear_reactions()
    await add_reaction_to_messeage(mess_obj, '✅')
    rules_channel = discord.utils.get(bot.get_all_channels(), name=get_rules_channel())
    await show_reg(rules_channel)


@bot.command(name='add')
async def rule_add(ctx: commands.Context, mess: str):
    rules_action_channel = get_rules_action_channel()
    if rules_action_channel != ctx.channel.name:
        await ctx.send("Zły kanał, użyj tej komendy na kanale " + "'" + rules_action_channel + "'")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "add", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    await add_reaction_to_messeage(ctx.message, '🕖')
    await ctx.send("Akcja czeka na decyzje Ojca")
    print("Rule action added")


@bot.command(name='del')
async def rule_delete(ctx: commands.Context, mess: str):
    rules_action_channel = get_rules_action_channel()
    if rules_action_channel != ctx.channel.name:
        await ctx.send("Zły kanał, użyj tej komendy na kanale " + "'" + rules_action_channel + "'")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "delete", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    await add_reaction_to_messeage(ctx.message, '🕖')
    await ctx.send("Akcja czeka na decyzje Ojca")
    print("Rule action added")


@bot.command(name='adminadd')
@commands.has_permissions(administrator=True)
async def rule_add_now(ctx: commands.Context, mess: str):
    rules_channel = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Zły kanał, użyj tej komendy na kanale " + "'" + rules_channel + "'")
        return

    rule: models.Rules = models.Rules(mess, str(ctx.message.author), get_current_position())
    session.add(rule)
    change_current_position('+', 1)
    session.commit()
    print("Rule added")
    update_regulations_last_modification()
    await show_regulations(ctx)


@bot.command(name='admindel')
@commands.has_permissions(administrator=True)
async def rule_delete_now(ctx: commands.Context, position: int):
    rules_channel = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Zły kanał, użyj tej komendy na kanale " + "'" + rules_channel + "'")
        return

    rule_to_delete: models.Rules = session.query(models.Rules).filter(models.Rules.Position == position).first()

    if rule_to_delete is None:
        await ctx.send('Nie ma takiej pozycji')
        return

    session.delete(rule_to_delete)
    change_current_position('-', 1)
    session.commit()
    print('Rule deleted')
    update_regulations_last_modification()
    recalculate_positions()
    await show_regulations(ctx)


async def add_reaction_to_messeage(msg: discord.Message, emoji_name: str):
    await msg.add_reaction(emoji_name)


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


def update_regulations_last_modification():
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    r_last_modification: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RegulationsLastModification').first()
    r_last_modification.SettingValue = d1
    session.commit()


@bot.command(name='show')
async def show_regulations(ctx: commands.Context):
    rules_channel: str = get_rules_channel()
    if rules_channel != ctx.channel.name:
        await ctx.send("Zły kanał, użyj tej komendy na kanale " + "'" + rules_channel + "'")
        return
    await show_reg(ctx.channel)


async def show_reg(channel: discord.Message.channel):
    amount_of_fields_in_embed = 5
    amount_of_rules_in_embed_field = 20
    await channel.purge(limit=10)
    list_of_rules: list = session.query(models.Rules).all()
    regulations_last_modification: str = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RegulationsLastModification').first().SettingValue

    position = 0
    while position < len(list_of_rules):
        embed_title: str = "Regulamin - ostatnia zmiana: " + regulations_last_modification
        embed = discord.Embed(title=embed_title, color=0xff0000)
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
        await channel.send(embed=embed)


@bot.command(name='help')
async def show_help(ctx: commands.Context):
    desc = get_rules_action_channel()
    embed = discord.Embed(description="Komendy działają tylko na " + "''" + desc + "''", color=0xff0000)
    embed.add_field(name=".add", value="Dodaj punkt do regulaminu (np: **.add ''wojtek to gej''**)", inline=False)
    embed.add_field(name=".del", value="Usuń punkt z regulaminu (np: **.del 12**)", inline=False)
    embed.add_field(name=".adminadd", value="Natychmiast dodaj punkt (**tylko admin**)", inline=False)
    embed.add_field(name=".admindel", value="Natychmiast usuń punkt (**tylko admin**)", inline=False)
    embed.add_field(name=".show", value="Pokaż regulamin", inline=True)
    embed.add_field(name=".help", value="Pokaż komendy", inline=True)
    embed.set_footer(text="Po dodaniu nowego punktu poczekaj aż Ojciec go zatwierdzi")
    await ctx.send(embed=embed)


bot.run(TOKEN)
