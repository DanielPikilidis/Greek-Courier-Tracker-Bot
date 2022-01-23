import asyncio, discord
from bs4 import BeautifulSoup as bs
from discord.ext import commands, tasks
from requests import get
from json import dump
from os.path import relpath

class Speedex(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_ids.start()

    @commands.group(name="speedex", invoke_without_command=True)
    async def speedex(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Speedex help",
            description="All the available subcommands for Speedex.",
            color=discord.Color.green()
        )

        embed.add_field(name="?/speedex track <id1> <id2> ...", value="Returns current status for the parcel(s)", inline=False)
        embed.add_field(name="?/speedex add <id> <description>", value="Adds the id to the list.", inline=False)
        embed.add_field(name="?/speedex edit <id> <new description>", value = "Replaces the old description with the new.", inline=False)
        embed.add_field(name="?/speedex remove <id>", value="Removed the id from the list.", inline=False)

        embed.set_footer(text=f"speedex help requested by: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @speedex.command(name="track")
    async def track(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.send_status(ctx, id)

    @speedex.command(name="add")
    async def add(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.store_id(ctx, id, description)

    @speedex.command(name="edit")
    async def edit(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.remove_id(ctx, id)
        await self.store_id(ctx, id, description)

    @speedex.command(name="remove")
    async def remove(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.remove_id(ctx, id)

    ########### ERROR HANDLING ###########

    @track.error
    async def track_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing tracking id(s).")

    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing arguments.")

    @edit.error
    async def edit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing arguments.")

    @remove.error
    async def remove_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing tracking id.")

    ########### HELPER FUNCTIONS ###########

    async def send_status(self, ctx: commands.Context, id, description=None):
        result, status = await self.get_last_status(id)
        if result == 1:
            await ctx.send(f"Parcel ({id}) not found")
            return

        title = ""
        if not description:
            title = id
        else:
            title = description

        embed = discord.Embed(
            title=title,
            url=f"http://www.speedex.gr/isapohi.asp?voucher_code={id}&searcggo=Submit",
            color=discord.Color.green()
        )

        embed.add_field(name="Location", value=status['location'], inline=True)
        embed.add_field(name="Description", value=status['description'], inline=True)
        embed.add_field(name="Date", value=status['date'], inline=False)

        await ctx.send(embed=embed)

        if status['description'].upper() == "Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ":
            await self.remove_id(ctx, id)


    async def get_last_status(self, id):
        html = get(f"http://www.speedex.gr/speedex/NewTrackAndTrace.aspx?number={id}").text
        soup = bs(html, features="html.parser")
        timeline_section = soup.find("section", {"id": "timeline"})

        if timeline_section.text.find("Δεν βρέθηκαν αποτελέσματα.") != -1:
            return 1, None

        if timeline_section.text.find("Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ") != -1:
            status = timeline_section.find("div", {"class": "card-header delivered-speedex"})
            description = "Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ"
            other = status.find("span", {"class": "font-small-3"}).contents[0].split(", ")
            location = other[0]
            date = other[1]
            return 0, {"date": date, "description": description, "location": location}

        status = timeline_section.find_all("ul", {"class": "timeline"})[1]
        last = status.find_all("li", {"class": "timeline-item mt-3"})[-1]

        description = last.find("h4", {"class": "card-title"}).contents[0]
        other = last.find("span", {"class": "font-small-3"}).contents[0].split(", ")
        location = other[0]
        date = other[1]

        return 0, {"date": date, "description": description.capitalize(), "location": location.capitalize()}

    async def store_id(self, ctx: commands.Context, id, description):
        result, status = await self.get_last_status(id)
        if result == 1:
            await ctx.send(f"Parcel ({id}) not found")
            return
        
        if id not in self.bot.guild_data[str(ctx.guild.id)]['speedex']:
            self.bot.guild_data[str(ctx.guild.id)]['speedex'].append({"id": id, "description": description, "status": status})
            await ctx.send(f"Added {id} ({description}) to the list.")

        with open(relpath("../data/guild_data.json"), "w") as file:
            dump(self.bot.guild_data, file, indent=4)

    async def remove_id(self, ctx: commands.Context, id):
        for i in self.bot.guild_data[str(ctx.guild.id)]['speedex']:
            if i['id'] == id:
                description = i['description']
                self.bot.guild_data[str(ctx.guild.id)]['speedex'].remove(i)
                await ctx.send(f"Removed {id} ({description}) from the list")

        with open(relpath("../data/guild_data.json"), "w") as file:
            dump(self.bot.guild_data, file, indent=4)

    async def check_if_changed(self, guild, entry, old_status):
        result, new = await self.get_last_status(entry['id'])

        if new['date'] != old_status['date'] or new['time'] != old_status['time']:
            entry['status'] = new
            if new['description'].upper() == "Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ":
                for i in self.bot.guild_data[guild]['speedex']:
                    if i['id'] == entry['id']:
                        self.bot.guild_data[guild]['speedex'].remove(i)

            with open(relpath("../data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)

            return True, new
        return False, None

    @tasks.loop(minutes=5.0)
    async def update_ids(self):
        for guild in self.bot.guild_data:
            updates_channel = int(self.bot.guild_data[guild]['updates_channel'])
            if updates_channel == 0:
                continue
            for entry in self.bot.guild_data[guild]['speedex']:
                result, new = await self.check_if_changed(guild, entry, entry['status'])
                if result:
                    embed = discord.Embed(
                        title=entry['description'],
                        url=f"http://www.speedex.gr/isapohi.asp?voucher_code={entry['id']}&searcggo=Submit",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Location", value=new['location'], inline=True)
                    embed.add_field(name="Description", value=new['description'], inline=True)
                    embed.add_field(name="Date", value=f"{new['date']}, {new['time']}", inline=False)

                    channel = self.bot.get_channel(updates_channel)
                    await channel.send(embed=embed)

                    if new['description'].upper() == "Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ":
                        await channel.send(f"Removed {entry['id']} ({entry['description']}) from the list")

    @update_ids.before_loop
    async def before_update(self):
        await asyncio.sleep(180)


def setup(bot):
    bot.add_cog(Speedex(bot))