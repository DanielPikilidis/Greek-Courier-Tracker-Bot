import discord, asyncio
from discord.ext import commands, tasks
from bs4 import BeautifulSoup as bs
from requests import post
from json import dump
from os.path import relpath

class CourierCenter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_ids.start()
        self.colour = 0xF37029
        self.tracking_url = "https://www.courier.gr/track/result/"
        self.main_url = "https://courier.gr/track/result?tracknr="
        self.logo = "https://i.imgur.com/w51MEA1.png"
        
    @commands.group(name="couriercenter", invoke_without_command=True)
    async def couriercenter(self, ctx: commands.Context):
        embed = discord.Embed(
            title="CourierCenter help",
            description="All the available subcommands for CourierCenter.",
            color=self.colour
        )

        embed.add_field(name="?/couriercenter track <id1> <id2> ...", value="Returns current status for the package(s)", inline=False)
        embed.add_field(name="?/couriercenter add <id> <description>", value="Adds the id to the list.", inline=False)
        embed.add_field(name="?/couriercenter edit <id> <new description>", value = "Replaces the old description with the new.", inline=False)
        embed.add_field(name="?/couriercenter remove <id>", value="Removed the id from the list.", inline=False)

        embed.set_thumbnail(url=self.logo)
        embed.set_footer(text=f"CourierCenter help requested by: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @couriercenter.command(name="track")
    async def track(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.send_status(ctx, id, False)
            await asyncio.sleep(1)

    @couriercenter.command(name="add")
    async def add(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.store_id(ctx, id, description)

    @couriercenter.command(name="edit")
    async def edit(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.remove_id(ctx, id)
        await self.store_id(ctx, id, description)

    @couriercenter.command(name="remove")
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

    async def send_status(self, ctx: commands.Context, id, silent, description=None):
        (result, status) = await self.get_last_status(id)
        if result == 1:
            if not silent:
                await ctx.send(f"Package ({id}) not found")
            return

        if description:
            title = description
        else:
            title = id

        embed = discord.Embed(
            title=title,
            url=f"{self.main_url}{id}",
            color=self.colour
        )

        embed.add_field(name="Location", value=status['location'], inline=True)
        embed.add_field(name="Description", value=status['description'], inline=True)
        embed.add_field(name="Date", value=f"{status['date']}", inline=False)

        embed.set_thumbnail(url=self.logo)
        await ctx.send(embed=embed)

    async def get_last_status(self, id) -> tuple:
        response = post(self.tracking_url, data={"tracknr": id})
        if response.status_code == 400:
            return (1, None)

        soup = bs(response.text, features="html.parser")

        if soup.find("h4", {"class": "error"}):
            return (1, None)

        last_status = soup.find("div", {"class": "track-table"}).contents[3]
        date = last_status.find("div", {"id": "date"}).contents[0]
        time = last_status.find("div", {"id": "time"}).contents[0]

        return (0, {
            "date": f"{date}, {time}", 
            "description": last_status.find("div", {"id": "action"}).contents[0].capitalize(),
            "location": last_status.find("div", {"id": "area"}).contents[0].title(),
            "delivered": soup.find("div", {"class": "status"}).contents[3].contents[0] == "(29) DeliveryCompleted"
        })

    async def store_id(self, ctx: commands.Context, id, description):
        (result, status) = await self.get_last_status(id)
        if result == 1:
            await ctx.send(f"Package ({id}) not found")
            return

        if status["delivered"]:
            await ctx.send("Package already delivered")
            await self.send_status(ctx, id, False)
            return
        
        if not next((i for i in self.bot.guild_data[str(ctx.guild.id)]['couriercenter'] if i['id'] == id), None):
            if self.bot.guild_data[str(ctx.guild.id)]['updates_channel'] == 0:
                updates_channel = str(ctx.channel.id)
                self.bot.guild_data[str(ctx.guild.id)]['updates_channel'] = updates_channel
                with open(relpath("data/guild_data.json"), "w") as file:
                    dump(self.bot.guild_data, file, indent=4)
                await ctx.send("Channel for updates has not been set. Using this one for now. You can change it with ?/updates.")
            self.bot.guild_data[str(ctx.guild.id)]['couriercenter'].append({"id": id, "description": description, "status": status})
            await ctx.send(f"Added {id} ({description}) to the list.")
            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send("Package already in list.\nIf you want to change its description use ?/couriercenter edit")

    async def remove_id(self, ctx: commands.Context, id):
        package = next((i for i in self.bot.guild_data[str(ctx.guild.id)]['couriercenter'] if i['id'] == id), None)
        if package:
            description = package['description']
            self.bot.guild_data[str(ctx.guild.id)]['couriercenter'].remove(package)
            await ctx.send(f"Removed {id} ({description}) from the list")

            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send(f"Package {id} is not in the list.")

    async def check_if_changed(self, guild, entry, old_status) -> tuple:
        (result, new) = await self.get_last_status(entry['id'])

        if new['date'] != old_status['date']:
            entry['status'] = new
            if new['delivered']:
                for i in self.bot.guild_data[guild]['couriercenter']:
                    if i['id'] == entry['id']:
                        self.bot.guild_data[guild]['couriercenter'].remove(i)

            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)

            return (True, new)
        return (False, None)

    @tasks.loop(minutes=5.0)
    async def update_ids(self):
        for guild in self.bot.guild_data:
            updates_channel = int(self.bot.guild_data[guild]['updates_channel'])
            if updates_channel == 0:
                continue
            for entry in self.bot.guild_data[guild]['couriercenter']:
                (result, new) = await self.check_if_changed(guild, entry, entry['status'])
                if result:
                    embed = discord.Embed(
                        title=entry['description'],
                        url=f"{self.main_url}{entry['id']}",
                        color=self.colour
                    )
                    embed.add_field(name="Location", value=new['location'], inline=True)
                    embed.add_field(name="Description", value=new['description'], inline=True)
                    embed.add_field(name="Date", value=f"{new['date']}", inline=False)

                    embed.set_thumbnail(url=self.logo)
                    channel = self.bot.get_channel(updates_channel)
                    await channel.send(embed=embed)

                    if new['delivered']:
                        await channel.send(f"Removed {entry['id']} ({entry['description']}) from the list")

                await asyncio.sleep(1)
                        

def setup(bot: commands.Bot):
    bot.add_cog(CourierCenter(bot))