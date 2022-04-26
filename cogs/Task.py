import discord.utils
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from dotenv import load_dotenv
from pytz import utc
from sqlalchemy.exc import SQLAlchemyError
from db import Session
from models import Guilds

load_dotenv()


class Task(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.async_scheduler = AsyncIOScheduler(timezone=utc)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_all_schedules()
        self.example()

    def start_all_schedules(self):
        self.async_scheduler.add_job(self.async_example, 'cron', hour=19, minute=37)
        self.async_scheduler.start()

    def example(self):
        with Session() as session, session.begin():
            try:
                guilds: list = session.query(Guilds).order_by(Guilds.id).all()
                for guild in guilds:
                    pass
            except SQLAlchemyError as error:
                print(error)
                return

    async def async_example(self):
        pass


async def setup(bot):
    await bot.add_cog(Task(bot))
