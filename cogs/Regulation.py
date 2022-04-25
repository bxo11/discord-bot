import random
from datetime import date
from time import sleep

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import Session
from models import Guilds, Rules, RulesActions, RulesActionsType, get_setting, \
    set_setting
from run import MY_GUILD

ERROR_WRONG_CHANNEL = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
ERROR_WRONG_INDEX = 'Nie ma takiej pozycji'
CONFIRMATION_REPLY_LIST = ['Akcja czeka na decyzje Ojca']
REGULATION_DESCRIPTION = 'Regulamin - ostatnia zmiana'
CONSTANT_NEW_RULE = 'Nowa zasada'
CONSTANT_DELETE_RULE = 'Usun zasade'
CONSTANT_SUCCESS = 'OK'


class Regulation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    @commands.has_permissions(administrator=True)
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member == self.bot.user:
            return

        with Session() as session, session.begin():
            try:
                message_id: int = payload.message_id
                guild_id = payload.guild_id
                action: RulesActions = session.query(RulesActions).join(Guilds).filter(
                    and_(Guilds.guild_id == guild_id, RulesActions.message_id == message_id)).first()

                if not action:
                    return

                channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)

                # add action
                if action.action == RulesActionsType.add:
                    rule: Rules = Rules(action.text, action.author,
                                        session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
                    session.add(rule)

                # delete action
                elif action.action == RulesActionsType.delete:
                    rule_to_delete = self.get_rule_by_position(guild_id, action.text)
                    session.delete(rule_to_delete)

                session.delete(action)
                Regulation.update_regulations_last_modification(discord.Object(id=guild_id))
                message_object: discord.Message = await channel.get_partial_message(message_id).fetch()
                l_rules_channel = discord.utils.get(self.bot.get_all_channels(),
                                                    id=get_setting(guild_id, 'RulesChannel'))
                # colour set
                current_embed = message_object.embeds[0]
                current_embed.colour = 0x00FF00
                await message_object.edit(embed=current_embed)
                # reaction set
                await message_object.clear_reactions()
                await message_object.add_reaction('✅')
            except Exception as error:
                print(error)
                session.rollback()
                return
        await Regulation.print_regulation(l_rules_channel)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        with Session() as session, session.begin():
            try:
                action: RulesActions = session.query(RulesActions).filter(
                    RulesActions.message_id == payload.message_id).first()

                if action:
                    session.delete(action)
            except SQLAlchemyError as error:
                session.rollback()
                print(error)
                return

    @staticmethod
    def get_rule_by_position(guild_id: int, position: int) -> Rules or None:
        with Session() as session, session.begin():
            rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(Rules.id).all()
            if int(position) < 1 or int(position) > len(rules):
                return None
            return rules[int(position) - 1]

    @staticmethod
    async def print_regulation(ctx: discord.TextChannel):
        amount_of_fields_in_embed = 5
        amount_of_rules_in_embed_field = 20

        with Session() as session, session.begin():
            try:
                guild_id = ctx.guild.id
                await ctx.purge(limit=10)
                sleep(1)
                rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(
                    Rules.id).all()
                regulations_last_modification: str = get_setting(guild_id, 'RegulationsLastModification')

                position = 0
                while position < len(rules):
                    embed = discord.Embed(title=f'{REGULATION_DESCRIPTION}: {regulations_last_modification}',
                                          color=0xff0000)
                    for i in range(amount_of_fields_in_embed):
                        if position < len(rules):
                            text = ""
                            for j in range(amount_of_rules_in_embed_field):
                                if position < len(rules):
                                    rule: Rules = rules[position]
                                    text += f'{position + 1}. {rule.text}\n'
                                    position += 1
                                else:
                                    break
                            embed.add_field(name='\u200b', value=text, inline=False)
                        else:
                            break
                    await ctx.send(embed=embed)
            except SQLAlchemyError as error:
                print(error)
                return

    @staticmethod
    def update_regulations_last_modification(guild: discord.Guild):
        today = date.today()
        dat = today.strftime("%d/%m/%Y")
        set_setting(guild.id, 'RegulationsLastModification', dat)

    @staticmethod
    async def create_confirmation_embed(channel: discord.TextChannel, title: str, rule: str,
                                        author: discord.User) -> discord.Message:
        embed = discord.Embed(title=title, color=0xff0000)
        embed.add_field(name='\u200b', value=f'"{rule}" by {author}', inline=False)
        sent_message = await channel.send(embed=embed)
        return sent_message


class RulesGroup(app_commands.Group):

    @app_commands.command(name='show', description='Show rules')
    async def show_regulations(self, interaction: discord.Interaction):
        rules_channel_id = get_setting(interaction.guild_id, 'RulesChannel')

        if not interaction.channel_id == rules_channel_id:
            await interaction.response.send_message(ERROR_WRONG_CHANNEL, ephemeral=True)
            return

        await Regulation.print_regulation(interaction.channel)
        await interaction.response.send_message(CONSTANT_SUCCESS)

    @app_commands.command(name='admin-add', description='Add rule')
    @commands.has_permissions(administrator=True)
    async def rule_add_now(self, interaction: discord.Interaction, message: str):
        guild_id = interaction.guild_id
        rules_channel_id = get_setting(guild_id, 'RulesChannel')

        if not interaction.channel_id == rules_channel_id:
            await interaction.response.send_message(ERROR_WRONG_CHANNEL, ephemeral=True)
            return

        with Session() as session, session.begin():
            try:
                rule: Rules = Rules(message, str(interaction.user),
                                    session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
                session.add(rule)
                print("Rule added")
                Regulation.update_regulations_last_modification(interaction.guild)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return
        await interaction.response.send_message(CONSTANT_SUCCESS, ephemeral=True)
        await Regulation.print_regulation(interaction.channel)

    @app_commands.command(name='admin-del', description='Remove rule')
    @commands.has_permissions(administrator=True)
    async def rule_delete_now(self, interaction: discord.Interaction, position: int):
        guild_id = interaction.guild.id
        rules_channel_id = get_setting(guild_id, 'RulesChannel')

        if not interaction.channel_id == rules_channel_id:
            await interaction.response.send_message(ERROR_WRONG_CHANNEL, ephemeral=True)
            return
        rule_to_delete = Regulation.get_rule_by_position(guild_id, int(position))
        if not rule_to_delete:
            await interaction.response.send_message(ERROR_WRONG_INDEX, ephemeral=True)
            return

        with Session() as session, session.begin():
            try:
                session.delete(rule_to_delete)
                print('Rule deleted')
                Regulation.update_regulations_last_modification(interaction.guild)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return
        await interaction.response.send_message(CONSTANT_SUCCESS, ephemeral=True)
        await Regulation.print_regulation(interaction.channel)

    @app_commands.command(name='add', description='Add new rule proposition')
    async def rule_action_add(self, interaction: discord.Interaction, message: str):
        guild_id = interaction.guild_id
        rules_action_channel_id = get_setting(guild_id, 'RulesActionChannel')

        if not interaction.channel_id == rules_action_channel_id:
            await interaction.response.send_message(ERROR_WRONG_CHANNEL, ephemeral=True)
            return

        await interaction.response.send_message(random.choice(CONFIRMATION_REPLY_LIST), ephemeral=True)
        sent_message = await Regulation.create_confirmation_embed(interaction.channel, CONSTANT_NEW_RULE, message,
                                                                  interaction.user)
        await sent_message.add_reaction('🕖')

        with Session() as session, session.begin():
            try:
                action: RulesActions = RulesActions(sent_message.id, RulesActionsType.add,
                                                    str(interaction.user),
                                                    message,
                                                    session.query(Guilds).filter(
                                                        Guilds.guild_id == guild_id).first().id)
                session.add(action)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return

    @app_commands.command(name='delete', description='Add delete proposition')
    async def rule_action_delete(self, interaction: discord.Interaction, position: int):
        guild_id = interaction.guild_id
        rules_action_channel_id = get_setting(guild_id, 'RulesActionChannel')

        if not interaction.channel_id == rules_action_channel_id:
            await interaction.response.send_message(ERROR_WRONG_CHANNEL, ephemeral=True)
            return
        rule_to_delete = Regulation.get_rule_by_position(guild_id, int(position))
        if not rule_to_delete:
            await interaction.response.send_message(ERROR_WRONG_INDEX, ephemeral=True)
            return

        await interaction.response.send_message(random.choice(CONFIRMATION_REPLY_LIST), ephemeral=True)
        sent_message = await Regulation.create_confirmation_embed(interaction.channel, CONSTANT_DELETE_RULE, position,
                                                                  interaction.user)
        await sent_message.add_reaction('🕖')

        with Session() as session, session.begin():
            try:
                action: RulesActions = RulesActions(sent_message.id, RulesActionsType.delete,
                                                    str(interaction.user),
                                                    position,
                                                    session.query(Guilds).filter(
                                                        Guilds.guild_id == guild_id).first().id)
                session.add(action)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return

    @app_commands.command(name='setup', description='set the RulesChannel and RulesActionChannel')
    @app_commands.describe(rules_channel='Text channel to show regulation',
                           action_channel='Text channel for sending actions to modify regulation')
    @commands.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, rules_channel: discord.TextChannel,
                    action_channel: discord.TextChannel):
        set_setting(interaction.guild_id, "RulesChannel", str(rules_channel.id))
        set_setting(interaction.guild_id, "RulesActionChannel", str(action_channel.id))
        await interaction.response.send_message(CONSTANT_SUCCESS, ephemeral=True)


async def setup(bot):
    bot.tree.add_command(RulesGroup(), guild=discord.Object(id=MY_GUILD))
    await bot.add_cog(Regulation(bot))
