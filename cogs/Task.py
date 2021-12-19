import json
import os
import random

import discord
import requests
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pytz import utc
from sqlalchemy.orm import Session


import models

CONSTANT_POPE_TAGS = ['2137', 'jp2', 'jp2gmd']

load_dotenv()
KEY = os.getenv('TENOR_KEY')


class Task(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.async_sched = AsyncIOScheduler(timezone=utc)

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     self.guild = self.bot.get_guild(int(GUILD_ID))
    #     self.start_all_schedules()
    #
    # def start_all_schedules(self):
    #     self.async_sched.add_job(self.pope_reminder, 'cron', day_of_week='fri,sat,sun', hour=19, minute=37)
    #     #self.async_sched.start()
    #
    # async def pope_reminder(self):
    #     channel: discord.TextChannel = discord.utils.get(self.guild.channels, name=Task.get_pope_channel(session))
    #     r = requests.get(
    #         "https://g.tenor.com/v1/search?key=%s&q=%s&limit=%s" % (KEY, random.choice(CONSTANT_POPE_TAGS), 25))
    #
    #     if r.status_code == 200:
    #         data = json.loads(r.content)
    #     else:
    #         data = 'https://media.tenor.com/images/c9402647cb169182173c44701a2b5291/tenor.gif'
    #
    #     rand_index = random.randint(0, 24)
    #     embed = discord.Embed(colour=discord.Colour.blue())
    #     embed.set_image(url=data['results'][rand_index]['media'][0]['gif']['url'])
    #     await channel.send(embed=embed)
    #
    # @staticmethod
    # def get_pope_channel(s: Session) -> str:
    #     l_rules_action_channel = s.query(models.Configuration) \
    #         .filter(models.Configuration.SettingName == 'PopeChannel') \
    #         .first()
    #     return l_rules_action_channel.SettingValue


def setup(bot):
    bot.add_cog(Task(bot))
