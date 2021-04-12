import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!@')


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='radd', help='Responds with a random quote from Brooklyn 99')
async def rule_add(context, rule):
    response = rule
    await context.send(response)


bot.run(TOKEN)
