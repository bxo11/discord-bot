import logging
import os
import sys
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

# logging
from models import new_guild_and_default_config, remove_guild

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MY_GUILD = os.getenv('MY_GUILD')

initial_extensions = (
    'cogs.Regulation',
)


class Regulaminson(commands.Bot):
    def __init__(self, prefix):
        self.bot_prefix = prefix
        super().__init__(command_prefix=prefix, help_command=None, intents=discord.Intents.all())

    async def startup(self):
        await self.wait_until_ready()
        await self.tree.sync(guild=discord.Object(
            id=MY_GUILD))  # If you want to define specific guilds, pass a discord object with id (Currently, this is global)
        print('Sucessfully synced applications commands')
        print(f'Connected as {self.user}')

    async def setup_hook(self):
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()
        self.loop.create_task(self.startup())

    def run(self):
        super().run(TOKEN, reconnect=True)

    async def on_guild_join(self, guild):
        new_guild_and_default_config(guild.id)

    async def on_guild_remove(self, guild):
        # remove_guild(guild.id)
        pass

    async def on_ready(self):
        print('Logged in as:')
        print('Username: ' + self.user.name)
        print('------')
        await self.change_presence(activity=discord.Game(name='ruling'))


if __name__ == '__main__':
    regulaminson = Regulaminson('.')
    regulaminson.run()
