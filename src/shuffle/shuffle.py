import discord
from discord.ext import commands

class ShuffleBot(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'HELLO MAN'))
        self.logger.info('Bot is ready')

    @commands.command()
    async def ping(self, ctx):
        await ctx.send('pong')
