import discord
from discord.ext import commands, tasks
from json import dump
from os.path import relpath
from selenium import webdriver
from selenium.webdriver.firefox import options
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup as bs
from datetime import datetime


class Acs(commands.Cog, name="ACS"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_ids.start()
        self.colour = 0xE42229
        self.driver = setup_selenium()

    @commands.group(name="acs", invoke_without_command=True)
    async def acs(self, ctx: commands.Context):
        embed = discord.Embed(
            title="ACS help",
            description="All the available subcommands for ACS.",
            color=self.colour
        )

        embed.add_field(name="?/acs track <id1> <id2> ...", value="Returns current status for the package(s)", inline=False)
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
                await ctx.send(f"package ({id}) not found")
            return

        if description:
            title = description
        else:
            title = id

        embed = discord.Embed(
            title=title,
            url=f"https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking3&generalCode={id}",
            color=self.colour
        )

        embed.add_field(name="Location", value=status['location'], inline=True)
        embed.add_field(name="Description", value=status['description'], inline=True)
        embed.add_field(name="Date", value=f"{status['date']}", inline=False)

        await ctx.send(embed=embed)

    async def get_last_status(self, id) -> tuple:
        url = f"https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking&generalCode={id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.TAG_NAME, 'app-parcels-search-results')))
        except TimeoutException:
            try:    # Trying 1 more time before giving up.
                WebDriverWait(self.driver, 8).until(EC.visibility_of_element_located((By.TAG_NAME, 'app-parcels-search-results')))
            except TimeoutException:
                return (1, None)

        soup = bs(self.driver.page_source, features="html.parser")
        tables = soup.find_all("tbody")
        tbody1 = tables[-2]
        tbody2 = tables[-1]

        status_list = tbody2.find_all("tr")

        if len(status_list) == 0:   # Invalid id
            return (1, None)

        last = status_list[-1]

        details = last.find_all("td")
        dt = details[1].text
        dt = dt.replace('μ.μ.', 'PM')
        dt = dt.replace('π.μ.', 'AM')

        try:
            date = datetime.strptime(dt, ' %d/%m/%y, %I:%M %p ').strftime('%d/%m/%Y, %H:%M')
        except ValueError:  # No idea what happens here
            date = "\u200b"

        return (0, {
            "date": date,
            "description": details[2].text.capitalize(),
            "location": details[0].text.capitalize(),
            "delivered": tbody1.find("tr", {"class": "delivered"}) != 0
        })


    async def store_id(self, ctx: commands.Context, id, description):
        (result, status) = await self.get_last_status(id)
        if result == 1:
            await ctx.send(f"package ({id}) not found")
            return

        if status["delivered"]:
            await ctx.send("package already delivered")
            await self.send_status(ctx, id, False)
            return

        if not next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None):
            self.bot.guild_data[str(ctx.guild.id)]['acs'].append({"id": id, "description": description, "status": status})
            await ctx.send(f"Added {id} ({description}) to the list.")
            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send("package already in list.\nIf you want to change its description use ?/acs edit")

    async def remove_id(self, ctx: commands.Context, id):
        package = next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None)
        if package:
            description = package['description']
            self.bot.guild_data[str(ctx.guild.id)]['acs'].remove(package)
            await ctx.send(f"Removed {id} ({description}) from the list")

            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send(f"package {id} is not in the list.")

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
                        url=f"https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking3&generalCode={entry['id']}",
                        color=self.colour
                    )
                    embed.add_field(name="Location", value=new['location'], inline=True)
                    embed.add_field(name="Description", value=new['description'], inline=True)
                    embed.add_field(name="Date", value=f"{new['date']}", inline=False)

                    channel = self.bot.get_channel(updates_channel)
                    await channel.send(embed=embed)

                    if new['delivered']:
                        await channel.send(f"Removed {entry['id']} ({entry['description']}) from the list")
                        

def setup_selenium() -> webdriver:
    Options = options.Options()
    Options.headless = True

    driver = webdriver.Firefox(options=Options, service=Service(GeckoDriverManager().install()))
    return driver


def setup(bot: commands.Bot):
    bot.add_cog(Acs(bot))