import logging
import os
import sys
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

# logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

initial_extensions = (
    'cogs.Regulation',
    'cogs.Task',
)


class Regulaminson(commands.Bot):
    def __init__(self, prefix):
        self.bot_prefix = prefix
        super().__init__(command_prefix=prefix, help_command=None)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    def run(self):
        super().run(TOKEN, reconnect=True)

    async def on_ready(self):
        print('Logged in as:')
        print('Username: ' + self.user.name)
        print('------')
        await self.change_presence(activity=discord.Game(name=f'{self.bot_prefix}help'))


if __name__ == '__main__':
    regulaminson = Regulaminson('.')
    regulaminson.run()
