import discord
from discord.ext import commands, tasks
from requests import get
from json import dump
from os.path import relpath

class Acs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_ids.start()
        
    @commands.group(name="acs", invoke_without_command=True)
    async def acs(self, ctx: commands.Context):
        embed = discord.Embed(
            title="ACS help",
            description="All the available subcommands for ACS.",
            color=discord.Color.red()
        )

        embed.add_field(name="?/acs track <id1> <id2> ...", value="Returns current status for the parcel(s)", inline=False)
        embed.add_field(name="?/acs add <id> <description>", value="Adds the id to the list.", inline=False)
        embed.add_field(name="?/acs edit <id> <new description>", value = "Replaces the old description with the new.", inline=False)
        embed.add_field(name="?/acs remove <id>", value="Removed the id from the list.", inline=False)

        embed.set_footer(text=f"ACS help requested by: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @acs.command(name="track")
    async def track(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.send_status(ctx, id, False)

    @acs.command(name="add")
    async def add(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.store_id(ctx, id, description)

    @acs.command(name="edit")
    async def edit(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.remove_id(ctx, id)
        await self.store_id(ctx, id, description)

    @acs.command(name="remove")
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
                await ctx.send(f"Parcel ({id}) not found")
            return

        if description:
            title = description
        else:
            title = id

        embed = discord.Embed(
            title=title,
            url=f"https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking&cid=2ΒΞ45143&generalCode={id}&p_p_id=ACSCustomersAreaTrackTrace_WAR_ACSCustomersAreaportlet&stop_mobile=yes",
            color=discord.Color.red()
        )

        embed.add_field(name="Location", value=status['location'], inline=True)
        embed.add_field(name="Description", value=status['description'], inline=True)
        embed.add_field(name="Date", value=f"{status['date']}", inline=False)

        await ctx.send(embed=embed)

        if status['delivered']:
            await self.remove_id(ctx, id)

    async def get_last_status(self, id) -> tuple:
        response = get(f"https://api.acscourier.net/api/parcels/search/{id}")
        if response.status_code == 400:
            return (1, None)

        package = (response.json())["items"][0]
        if package["notes"] == "Η αποστολή δεν βρέθηκε":
            return (1, None)
            
        delivered = package["isDelivered"]

        if len(package["statusHistory"]) == 0:
            return (0, {
                "date": "\u200b", 
                "description": "Προς Παραλαβη", 
                "location": "\u200b",
                "delivered": delivered
            })
        else:
            last_status = package["statusHistory"][-1]
            date = last_status["controlPointDate"]
            date = f"{date[8:10]}-{date[5:7]}-{date[0:4]}, {date[11:19]}"
            return (0, {
                "date": date, 
                "description": last_status["description"].capitalize(), 
                "location": last_status["controlPoint"].capitalize(), 
                "delivered": delivered
            })

    async def store_id(self, ctx: commands.Context, id, description):
        (result, status) = await self.get_last_status(id)
        if result == 1:
            await ctx.send(f"Parcel ({id}) not found")
            return
        
        if not next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None):
            self.bot.guild_data[str(ctx.guild.id)]['acs'].append({"id": id, "description": description, "status": status})
            await ctx.send(f"Added {id} ({description}) to the list.")
            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send("Parcel already in list.\nIf you want to change its description use ?/acs edit")

    async def remove_id(self, ctx: commands.Context, id):
        parcel = next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None)
        if parcel:
            description = parcel['description']
            self.bot.guild_data[str(ctx.guild.id)]['acs'].remove(parcel)
            await ctx.send(f"Removed {id} ({description}) from the list")

            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send(f"Parcel {id} is not in the list.")

    async def check_if_changed(self, guild, entry, old_status) -> tuple:
        (result, new) = await self.get_last_status(entry['id'])

        if new['date'] != old_status['date']:
            entry['status'] = new
            if new['delivered']:
                for i in self.bot.guild_data[guild]['acs']:
                    if i['id'] == entry['id']:
                        self.bot.guild_data[guild]['acs'].remove(i)

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
            for entry in self.bot.guild_data[guild]['acs']:
                (result, new) = await self.check_if_changed(guild, entry, entry['status'])
                if result:
                    embed = discord.Embed(
                        title=entry['description'],
                        url=f"https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking&cid=2ΒΞ45143&generalCode={entry['id']}&p_p_id=ACSCustomersAreaTrackTrace_WAR_ACSCustomersAreaportlet&stop_mobile=yes",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Location", value=new['location'], inline=True)
                    embed.add_field(name="Description", value=new['description'], inline=True)
                    embed.add_field(name="Date", value=f"{new['date']}", inline=False)

                    channel = self.bot.get_channel(updates_channel)
                    await channel.send(embed=embed)

                    if new['delivered']:
                        await channel.send(f"Removed {entry['id']} ({entry['description']}) from the list")
                        

def setup(bot: commands.Bot):
    bot.add_cog(Acs(bot))