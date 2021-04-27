from datetime import date
import random
import discord
import sqlalchemy.exc
from discord.ext import commands
from sqlalchemy.orm import Session
from db import session
import models

CONSTANT_RULES_ACTION_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_RULES_CHANNEL_ERROR = 'Zły kanał, użyj tej komendy na odpowiednim kanale'
CONSTANT_ACTION_CONFIRMATION = ['Akcja czeka na decyzje Ojca']


class Regulation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.rules_action_channel = Regulation.get_rules_action_channel(session)
        self.rules_channel = Regulation.get_rules_channel(session)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # author check
        if payload.member == self.bot.user:
            return
        # permissions check
        if not payload.member.guild_permissions.administrator:
            return
        mess_id: int = payload.message_id
        action: models.RulesActions = session.query(models.RulesActions) \
            .filter(models.RulesActions.MessageId == mess_id) \
            .first()
        # valid msg check
        if action is None:
            return

        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)

        # adding rule
        if action.Action == "add":
            rule: models.Rules = models.Rules(action.Text, str(action.Author), self.get_current_position(session))
            session.add(rule)
            self.change_current_position(session, '+', 1)

        # deleting rule
        elif action.Action == "delete":
            try:
                rule_to_delete: models.Rules = session.query(models.Rules) \
                    .filter(models.Rules.Position == action.Text) \
                    .first()
                session.delete(rule_to_delete)
                session.commit()
                self.change_current_position(session, '-', 1)
                self.recalculate_positions(session)
            except Exception:
                session.rollback()
                await channel.send('Coś poszło nie tak')

        session.delete(action)
        session.commit()
        self.update_regulations_last_modification(session)
        mess_obj: discord.PartialMessage = channel.get_partial_message(mess_id)
        await mess_obj.clear_reactions()
        await mess_obj.add_reaction('✅')
        l_rules_channel = discord.utils.get(self.bot.get_all_channels(), name=self.get_rules_channel(session))
        await self.show_reg(l_rules_channel)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        action: models.RulesActions = session.query(models.RulesActions) \
            .filter(models.RulesActions.MessageId == payload.message_id) \
            .first()

        if action is not None:
            session.delete(action)
            session.commit()

    @commands.command(name='add')
    async def rule_add(self, ctx: commands.Context, mess: str, *args):
        if self.rules_action_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_CHANNEL_ERROR}: {self.rules_action_channel}')
            return

        if len(args) != 0:
            for p in args:
                mess += " " + p

        action: models.RulesActions = models.RulesActions(ctx.message.id, "add", str(ctx.message.author), mess)
        session.add(action)
        session.commit()
        await ctx.message.add_reaction('🕖')
        await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
        print("Rule action added")

    @commands.command(name='del')
    async def rule_delete(self, ctx: commands.Context, mess: str):
        # channel check
        if self.rules_action_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_CHANNEL_ERROR}: {self.rules_action_channel}')
            return

        try:
            rule_to_delete: models.Rules = session.query(models.Rules) \
                .filter(models.Rules.Position == mess) \
                .first()
            # valid position check
            if rule_to_delete is None:
                await ctx.send('Nie ma takiej pozycji')
                return
        except sqlalchemy.exc.DataError:
            await ctx.send('Zły format danych')
            return

        action: models.RulesActions = models.RulesActions(ctx.message.id, "delete", str(ctx.message.author), mess)
        session.add(action)
        session.commit()
        await ctx.message.add_reaction('🕖')
        await ctx.send(random.choice(CONSTANT_ACTION_CONFIRMATION))
        print("Rule action added")

    @commands.command(name='adminadd')
    @commands.has_permissions(administrator=True)
    async def rule_add_now(self, ctx: commands.Context, mess: str, *args):
        if self.rules_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_CHANNEL_ERROR}: {self.rules_channel}')
            return

        if len(args) != 0:
            for p in args:
                mess += " " + p

        rule: models.Rules = models.Rules(mess, str(ctx.message.author), self.get_current_position(session))
        session.add(rule)
        session.commit()
        self.change_current_position(session, '+', 1)
        print("Rule added")
        self.update_regulations_last_modification(session)
        await self.show_regulations(ctx)

    @commands.command(name='admindel')
    @commands.has_permissions(administrator=True)
    async def rule_delete_now(self, ctx: commands.Context, position: int):
        if self.rules_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_CHANNEL_ERROR}: {self.rules_channel}')
            return

        rule_to_delete: models.Rules = session.query(models.Rules) \
            .filter(models.Rules.Position == position) \
            .first()

        if rule_to_delete is None:
            await ctx.send('Nie ma takiej pozycji')
            return

        session.delete(rule_to_delete)
        session.commit()
        self.change_current_position(session, '-', 1)
        print('Rule deleted')
        self.update_regulations_last_modification(session)
        self.recalculate_positions(session)
        await self.show_regulations(ctx)

    @commands.command(name='show')
    async def show_regulations(self, ctx: commands.Context):
        if self.rules_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_CHANNEL_ERROR}: {self.rules_channel}')
            return
        await self.show_reg(ctx.channel)

    @staticmethod
    async def show_reg(channel: discord.Message.channel):
        amount_of_fields_in_embed = 5
        amount_of_rules_in_embed_field = 20
        await channel.purge(limit=10)
        list_of_rules: list = session.query(models.Rules).all()
        regulations_last_modification: str = session.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'RegulationsLastModification') \
            .first() \
            .SettingValue

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

    @commands.command(name='help')
    async def show_help(self, ctx: commands.Context):
        if self.rules_action_channel != ctx.channel.name:
            await ctx.send(f'{CONSTANT_RULES_ACTION_CHANNEL_ERROR}: "{self.rules_action_channel}"')
            return

        embed = discord.Embed(description=f'Komendy działają tylko na kanale: "{self.rules_action_channel}"',
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

    @staticmethod
    def update_regulations_last_modification(s: Session):
        today = date.today()
        d1 = today.strftime("%d/%m/%Y")
        r_last_modification: models.Configuration = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'RegulationsLastModification') \
            .first()
        r_last_modification.SettingValue = d1
        s.commit()

    @staticmethod
    def get_rules_action_channel(s: Session):
        l_rules_action_channel = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'RulesActionChannel') \
            .first()
        return l_rules_action_channel.SettingValue

    @staticmethod
    def get_rules_channel(s: Session):
        l_rules_channel = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'RulesChannel') \
            .first()
        return l_rules_channel.SettingValue

    @staticmethod
    def get_current_position(s: Session):
        current_position: models.Configuration = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'CurrentRulePosition') \
            .first()
        return current_position.SettingValue

    @staticmethod
    def change_current_position(s: Session, operation: chr, value: int):
        current_position: models.Configuration = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'CurrentRulePosition') \
            .first()
        if operation == '+':
            current_position.SettingValue = int(current_position.SettingValue) + value
        elif operation == '-':
            current_position.SettingValue = int(current_position.SettingValue) - value
        s.commit()

    @staticmethod
    def recalculate_positions(s: Session):
        list_of_rules: list = s.query(models.Rules).order_by(models.Rules.Id).all()
        iterator: int = 1
        for elem in list_of_rules:
            elem.Position = iterator
            iterator += 1

        current_position: models.Configuration = s.query(models.Configuration) \
            .filter(models.Configuration.SettingName == 'CurrentRulePosition') \
            .first()
        current_position.SettingValue = iterator
        s.commit()


def setup(bot):
    bot.add_cog(Regulation(bot))
