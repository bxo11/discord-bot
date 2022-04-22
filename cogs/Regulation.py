import random
from datetime import date
from time import sleep

import discord
from discord.ext import commands
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Union

from db import Session
from models import Guilds, Configuration, Rules, RulesActions, RulesActionsType, ConfigurationType

CONSTANT_RULES_ACTION_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_RULES_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_RULES_CHANNEL_TYPE_ERROR = 'Zły typ argumentu'
CONSTANT_ACTION_CONFIRMATION = ['Akcja czeka na decyzje Ojca']


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
                self.update_regulations_last_modification(guild_id)
                message_object: discord.PartialMessage = channel.get_partial_message(message_id)
                l_rules_channel = discord.utils.get(self.bot.get_all_channels(),
                                                    id=self.get_setting(guild_id, 'RulesChannel'))
                await message_object.clear_reactions()
                await message_object.add_reaction('✅')
            except Exception as error:
                print(error)
                session.rollback()
                return
        await self.print_regulation(l_rules_channel)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        with Session() as session, session.begin():
            try:
                action: RulesActions = session.query(RulesActions).filter(
                    RulesActions.message_id == payload.message_id).first()

                if action:
                    session.delete(action)
                    print('Action deleted')
            except SQLAlchemyError as error:
                session.rollback()
                print(error)
                return

    @commands.command(name='add')
    async def rule_action_add(self, ctx: commands.Context, message: str, *args):
        guild_id = ctx.guild.id
        rules_action_channel_id = self.get_setting(guild_id, 'RulesActionChannel')
        if not ctx.channel.id == rules_action_channel_id:
            error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}'
            await ctx.send(error_message)
            raise Exception(error_message)

        if len(args) != 0:
            for p in args:
                message += " " + p

        with Session() as session, session.begin():
            try:
                action: RulesActions = RulesActions(ctx.message.id, RulesActionsType.add, str(ctx.message.author),
                                                    message,
                                                    session.query(Guilds).filter(
                                                        Guilds.guild_id == guild_id).first().id)
                session.add(action)
                await ctx.message.add_reaction('🕖')
                await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
                print("Rule action added")
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return

    @commands.command(name='del')
    async def rule_action_delete(self, ctx: commands.Context, position: str):
        guild_id = ctx.guild.id
        rules_action_channel_id = self.get_setting(guild_id, 'RulesActionChannel')

        if not position.isnumeric():
            error_message = f'{CONSTANT_RULES_CHANNEL_TYPE_ERROR}'
            await ctx.send(error_message)
            return
        if not ctx.channel.id == rules_action_channel_id:
            error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}'
            await ctx.send(error_message)
            return
        rule_to_delete = self.get_rule_by_position(guild_id, int(position))
        if not rule_to_delete:
            error_message = 'Nie ma takiej pozycji'
            await ctx.send(error_message)
            return

        with Session() as session, session.begin():
            try:
                action: RulesActions = RulesActions(ctx.message.id, RulesActionsType.delete, str(ctx.message.author),
                                                    position,
                                                    session.query(Guilds).filter(
                                                        Guilds.guild_id == guild_id).first().id)
                session.add(action)
                print("Rule action added")
                await ctx.message.add_reaction('🕖')
                await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return

    @commands.command(name='adminadd')
    @commands.has_permissions(administrator=True)
    async def rule_add_now(self, ctx: commands.Context, message: str, *args):
        guild_id = ctx.guild.id
        rules_channel_id = self.get_setting(guild_id, 'RulesChannel')

        if not ctx.channel.id == rules_channel_id:
            error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}'
            await ctx.send(error_message)
            return

        if len(args) != 0:
            for arg in args:
                message += " " + arg

        with Session() as session, session.begin():
            try:
                rule: Rules = Rules(message, str(ctx.message.author),
                                    session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
                session.add(rule)
                print("Rule added")
                self.update_regulations_last_modification(guild_id)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return
        await self.show_regulations(ctx)

    @commands.command(name='admindel')
    @commands.has_permissions(administrator=True)
    async def rule_delete_now(self, ctx: commands.Context, position: str):
        guild_id = ctx.guild.id
        rules_channel_id = self.get_setting(guild_id, 'RulesChannel')

        if not position.isnumeric():
            error_message = f'{CONSTANT_RULES_CHANNEL_TYPE_ERROR}'
            await ctx.send(error_message)
            return
        if not ctx.channel.id == rules_channel_id:
            error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}'
            await ctx.send(error_message)
            return
        rule_to_delete = self.get_rule_by_position(guild_id, int(position))
        if not rule_to_delete:
            error_message = 'Nie ma takiej pozycji'
            await ctx.send(error_message)
            return

        with Session() as session, session.begin():
            try:
                session.delete(rule_to_delete)
                print('Rule deleted')
                self.update_regulations_last_modification(guild_id)
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
                return
        await self.show_regulations(ctx)

    def get_rule_by_position(self, guild_id: int, position: int) -> Rules or None:
        with Session() as session, session.begin():
            rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(Rules.id).all()
            if int(position) < 1 or int(position) > len(rules):
                return None
            return rules[int(position) - 1]

    @commands.command(name='show')
    async def show_regulations(self, ctx: commands.Context):
        rules_channel_id = self.get_setting(ctx.guild.id, 'RulesChannel')

        if not ctx.channel.id == rules_channel_id:
            error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}'
            await ctx.send(error_message)
            return

        await self.print_regulation(ctx.channel)

    async def print_regulation(self, ctx: discord.TextChannel):
        amount_of_fields_in_embed = 5
        amount_of_rules_in_embed_field = 20

        with Session() as session, session.begin():
            try:
                guild_id = ctx.guild.id
                await ctx.purge(limit=10)
                sleep(1)
                rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(
                    Rules.id).all()
                regulations_last_modification: str = self.get_setting(guild_id, 'RegulationsLastModification')

                position = 0
                while position < len(rules):
                    embed = discord.Embed(title=f'Regulamin - ostatnia zmiana: {regulations_last_modification}',
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

    @commands.command(name='help')
    async def show_help(self, ctx: commands.Context):
        # embed body
        embed = discord.Embed(description=f'Komendy działają tylko na określonym kanale.',
                              color=0xff0000)
        embed.add_field(name=".setup", value=f'Podstawowa konfiguracja bota \n(np: **.setup id-rules-channel id-rules-action-channel**)', inline=False)
        embed.add_field(name=".add", value=f'Dodaj punkt do regulaminu (np: **.add "wojtek to gej"**'
                                           '\nlub **.add wojtek to gej**)', inline=False)
        embed.add_field(name=".del", value=f"Usuń punkt z regulaminu (np: **.del 12**)", inline=False)
        embed.add_field(name=".adminadd", value=f"Natychmiast dodaj punkt (**tylko admin**)", inline=False)
        embed.add_field(name=".admindel", value=f"Natychmiast usuń punkt (**tylko admin**)", inline=False)
        embed.add_field(name=".show", value=f"Pokaż regulamin", inline=True)
        embed.add_field(name=".help", value=f"Pokaż komendy", inline=True)
        embed.set_footer(text=f"Po dodaniu nowego punktu poczekaj aż Ojciec go zatwierdzi")
        await ctx.send(embed=embed)

    @commands.command(name='setup')
    async def setup(self, ctx: commands.Context, rules_channel_id: str, action_channel_id: str):
        if rules_channel_id.isnumeric() and action_channel_id.isnumeric():
            self.set_setting(ctx.guild.id, "RulesChannel", rules_channel_id)
            self.set_setting(ctx.guild.id, "RulesActionChannel", action_channel_id)

    def update_regulations_last_modification(self, guild_id: int):
        today = date.today()
        dat = today.strftime("%d/%m/%Y")
        self.set_setting(guild_id, 'RegulationsLastModification', dat)

    def get_setting(self, guild_id: int, setting_name: str) -> Union[int, str, None]:
        return_value = None
        with Session() as session, session.begin():
            try:
                setting: Configuration = session.query(Configuration).join(Guilds).filter(
                    and_(Guilds.guild_id == guild_id, Configuration.setting_name == setting_name)).first()
                return_value = setting.setting_value
                if setting.setting_type == ConfigurationType.int:
                    return_value = int(return_value)
                elif setting.setting_type == ConfigurationType.string:
                    pass
                elif setting.setting_type == ConfigurationType.date:
                    pass
            except SQLAlchemyError as error:
                print(error)
                session.rollback()
            except Exception as error:
                print(error)
                session.rollback()
            finally:
                return return_value

    def set_setting(self, guild_id: int, setting_name: str, new_value: str):
        with Session() as session, session.begin():
            try:
                setting: Configuration = session.query(Configuration).join(Guilds).filter(
                    and_(Guilds.guild_id == guild_id), Configuration.setting_name == setting_name).first()
                setting.setting_value = new_value
            except SQLAlchemyError as error:
                print(error)
                session.rollback()


def setup(bot):
    bot.add_cog(Regulation(bot))
