import asyncio, discord, requests, json
from discord.ext import commands

class Geniki(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot