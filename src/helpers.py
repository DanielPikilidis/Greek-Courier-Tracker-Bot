import discord, requests, sqlite3, logging, json, datetime
from dateutil import parser
from os import getenv
from os.path import exists
from discord.ext import pages

import models, sqlite3_handler

TRACKER_URL = getenv("TRACKER_URL", "https://courier-api.danielpikilidis.com")

courier_urls = {
    "acs": "https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking3&generalCode=",
    "couriercenter": "https://courier.gr/track/result?tracknr=",
    "easymail": "https://trackntrace.easymail.gr/",
    "skroutz": "https://www.skroutzlastmile.gr/#",
    "elta": "https://itemsearch.elta.gr/Query/Direct/",
    "speedex": "http://www.speedex.gr/isapohi.asp?voucher_code=",
    "geniki": "https://www.taxydromiki.com/en/track/",
}

async def send_status(logger: logging.Logger, package: models.TrackingResult, courier_name: str, guild_id: str = "", ctx: discord.ApplicationContext = None, bot: discord.Bot = None, channel_id: str = ""):
    if package is None:
        await ctx.respond("Failed to retrieve package info, please try again.")
        return
    
    if package.found == False:
        await ctx.respond(f"Package ({package.id}) not found")
        return
    
    if guild_id != "":
        description = sqlite3_handler.get_description_for_tracking_id(logger, guild_id, package.id)
        if description is None:
            description = package.id
    else:
        description = package.id

    embed = discord.Embed(
        title=description,
        url=courier_urls[courier_name] + package.id,
        color=0xFFFFFF
    )

    embed.add_field(name="Location", value=package.last_location.location, inline=True)
    embed.add_field(name="Description", value=package.last_location.description, inline=True)

    date = parser.isoparse(package.last_location.datetime)
    embed.add_field(name="Date", value=date.strftime("%d-%m-%Y, %H:%M"), inline=False)

    embed.set_thumbnail(url=package.courier_icon)
    
    if ctx is None:
        channel = bot.get_channel(int(channel_id))
        await channel.send(embed=embed)
    else:
        await ctx.respond(embed=embed)


async def retrieve_package_info(logger: logging.Logger, courier: str, id: str) -> models.TrackingResult:
    try:
        logger.debug(f"Requesting data from {TRACKER_URL}/track-one/{courier}/{id}")
        res = requests.get(f"{TRACKER_URL}/track-one/{courier}/{id}", timeout=2.5)
    except requests.exceptions.Timeout:
        return None
    
    if res.status_code >= 500:
        logger.debug(f"Request failed with status code {res.status_code}")
        return None

    data = res.json()["data"]
    package = data[id]

    if package["found"] == False:
        return None

    if len(package["locations"]) == 0:
        last_location = models.Location(
            location="Unknown",
            description="Unknown",
            datetime=datetime.datetime.fromtimestamp(0).isoformat()
        )
    else:
        last_location = models.Location(
            location=package["locations"][-1]["location"],
            description=package["locations"][-1]["description"],
            datetime=package["locations"][-1]["datetime"]
        )

    return models.TrackingResult(
        id=id,
        courier_icon=package["courier_icon"],
        found=package["found"],
        delivered=package["delivered"],
        last_location=last_location
    )

async def store_package(logger: logging.Logger, ctx: discord.ApplicationContext, courier: str, id: str, description: str):
    res = await retrieve_package_info(logger, courier, id)

    if not res.found:
        await ctx.respond(f"Package ({id}) not found.")
        return
    
    if res.delivered:
        await ctx.respond(f"Package ({id}) has already been delivered.")
        return
    
    p = models.Package(
        tracking_id=id,
        courier_name=courier,
        last_location=json.dumps(res.last_location.__dict__),
        description=description
    )

    sqlite3_handler.insert_package(logger, str(ctx.guild.id), p)
    await ctx.respond(f"Added package {id} ({description})")

async def remove_package(logger: logging.Logger, ctx: discord.ApplicationContext, id: str):
    sqlite3_handler.delete_package(logger, str(ctx.guild.id), id)
    await ctx.respond(f"Removed package ({id})")

async def edit_package(logger: logging.Logger, ctx: discord.ApplicationContext, id: str, description: str):
    sqlite3_handler.update_package_description(logger, str(ctx.guild.id), id, description)
    await ctx.respond(f"Edited package ({id})")

async def list_packages(logger: logging.Logger, ctx: discord.ApplicationContext):
    packages = []

    tracking_ids = sqlite3_handler.get_tracking_ids_for_guild_id(logger, ctx.guild.id)
    if len(tracking_ids) == 0:
        await ctx.respond("No packages found.")
        return
    

    for tracking_id in tracking_ids:
        courier_name = sqlite3_handler.get_courier_name_for_tracking_id(logger, tracking_id)
        l = sqlite3_handler.get_last_location_for_tracking_id(logger, tracking_id)

        last_location = models.Location(**json.loads(l))

        description = sqlite3_handler.get_description_for_tracking_id(logger, str(ctx.guild.id), tracking_id)

        embed = discord.Embed(
            title=description,
        )

        embed.add_field(name="Courier", value=courier_name, inline=True)
        embed.add_field(name="Location", value=last_location.location, inline=True)
        embed.add_field(name="Description", value=last_location.description, inline=True)

        date = parser.isoparse(last_location.datetime)
        embed.add_field(name="Date", value=date.strftime("%d-%m-%Y, %H:%M"), inline=False)

        packages.append(
            embed
        )

    paginator = pages.Paginator(pages=packages)

    paginator.add_button(
        pages.PaginatorButton(
            "prev", label="<", style=discord.ButtonStyle.green, loop_label="lst"
        )
    )

    paginator.add_button(
        pages.PaginatorButton(
            "next", style=discord.ButtonStyle.green, loop_label="fst"
        )
    )

    await paginator.respond(ctx.interaction, ephemeral=False)

def check_guilds(logger: logging.Logger, bot: discord.Bot):
    conn = sqlite3.connect("/data/data.sqlite3")

    cur = conn.cursor()

    cur.execute("SELECT guild_id FROM Guilds")
    db_guild_ids = [ str(guild_id[0]) for guild_id in cur.fetchall() ]

    logger.debug(f"Guilds in database: {db_guild_ids}")

    conn.close()

    bot_guild_ids = [ str(guild.id) for guild in bot.guilds ]

    logger.debug(f"Guilds the bot has joined: {bot_guild_ids}")

    for guild_id in bot_guild_ids:
        if guild_id not in db_guild_ids:
            logger.info(f"Adding guild {guild_id}")
            sqlite3_handler.insert_guild(logger, str(guild_id))

def create_database(logger: logging.Logger):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
    ATTACH DATABASE 'data.sqlite3' AS GuildData;

    CREATE TABLE IF NOT EXISTS Packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT,
        courier_name TEXT,
        description TEXT,
        last_location TEXT,
        guild_id TEXT,
        FOREIGN KEY (guild_id) REFERENCES Guilds(guild_id)
    );

    CREATE TABLE IF NOT EXISTS Guilds (
        guild_id TEXT PRIMARY KEY,
        updates_channel TEXT
    );
    """

    logger.debug(query)

    cur.executescript(query)
    conn.commit()
    conn.close()
   
    logger.info("Created database.")

def check_database(logger: logging.Logger):
    if not exists("/data/data.sqlite3"):
        with open("/data/data.sqlite3", "w") as file:
            pass
        create_database(logger)
