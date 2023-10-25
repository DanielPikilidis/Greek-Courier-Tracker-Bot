import discord, logging, json
from os import getenv
from logging.config import dictConfig
from discord.ext import tasks

import sqlite3_handler, helpers, models
from log_config import LogConfig


bot = discord.Bot(intents=discord.Intents.all())

@bot.event
async def on_ready():
    logger.info("Bot is ready.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

@bot.event
async def on_guild_join(guild: discord.Guild):
    logger.info(f"Joined guild {guild.name} ({guild.id})")
    sqlite3_handler.insert_guild(logger, guild.id)

@bot.event
async def on_guild_remove(guild: discord.Guild):
    logger.info(f"Removed from guild {guild.name} ({guild.id})")
    sqlite3_handler.delete_guild(logger, guild.id)

@bot.command()
async def help(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="Help",
        description="All the available commands.",
        color=0xFFFFFF,
    )

    embed.add_field(
        name="/updates <#channel>",
        value="Set the channel to send updates to.",
        inline=False,
    )

    embed.add_field(
        name="/track <courier> <id>",
        value="Track a package.",
        inline=False,
    )

    embed.add_field(
        name="/add <courier> <id> <description>",
        value="Add a package to track.",
        inline=False,
    )

    embed.add_field(
        name="/remove <id>",
        value="Remove a package from tracking.",
        inline=False,
    )

    embed.add_field(
        name="/edit <id> <description>",
        value="Edit the description of a package.",
        inline=False,
    )

    embed.add_field(
        name="/list",
        value="List all the packages you are tracking.",
        inline=False,
    )

    await ctx.respond(embed=embed)

@bot.command()
async def updates(
        ctx: discord.ApplicationContext, 
        channel: discord.Option(discord.TextChannel, "The channel to send updates to.")
        ):
    logger.info(f"Set updates channel for guild {ctx.guild.name} ({ctx.guild.id}) to {channel.name} ({channel.id})")
    sqlite3_handler.update_channel(logger, ctx.guild.id, channel.id)
    await ctx.respond(f"Set updates channel to {channel.mention}")

@bot.command()
async def track(
        ctx: discord.ApplicationContext,
        courier: discord.Option(str, choices=["acs", "couriercenter", "easymail", "skroutz", "elta", "speedex", "geniki"], description="The courier to track."),
        id: discord.Option(str, "The tracking id."),
        ):
    package = await helpers.retrieve_package_info(courier, id)
    await helpers.send_status(package, ctx)

@bot.command()
async def add(
        ctx: discord.ApplicationContext,
        courier: discord.Option(str, choices=["acs", "couriercenter", "easymail", "skroutz", "elta", "speedex", "geniki"], description="The courier to track."),
        id: discord.Option(str, "The tracking id."),
        description: discord.Option(str, "The description of the package."),
        ):
    update_channel = sqlite3_handler.get_update_channels_for_guild_ids(logger, [ctx.guild.id])[0]
    if update_channel[0] is None:
        await ctx.respond("No updates channel set. Use `/updates <#channel>` to set one.")
        return

    await helpers.store_package(logger, ctx, courier, id, description)

@bot.command()
async def remove(
        ctx: discord.ApplicationContext,
        id: discord.Option(str, "The tracking id."),
        ):
    await helpers.remove_package(logger, ctx, id)

@bot.command()
async def edit(
        ctx: discord.ApplicationContext,
        id: discord.Option(str, "The tracking id."),
        description: discord.Option(str, "The new description of the package."),
        ):
    await helpers.edit_package(logger, ctx, id, description)

@bot.command()
async def list(
        ctx: discord.ApplicationContext,
        ):
    await helpers.list_packages(logger, ctx)


@tasks.loop(minutes=10.0)
async def update_ids():
    logger.debug("Starting update_ids")

    # Get all courier names in the database
    courier_names = sqlite3_handler.get_distinct_courier_names(logger)
    for courier_name in courier_names:
        # For each courier get the ids in the database
        ids = sqlite3_handler.get_distinct_tracking_ids_for_courier_name(logger, courier_name)
        for id in ids:
            logger.debug(f"Checking id {id} for courier {courier_name}")
            # For each id get the package info
            package = await helpers.retrieve_package_info(courier_name, id)
            if package is None:
                continue
            
            try:
                last_location = package.last_location
            except:
                continue
            
            last_stored_location = models.Location(**json.loads(sqlite3_handler.get_last_location_for_tracking_id(logger, id)))
            logger.debug(f"last_location: {last_location}, last_stored_location: {last_stored_location}")
            if last_location == last_stored_location:
                continue

            # Last location has changed

            # Getting the update channels for the guilds that are watching this package
            guild_ids = sqlite3_handler.get_guild_ids_for_tracking_id(logger, id)
            update_channels = sqlite3_handler.get_update_channels_for_guild_ids(logger, guild_ids)
            
            # Sending the updated status to the update channels
            for channel_id in update_channels:
                await helpers.send_status(package, bot=bot, channel_id=channel_id[0])
            
            if package.delivered:
                for guild_id in guild_ids:
                    sqlite3_handler.delete_package(logger, guild_id, id)
            else:
                sqlite3_handler.update_package_last_location(logger, id, json.dumps(last_location.__dict__))

@update_ids.before_loop
async def update_ids_before_loop():
    await bot.wait_until_ready()

if __name__ == "__main__":
    dictConfig(LogConfig().dict())
    logger = logging.getLogger(getenv("LOG_NAME", "courier-tracking-bot"))

    helpers.check_database(logger)

    update_ids.start()


key = getenv("DISCORD_KEY")
if key is None:
    logger.error("DISCORD_KEY environment variable not set.")
    exit(1)

logger.debug(key)

bot.run(key)