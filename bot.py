import discord, os, json
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

prefix = "?/"
bot = commands.Bot(command_prefix=prefix, help_command=None, intents=intents)

started = False
couriers = []

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started = False
        self.couriers = []
        
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.started:
            with open("guild_data.json", "r") as f:
                bot.guild_data = json.loads(f.read())

            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    try:
                        self.bot.load_extension(f"cogs.{filename[:-3]}")
                        print(f"Loaded cog: {filename[:-3].capitalize()}")
                        self.couriers.append(self.bot.get_cog(filename[:-3].capitalize()))
                    except:
                        print(f"Failed to load cog: {filename[:-3].capitalize()}")
            
            self.started = True
            print("Bot logged in and ready")

        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="?/help"))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        bot.guild_data[str(guild.id)] = {"updates_channel": 0, "acs": [], "easymail": [], "elta": [], "speedex": [], "geniki": []}
        with open("guild_data.json", "w") as file:
            json.dump(bot.guild_data, file, indent=4)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        bot.guild_data.pop(str(guild.id))
        with open("guild_data.json", "w") as file:
            json.dump(bot.guild_data, file, indent=4)

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

        embed.add_field(
            name="?/tracking-update",
            value="Returns the current status for all the parcels in the list. If a parcel arrived, it is removed from that list",
            inline=False
        )

        embed.add_field(
            name="?/updates <#channel>",
            value="Sets the channel for the updates (when a parcel moves).",
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
    async def updates(self, ctx: commands.Context, *, args):
        args = args.split()
        channel = bot.get_channel(int(args[0][2:-1]))
        if channel is None:
            await ctx.send("Invalid channel.")
            return

        bot.guild_data[str(ctx.guild.id)]['updates_channel'] = str(channel.id)
        await ctx.send("Updates channel changed.")
        with open("guild_data.json", "w") as file:
            json.dump(bot.guild_data, file, indent=4)

    @updates.error
    async def updates_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing channel arguments.")

    @commands.command(name="track")
    async def track(self, ctx: commands.Context, *, args):
        courier = None
        id = args.split()[0]
        if len(id) == 10:
            courier = next(i for i in self.couriers if i.qualified_name == "Acs")
        elif len(id) == 11:
            courier = next(i for i in self.couriers if i.qualified_name == "Easymail")
        elif len(id) == 12:
            courier = next(i for i in self.couriers if i.qualified_name == "Speedex")
        elif len(id) == 13:
            courier = next(i for i in self.couriers if i.qualified_name == "Elta")

        await courier.send_status(ctx, id)

    @track.error
    async def track_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing tracking id.")

    @commands.command(name="tracking-update")
    async def tracking_update(self, ctx: commands.Context):
        guild = bot.guild_data[str(ctx.guild.id)]
        for i in self.couriers:
            cur = i.qualified_name.lower()
            for entry in guild[cur]:
                await i.send_status(ctx, entry['id'], entry['description'])


if __name__ == "__main__":
    bot.add_cog(Main(bot))

    if not os.path.exists("guild_data.json"):
        with open("guild_data.json", "a+") as file:
            json.dump({}, file, indent=4)

    if os.path.exists("config.txt"):
        with open("config.txt", "r") as file:
            bot_key = file.read()
        bot.run(bot_key)
    else:
        open("config.txt", "w").close()
        print("Paste the api key in the config.txt (nothign else in there) and restart the bot.")
