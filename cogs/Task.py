import json
import os
import random

import discord
import requests
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

CONSTANT_POPE_TAGS = ['2137', 'jp2', 'jp2gmd']

load_dotenv()
KEY = os.getenv('TENOR_KEY')
GUILD_ID = os.getenv('GUILD_ID')


class Task(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.async_sched = AsyncIOScheduler()
        self.guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(int(GUILD_ID))
        self.start_all_schedules()

    def start_all_schedules(self):
        self.async_sched.add_job(self.pope_reminder, 'cron', hour=21, minute=37)
        self.async_sched.start()

    async def pope_reminder(self):
        channel: discord.TextChannel = discord.utils.get(self.guild.channels, name="📝kanal-do-pisania")
        r = requests.get(
            "https://g.tenor.com/v1/search?key=%s&q=%s&limit=%s" % (KEY, random.choice(CONSTANT_POPE_TAGS), 25))

        if r.status_code == 200:
            data = json.loads(r.content)
        else:
            data = 'https://media.tenor.com/images/c9402647cb169182173c44701a2b5291/tenor.gif'

        rand_index = random.randint(0, 24)
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_image(url=data['results'][rand_index]['media'][0]['gif']['url'])
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Task(bot))
