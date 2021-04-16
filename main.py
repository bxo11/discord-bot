import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

import db
from sqlalchemy.orm import sessionmaker

import models


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='o/')

engine = db.load_database()
Session = sessionmaker(bind=engine)
session = Session()

global rules_channel
global rules_action_channel


@bot.event
async def on_ready():
    global rules_channel
    global rules_action_channel
    rules_channel = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RulesChannel').first().SettingValue
    rules_action_channel = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'RulesActionChannel').first().SettingValue
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('------')


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if not payload.member.guild_permissions:
        return
    mess_id = payload.message_id
    action: models.RulesActions = session.query(models.RulesActions).filter(
        models.RulesActions.MessageId == mess_id).first()

    current_position: models.Configuration = session.query(models.Configuration).filter(
        models.Configuration.SettingName == 'CurrentRulePosition').first()
    if action.Action == "add":
        rule: models.Rules = models.Rules(action.Text, payload.member.name + '#' + payload.member.discriminator,
                                          current_position.SettingValue)
        session.add(rule)
        current_position.SettingValue = int(current_position.SettingValue) + 1
    if action.Action == "delete":
        try:
            rule_to_delete: models.Rules = session.query(models.Rules).filter(
                models.Rules.Position == action.Text).first()
            if rule_to_delete is None:
                channel = payload.channel_id
                await channel.send('Wrong position')
                return
            session.delete(rule_to_delete)
            current_position.SettingValue = int(current_position.SettingValue) - 1
            recalculate_positions()
        except:
            session.rollback()
            print("Type Error")

    session.delete(action)
    session.commit()


@bot.command(name='radd', help='Adding new rule')
async def rule_add(ctx: commands.Context, mess: str):
    global rules_action_channel
    if rules_action_channel != ctx.channel.name:
        print("Wrong channel")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "add",
                                                      ctx.message.author.name + '#' + ctx.message.author.discriminator,
                                                      mess)
    session.add(action)
    session.commit()
    print("Rule action added")


@bot.command(name='rdel', help='Adding new rule')
async def rule_delete(ctx: commands.Context, mess: str):
    global rules_action_channel
    if rules_action_channel != ctx.channel.name:
        print("Wrong channel")
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "delete",
                                                      ctx.message.author.name + '#' + ctx.message.author.discriminator,
                                                      mess)
    session.add(action)
    session.commit()
    print("Rule action added")


@bot.command(name='raddnow', help='Adding new rule')
@commands.has_permissions(administrator=True)
async def rule_add_now(ctx: commands.Context, mess: str):
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


@bot.command(name='rdelnow', help='')
@commands.has_permissions(administrator=True)
async def rule_delete_now(ctx: commands.Context, position: int):
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
