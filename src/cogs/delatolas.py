import discord, json
from discord.ext import commands, tasks
from requests import post
from dateutil import parser

import models
import sqlite3_handler

class Delatolas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_ids.start()
        self.colour = 0x211D70
        self.tracking_url = "https://docuclass.delatolas.com/js/code/epod/track_and_trace/tnt_server.php"
        self.main_url = "https://docuclass.delatolas.com/tnt_temp.php?id="
        self.logo = "https://i.imgur.com/eFfV98q.jpg"

    @commands.group(name="delatolas", invoke_without_command=True)
    async def delatolas(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Delatolas courier help",
            description="All the available subcommands for Delatolas courier.",
            color=self.colour
        )

        embed.add_field(name="?/delatolas track <id1> <id2> ...", value="Returns current status for the package(s)", inline=False)
        embed.add_field(name="?/delatolas add <id> <description>", value="Adds the id to the list.", inline=False)
        embed.add_field(name="?/delatolas edit <id> <new description>", value = "Replaces the old description with the new.", inline=False)
        embed.add_field(name="?/delatolas remove <id>", value="Removed the id from the list.", inline=False)

        embed.set_thumbnail(url=self.logo)
        embed.set_footer(text=f"Delatolas courier help requested by: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @delatolas.command(name="track")
    async def track(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.__track_id(ctx, id)

    @delatolas.command(name="add")
    async def add(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.__store_id(ctx, id, description)

    @delatolas.command(name="edit")
    async def edit(self, ctx: commands.Context, *, args):
        args = args.split()
        id = args[0]
        description = " ".join(args[1:])
        await self.__edit_package(ctx, id, description)

    @delatolas.command(name="remove")
    async def remove(self, ctx: commands.Context, *, args):
        for id in args.split():
            await self.__remove_id(ctx, id)

    async def __track_id(self, ctx: commands.Context, id: str):
        result = await self.__retrieve_package_info(id)
        await self.__send_status(result, ctx)

    async def __send_status(self, package: models.TrackingResult, ctx: commands.Context = None, channel_id: str = ""):
        if package.found == False:
            await ctx.send(f"Package ({package.id}) not found")
            return
        
        embed = discord.Embed(
            title=package.id,
            url=f"{self.main_url}{package.id}",
            color=self.colour
        )

        embed.add_field(name="Location", value=package.last_location.location, inline=True)
        embed.add_field(name="Description", value=package.last_location.description, inline=True)

        date = parser.isoparse(package.last_location.datetime)
        embed.add_field(name="Date", value=date.strftime("%d-%m-%Y, %H:%M"), inline=False)

        embed.set_thumbnail(url=package.courier_icon)
        
        if ctx is None:
            channel = self.bot.get_channel(int(channel_id))
            await channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    async def __retrieve_package_info(self, id: str):
        data = {
            "cmd": "getstatusnew",
            "orderid": id,
            "language": "el"
        }
        response = post(self.tracking_url, data=data)

        if response.status_code == 400:
            return models.TrackingResult(id, False, False, "", None)

        content = response.text.replace("\'", "\"")
        content = content.replace("h_date", "\"h_date\"")
        content = content.replace("h_status", "\"h_status\"")

        formatted_response = json.loads(content)

        if formatted_response[2][0] == 0:   # Status
            return models.TrackingResult(id, False, False, "", None)
        
        last_status = formatted_response[2][3][-1]
        status_messages = formatted_response[2][4]
        delivered = status_messages[-1]["selected"]

        last_location = models.Location("\u200b", last_status["h_status"], last_status["h_date"])

        return models.TrackingResult(
            id=id,
            courier_icon=self.logo,
            found=True,
            delivered=delivered,
            last_location=last_location
        )
            
    async def __store_id(self, ctx: commands.Context, id: str, description: str):
        update_channel = sqlite3_handler.get_update_channels_for_guild_ids([str(ctx.guild.id)])
        if update_channel[0][0] is None:
            await ctx.send("No updates channel set. Use `?/updates <#channel>` to set one.")
            return

        result = await self.__retrieve_package_info(id)
        if result.found == False:
            await ctx.send(f"Package ({id}) not found")
            return
        
        if result.delivered == True:
            await ctx.send(f"Package ({id}) already delivered")
            return
        
        p = models.Package(
            tracking_id=id, 
            courier_name="acs", 
            last_location=json.dumps(result.last_location.__dict__), 
            description=description
        )
        sqlite3_handler.insert_package(str(ctx.guild.id), p)
        await ctx.send(f"Package ({id}) added")

    async def __remove_id(self, ctx: commands.Context, id: str):
        sqlite3_handler.delete_package(str(ctx.guild.id), id)
        await ctx.send(f"Package ({id}) removed")

    async def __edit_package(self, ctx: commands.Context, id: str, new_description: str):
        sqlite3_handler.update_package_description(str(ctx.guild.id), id, new_description)
        await ctx.send(f"Package ({id}) description updated")

    async def __check_if_changed(self, tracking_id: str):
        new_info = await self.__retrieve_package_info(tracking_id)
        # Get last location from database
        result2 = sqlite3_handler.get_last_location_for_tracking_id(tracking_id)
        old_info = models.Location(**json.loads(result2))

        if new_info.last_location.datetime != old_info.datetime:
            if new_info.delivered == True:
                # Remove the package from the database if its delivered
                sqlite3_handler.delete_package(tracking_id)
            else:
                # Update the last location in the database if it hasn't been delivered
                sqlite3_handler.update_package_last_location(tracking_id, json.dumps(new_info.last_location.__dict__))

            # Get all the guild ids that might have this tracking id (I don't expect this to ever be more than 1 guild id but you never know)
            guild_ids = sqlite3_handler.get_guild_ids_for_tracking_id(tracking_id)
            # Get all the channels that want updates for these guild ids
            update_channels = sqlite3_handler.get_update_channels_for_guild_ids(guild_ids)

            for channel_id in update_channels:
                await self.__send_status(new_info, channel_id=channel_id[0])

    @tasks.loop(minutes=5.0)
    async def update_ids(self):
        # Getting all the ids that need to be tracked
        tracking_ids = sqlite3_handler.get_distinct_tracking_ids_for_courier_name("acs")
        # Checking each id
        for tracking_id in tracking_ids:
            await self.__check_if_changed(tracking_id)


def setup(bot: commands.Bot):
    bot.add_cog(Delatolas(bot))