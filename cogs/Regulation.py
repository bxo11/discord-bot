import random
from datetime import date
from time import sleep

import discord
from discord.ext import commands
from sqlalchemy import and_
from sqlalchemy.orm import Session

from db import Session
from models import Guilds, Configuration, Rules, RulesActions, RulesActionsType

CONSTANT_RULES_ACTION_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_RULES_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_RULES_CHANNEL_TYPE_ERROR = 'Zły typ argumentu'
CONSTANT_ACTION_CONFIRMATION = ['Akcja czeka na decyzje Ojca']


class Regulation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member == self.bot.user:
            return
        # permissions check
        if not payload.member.guild_permissions.administrator:
            return

        session = Session()
        try:
            message_id: int = payload.message_id
            guild_id = payload.guild_id
            action: RulesActions = session.query(RulesActions).join(Guilds).filter(
                and_(Guilds.guild_id == guild_id, RulesActions.message_id == message_id)).first()

            if action is None:
                session.close()
                return

            channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)

            # adding rule
            if action.action == RulesActionsType.add:
                rule: Rules = Rules(action.text, action.author,
                                    session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
                session.add(rule)

            # deleting rule
            elif action.action == RulesActionsType.delete:
                rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(
                    Rules.id).all()
                rule_to_delete: Rules = rules[int(action.text) - 1]
                session.delete(rule_to_delete)
                session.commit()

            session.delete(action)
            session.commit()
            self.update_regulations_last_modification(guild_id)
            mess_obj: discord.PartialMessage = channel.get_partial_message(message_id)
            await mess_obj.clear_reactions()
            await mess_obj.add_reaction('✅')
            l_rules_channel = discord.utils.get(self.bot.get_all_channels(),
                                                name=self.get_setting(guild_id, 'RulesChannel'))
            await self.print_regulation(l_rules_channel)
        except Exception as error:
            print(error)
            session.rollback()
        session.close()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        session = Session()
        try:
            action: RulesActions = session.query(RulesActions).filter(
                RulesActions.message_id == payload.message_id).first()

            if action is not None:
                session.delete(action)
                session.commit()
                print('Action deleted')
        except Exception as error:
            session.rollback()
            print(error)
        session.close()

    @commands.command(name='add')
    async def rule_action_add(self, ctx: commands.Context, message: str, *args):
        session = Session()
        try:
            guild_id = ctx.guild.id
            rules_action_channel = self.get_setting(guild_id, 'RulesActionChannel')
            if not ctx.channel.name == rules_action_channel:
                error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}: {rules_action_channel}'
                await ctx.send(error_message)
                raise Exception(error_message)

            if len(args) != 0:
                for p in args:
                    message += " " + p

            action: RulesActions = RulesActions(ctx.message.id, RulesActionsType.add, str(ctx.message.author), message,
                                                session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
            session.add(action)
            session.commit()
            await ctx.message.add_reaction('🕖')
            await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
            print("Rule action added")
        except Exception as error:
            session.rollback()
            print(error)
        session.close()

    @commands.command(name='del')
    async def rule_action_delete(self, ctx: commands.Context, position: str):
        session = Session()
        try:
            guild_id = ctx.guild.id
            rules_action_channel = self.get_setting(guild_id, 'RulesActionChannel')
            if not position.isnumeric():
                error_message = f'{CONSTANT_RULES_CHANNEL_TYPE_ERROR}'
                await ctx.send(error_message)
                raise Exception(error_message)
            if not ctx.channel.name == rules_action_channel:
                error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}: {rules_action_channel}'
                await ctx.send(error_message)
                raise Exception(error_message)

            rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(Rules.id).all()
            if int(position) < 1 or int(position) > len(rules):
                error_message = 'Nie ma takiej pozycji'
                await ctx.send(error_message)
                raise Exception(error_message)

            action: RulesActions = RulesActions(ctx.message.id, RulesActionsType.delete, str(ctx.message.author),
                                                position,
                                                session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
            session.add(action)
            session.commit()
            await ctx.message.add_reaction('🕖')
            await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
            print("Rule action added")
        except Exception as error:
            session.rollback()
            print(error)
        session.close()

    @commands.command(name='adminadd')
    @commands.has_permissions(administrator=True)
    async def rule_add_now(self, ctx: commands.Context, message: str, *args):
        session = Session()
        try:
            guild_id = ctx.guild.id
            rules_channel = self.get_setting(guild_id, 'RulesChannel')
            if not ctx.channel.name == rules_channel:
                error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}: "{rules_channel}"'
                await ctx.send(error_message)
                raise Exception(error_message)

            if len(args) != 0:
                for arg in args:
                    message += " " + arg

            rule: Rules = Rules(message, str(ctx.message.author),
                                session.query(Guilds).filter(Guilds.guild_id == guild_id).first().id)
            session.add(rule)
            self.update_regulations_last_modification(guild_id)
            session.commit()
            print("Rule added")
            await self.show_regulations(ctx)
        except Exception as error:
            session.rollback()
            print(error)
        session.close()

    @commands.command(name='admindel')
    @commands.has_permissions(administrator=True)
    async def rule_delete_now(self, ctx: commands.Context, position: str):
        session = Session()
        try:
            guild_id = ctx.guild.id
            rules_channel = self.get_setting(guild_id, 'RulesChannel')
            if not position.isnumeric():
                error_message = f'{CONSTANT_RULES_CHANNEL_TYPE_ERROR}'
                await ctx.send(error_message)
                raise Exception(error_message)
            if not ctx.channel.name == rules_channel:
                error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}: "{rules_channel}"'
                await ctx.send(error_message)
                raise Exception(error_message)

            rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(Rules.id).all()
            if int(position) < 1 or int(position) > len(rules):
                error_message = 'Nie ma takiej pozycji'
                await ctx.send(error_message)
                raise Exception(error_message)
            rule_to_delete: Rules = rules[int(position) - 1]

            session.delete(rule_to_delete)
            print('Rule deleted')
            session.commit()
            self.update_regulations_last_modification(guild_id)
            await self.show_regulations(ctx)
        except Exception as error:
            print(error)
            session.rollback()
        session.close()

    @commands.command(name='show')
    async def show_regulations(self, ctx: commands.Context):
        try:
            rules_channel = self.get_setting(ctx.guild.id, 'RulesChannel')
            if not ctx.channel.name == rules_channel:
                error_message = f'{CONSTANT_RULES_CHANNEL_ERROR}: "{rules_channel}"'
                await ctx.send(error_message)
                raise Exception(error_message)
            await self.print_regulation(ctx.channel)
        except Exception as error:
            print(error)

    async def print_regulation(self, ctx: discord.TextChannel):
        session = Session()
        try:
            guild_id = ctx.guild.id
            amount_of_fields_in_embed = 5
            amount_of_rules_in_embed_field = 20
            await ctx.purge(limit=10)
            sleep(1)
            rules: list = session.query(Rules).join(Guilds).filter(Guilds.guild_id == guild_id).order_by(Rules.id).all()
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
        except Exception as error:
            print(error)
        session.close()

    @commands.command(name='help')
    async def show_help(self, ctx: commands.Context):
        rules_action_channel = self.get_setting(ctx.guild.id, 'RulesActionChannel')
        if not ctx.channel.name == rules_action_channel:
            error_message = f'{CONSTANT_RULES_ACTION_CHANNEL_ERROR}: "{rules_action_channel}"'
            await ctx.send(error_message)
            raise Exception(error_message)

        embed = discord.Embed(description=f'Komendy działają tylko na kanale: "{rules_action_channel}"',
                              color=0xff0000)
        embed.add_field(name=".add", value=f'Dodaj punkt do regulaminu (np: **.add "wojtek to gej"**'
                                           '\nlub **.add wojtek to gej**)', inline=False)
        embed.add_field(name=".del", value=f"Usuń punkt z regulaminu (np: **.del 12**)", inline=False)
        embed.add_field(name=".adminadd", value=f"Natychmiast dodaj punkt (**tylko admin**)", inline=False)
        embed.add_field(name=".admindel", value=f"Natychmiast usuń punkt (**tylko admin**)", inline=False)
        embed.add_field(name=".show", value=f"Pokaż regulamin", inline=True)
        embed.add_field(name=".help", value=f"Pokaż komendy", inline=True)
        embed.set_footer(text=f"Po dodaniu nowego punktu poczekaj aż Ojciec go zatwierdzi")
        await ctx.send(embed=embed)

    def update_regulations_last_modification(self, guild_id: int):
        today = date.today()
        d1 = today.strftime("%d/%m/%Y")
        self.set_setting(guild_id, 'RegulationsLastModification', d1)

    def get_setting(self, guild_id: int, setting_name: str):
        session = Session()
        try:
            setting: Configuration = session.query(Configuration).join(Guilds).filter(and_(
                Guilds.guild_id == guild_id,
                Configuration.setting_name == setting_name)).first()
            session.close()
            return setting.setting_value
        except Exception as error:
            print(error)
            session.close()
            raise Exception

    def set_setting(self, guild_id: int, setting_name: str, new_value: str):
        session = Session()
        try:
            setting: Configuration = session.query(Configuration).join(Guilds).filter(and_(Guilds.guild_id == guild_id),
                                                                                      Configuration.setting_name == setting_name).first()
            setting.setting_value = new_value
            session.commit()
        except Exception as error:
            print(error)
            session.rollback()
            raise Exception
        session.close()


def setup(bot):
    bot.add_cog(Regulation(bot))
