import discord
from discord.ext import commands

DISCORD_FUN_CHANNEL = 832702123270471691


class Fun(commands.Cog):
    bot: discord.Client = None

    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Fun(bot))
