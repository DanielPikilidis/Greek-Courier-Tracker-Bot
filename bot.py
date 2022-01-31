import discord, logging
from discord.ext import commands
from logging.handlers import TimedRotatingFileHandler
from os import listdir, makedirs
from os.path import relpath, exists
from json import loads, dump
from sys import stdout


class Main(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started = False
        self.couriers = []
        self.ENABLE_DHL = False
        
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.started:
            with open("data/guild_data.json", "r") as file:
                self.bot.guild_data = loads(file.read())

            for filename in listdir("./cogs"):
                if filename[:-3] == "dhl" and not self.ENABLE_DHL:
                    self.bot.logger.info("DHL disabled, not loading")
                    continue

                if filename.endswith(".py"):
                    try:
                        self.bot.load_extension(f"cogs.{filename[:-3]}")
                        self.bot.logger.info(f"Loaded cog: {filename[:-3].capitalize()}")
                        self.couriers.append(self.bot.get_cog(filename[:-3].capitalize()))
                    except:
                        self.bot.logger.warning(f"Failed to load cog: {filename[:-3].capitalize()}")
            
            self.started = True
            self.bot.logger.info(f"Bot logged in and ready. Joined guilds: {len(bot.guilds)}")

        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="?/help"))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.bot.logger.info(f"Joined guild {guild.id}")
        self.bot.guild_data[str(guild.id)] = {"updates_channel": 0, "acs": [], "easymail": [], "elta": [], "speedex": [], "geniki": [], "skroutz": [], "dhl": []}
        with open(relpath("data/guild_data.json"), "w") as file:
            dump(bot.guild_data, file, indent=4)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.logger.info(f"Left guild {guild.id}")
        self.bot.guild_data.pop(str(guild.id))
        with open(relpath("data/guild_data.json"), "w") as file:
            dump(bot.guild_data, file, indent=4)

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Help",
            description="All the available commands.",
            color=discord.Color.blue()
        )

        embed.add_field(name="acs", value="Returns available commands for ACS.", inline=False)
        embed.add_field(name="easymail", value="Returns available commands for EasyMail.", inline=False)
        embed.add_field(name="elta", value="Returns available commands for ELTA.", inline=False)
        embed.add_field(name="speedex", value="Returns available commands for Speedex.", inline=False)
        embed.add_field(name="skroutz", value="Returns available commands for Skroutz Last Mile.", inline=False)
        if self.ENABLE_DHL:
            embed.add_field(name="dhl", value="Returns available commands for DHL.", inline=False)

        embed.add_field(
            name="?/tracking-update",
            value="Returns the current status for all the parcels in the list. If a parcel arrived, it is removed from that list",
            inline=False
        )

        if not self.bot.guild_data[str(ctx.guild.id)]["updates_channel"]:
            embed.add_field(
                name="?/updates <#channel>",
                value = "Sets the channel to send updates when a parcel moves.\n"
                        "A channel for updates has not been set, so no updates will be sent!",
                inline=False
            )
        else:
            embed.add_field(
                name="?/updates <#channel>",
                value="Sets the channel to send updates when a parcel moves",
                inline=False
            )


        embed.add_field(
            name="?/track <id>",
            value="Figures out the correct courier and returns the parcel status.",
            inline=False
        )

        embed.set_footer(text=f"Help requested by: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="updates")
    async def updates(self, ctx: commands.Context, arg1):
        channel = self.bot.get_channel(int(arg1[2:-1]))
        if channel is None:
            await ctx.send("Invalid channel.")
            return

        self.bot.guild_data[str(ctx.guild.id)]['updates_channel'] = str(channel.id)
        await ctx.send("Updates channel changed.")
        with open(relpath("data/guild_data.json"), "w") as file:
            dump(bot.guild_data, file, indent=4)

    @updates.error
    async def updates_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing channel arguments.")

    @commands.command(name="track")
    async def track(self, ctx: commands.Context, arg1):
        id = arg1
        if len(id) == 10:
            courier = next(i for i in self.couriers if i.qualified_name == "Acs")
            await courier.send_status(ctx, id, True)
        elif len(id) == 11:
            courier = next(i for i in self.couriers if i.qualified_name == "Easymail")
            await courier.send_status(ctx, id, True)
        elif len(id) == 12:
            courier = next(i for i in self.couriers if i.qualified_name == "Speedex")
            await courier.send_status(ctx, id, True)
        elif len(id) == 13:
            couriers = ["Elta", "Skroutz"]
            for c in couriers:
                courier = next(i for i in self.couriers if i.qualified_name == c)
                await courier.send_status(ctx, id, True)

    @track.error
    async def track_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing tracking id.")

    @commands.command(name="tracking-update")
    async def tracking_update(self, ctx: commands.Context):
        guild = self.bot.guild_data[str(ctx.guild.id)]
        for i in self.couriers:
            cur = i.qualified_name.lower()
            for entry in guild[cur]:
                await i.send_status(ctx, entry['id'], False, entry['description'])


def setup_logger() -> logging.Logger:
    discord_logger = logging.getLogger('discord')
    handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode='w')
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    discord_logger.addHandler(handler)

    logger = logging.getLogger("output")
    logname = "logs/output.log"
    logger.level = logging.INFO
    handler = TimedRotatingFileHandler(logname, when="midnight", interval=1, backupCount=1)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    handler.suffix = "%Y%m%d"

    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(stdout))
    
    return logger

if __name__ == "__main__":
    prefix = "?/"
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    bot.logger = setup_logger()

    bot.add_cog(Main(bot))

    if not exists("data"):
        makedirs("data")

    if not exists("data/guild_data.json"):
        with open("data/guild_data.json", "w") as file:
            dump({}, file, indent=4)

    if exists("data/config.txt"):
        with open("data/config.txt", "r") as file:
            key = file.read()
        bot.run(key)
    else:
        open("data/config.txt", "w").close()
        print("Paste your key in config.txt file in data/")
