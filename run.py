import logging
import os

from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
import db
from methods import *
import schedule

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

rules_action_channel: str
rules_channel: str
DISCORD_RULES_ACTION_CHANNEL_ERROR = f'Zły kanał, użyj tej komendy na odpowiednim kanale'
DISCORD_RULES_CHANNEL_ERROR = f'Zły kanał, użyj tej komendy na odpowiednim kanale'
DISCORD_ACTION_CONFIRMATION = f'Akcja czeka na decyzje Ojca'


@bot.event
async def on_ready():
    global rules_channel, rules_action_channel
    rules_action_channel = get_rules_action_channel(session)
    rules_channel = get_rules_channel(session)
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
        rule: models.Rules = models.Rules(action.Text, str(action.Author), get_current_position(session))
        session.add(rule)
        change_current_position(session, '+', 1)

    elif action.Action == "delete":
        try:
            rule_to_delete: models.Rules = session.query(models.Rules).filter(
                models.Rules.Position == action.Text).first()
            if rule_to_delete is None:
                session.delete(action)
                await channel.send('Nie ma takiej pozycji')
                return
            session.delete(rule_to_delete)
            change_current_position(session, '-', 1)
            recalculate_positions(session)
        except Exception:
            session.rollback()
            await channel.send('Zły format danych')

    session.delete(action)
    session.commit()
    update_regulations_last_modification(session)
    mess_obj: discord.PartialMessage = channel.get_partial_message(mess_id)
    await mess_obj.clear_reactions()
    await mess_obj.message.add_reaction('✅')
    l_rules_channel = discord.utils.get(bot.get_all_channels(), name=get_rules_channel(session))
    await show_reg(l_rules_channel)


@bot.command(name='add')
async def rule_add(ctx: commands.Context, mess: str, *args):
    if rules_action_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_CHANNEL_ERROR}: {rules_action_channel}')
        return

    if len(args) != 0:
        for p in args:
            mess += " " + p

    action: models.RulesActions = models.RulesActions(ctx.message.id, "add", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    await ctx.message.add_reaction('🕖')
    await ctx.send(DISCORD_ACTION_CONFIRMATION)
    print("Rule action added")


@bot.command(name='del')
async def rule_delete(ctx: commands.Context, mess: str):
    if rules_action_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_CHANNEL_ERROR}: {rules_action_channel}')
        return

    action: models.RulesActions = models.RulesActions(ctx.message.id, "delete", str(ctx.message.author), mess)
    session.add(action)
    session.commit()
    await ctx.message.add_reaction('🕖')
    await ctx.send(DISCORD_ACTION_CONFIRMATION)
    print("Rule action added")


@bot.command(name='adminadd')
@commands.has_permissions(administrator=True)
async def rule_add_now(ctx: commands.Context, mess: str, *args):
    if rules_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_CHANNEL_ERROR}: {rules_channel}')
        return

    if len(args) != 0:
        for p in args:
            mess += " " + p

    rule: models.Rules = models.Rules(mess, str(ctx.message.author), get_current_position(session))
    session.add(rule)
    change_current_position(session, '+', 1)
    session.commit()
    print("Rule added")
    update_regulations_last_modification(session)
    await show_regulations(ctx)


@bot.command(name='admindel')
@commands.has_permissions(administrator=True)
async def rule_delete_now(ctx: commands.Context, position: int):
    if rules_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_CHANNEL_ERROR}: {rules_channel}')
        return

    rule_to_delete: models.Rules = session.query(models.Rules).filter(models.Rules.Position == position).first()

    if rule_to_delete is None:
        await ctx.send('Nie ma takiej pozycji')
        return

    session.delete(rule_to_delete)
    change_current_position(session, '-', 1)
    session.commit()
    print('Rule deleted')
    update_regulations_last_modification(session)
    recalculate_positions(session)
    await show_regulations(ctx)


@bot.command(name='show')
async def show_regulations(ctx: commands.Context):
    if rules_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_CHANNEL_ERROR}: {rules_channel}')
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
        embed = discord.Embed(title=f'Regulamin - ostatnia zmiana: {regulations_last_modification}', color=0xff0000)
        for i in range(amount_of_fields_in_embed):
            if position >= len(list_of_rules):
                break
            text = ""
            for j in range(amount_of_rules_in_embed_field):
                if position >= len(list_of_rules):
                    break
                elem: models.Rules = list_of_rules[position]
                text += f'{elem.Position}. {elem.Text}\n'
                position += 1
            embed.add_field(name='\u200b', value=text, inline=False)
        await channel.send(embed=embed)


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    action: models.RulesActions = session.query(models.RulesActions).filter(
        models.RulesActions.MessageId == payload.message_id).first()

    if action is not None:
        session.delete(action)
        session.commit()


@bot.command(name='help')
async def show_help(ctx: commands.Context):
    if rules_action_channel != ctx.channel.name:
        await ctx.send(f'{DISCORD_RULES_ACTION_CHANNEL_ERROR}: "{rules_action_channel}"')
        return

    embed = discord.Embed(description=f'Komendy działają tylko na kanale: "{rules_action_channel}"', color=0xff0000)
    embed.add_field(name=".add", value=f'Dodaj punkt do regulaminu (np: **.add "wojtek to gej"**'
                                       '\nlub **.add wojtek to gej**)', inline=False)
    embed.add_field(name=".del", value=f"Usuń punkt z regulaminu (np: **.del 12**)", inline=False)
    embed.add_field(name=".adminadd", value=f"Natychmiast dodaj punkt (**tylko admin**)", inline=False)
    embed.add_field(name=".admindel", value=f"Natychmiast usuń punkt (**tylko admin**)", inline=False)
    embed.add_field(name=".show", value=f"Pokaż regulamin", inline=True)
    embed.add_field(name=".help", value=f"Pokaż komendy", inline=True)
    embed.set_footer(text=f"Po dodaniu nowego punktu poczekaj aż Ojciec go zatwierdzi")
    await ctx.send(embed=embed)


bot.run(TOKEN)
