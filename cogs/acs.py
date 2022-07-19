import discord, asyncio
from discord.ext import commands, tasks
from json import dump
from os.path import relpath
from pyppeteer import launch
from dateutil import parser, tz


class Acs(commands.Cog, name="ACS"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.colour = 0xE42229
        self.tracking_url = "https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking3&generalCode="
        self.main_url = "https://www.acscourier.net/el/web/greece/track-and-trace?action=getTracking3&generalCode="
        self.logo = "https://i.imgur.com/Yk1WIrQ.jpg"
        self.tracking = [False, False]  # This is very ugly but I can't be bothered to improve it
        self.response_json = [None, None]
        self.processed_flag = [asyncio.Event(), asyncio.Event()]
        self.started = False
          

    async def init_browser(self):
        self.browser = await launch(executablePath='/usr/bin/google-chrome-stable', headless=True, args=[
            '--disable-gpu',
            '--no-sandbox',
            '--disable-extensions'
        ])
        
        await self.browser.newPage()
        self.pages = await self.browser.pages()

        for page in self.pages:
            await self.setup_page(page)

        if not self.started:
            self.reload_pages.start()
            self.update_ids.start()
            self.started = True
        
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

        embed.set_thumbnail(url=self.logo)
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
        using = 1 if self.tracking[0] else 0
        page = self.pages[using]
        self.tracking[using] = True
        
        async def process_response(res, id):
            nonlocal using
            if res.url == f"https://api.acscourier.net/api/parcels/search/{id}":
                try:
                    self.response_json[using] = await asyncio.gather(res.json())
                    self.processed_flag[using].set()
                except:
                    pass
        
        await page.click(".mat-form-field-flex")   # Selects input box
        await page.keyboard.sendCharacter(id)   # Types the id in it
        await page.click(".d-sm-inline-block") # Clicks the search button
        
        page.on('response', lambda res: asyncio.ensure_future(process_response(res, id)))
        
        await self.processed_flag[using].wait()
        self.processed_flag[using].clear()
        
        await page.click(".mat-focus-indicator")   # Clears input box and search results        
        self.tracking[using] = False
        
        package = self.response_json[using][0]["items"][0]
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
            date = parser.isoparse(last_status["controlPointDate"]).astimezone(tz=tz.gettz('Europe/Athens'))
            return (0, {
                "date": date.strftime("%d-%m-%Y, %H:%M"), 
                "description": last_status["description"].capitalize(), 
                "location": last_status["controlPoint"].capitalize(), 
                "delivered": delivered
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

        if not next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None):
            self.bot.guild_data[str(ctx.guild.id)]['acs'].append({"id": id, "description": description, "status": status})
            await ctx.send(f"Added {id} ({description}) to the list.")
            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send("Package already in list.\nIf you want to change its description use ?/acs edit")

    async def remove_id(self, ctx: commands.Context, id):
        package = next((i for i in self.bot.guild_data[str(ctx.guild.id)]['acs'] if i['id'] == id), None)
        if package:
            description = package['description']
            self.bot.guild_data[str(ctx.guild.id)]['acs'].remove(package)
            await ctx.send(f"Removed {id} ({description}) from the list")

            with open(relpath("data/guild_data.json"), "w") as file:
                dump(self.bot.guild_data, file, indent=4)
        else:
            await ctx.send(f"Package {id} is not in the list.")

    async def check_if_changed(self, guild, entry, old_status) -> tuple:
        (result, new) = await self.get_last_status(entry['id'])

        if result == 1:
            return (False, None)

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

    async def setup_page(self, page):
        while True:
            try:
                await page.goto(
                    "https://www.acscourier.net/el/myacs/anafores-apostolwn/anazitisi-apostolwn/",
                    waitUntil=["domcontentloaded", "networkidle0"]
                )
                break
            except Exception as e:
                self.bot.logger.error(f"Error while setting up tab: {e}")
                await asyncio.sleep(30)
            
        try:
            await page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
        except:
            pass

    @tasks.loop(minutes=2.0)
    async def update_ids(self):
        for guild in self.bot.guild_data:
            updates_channel = int(self.bot.guild_data[guild]['updates_channel'])
            if updates_channel == 0:
                continue
            for entry in self.bot.guild_data[guild]['acs']:
                while self.tracking[0] == self.tracking[1] == True:
                    await asyncio.sleep(1)
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

    @update_ids.before_loop
    async def before_update_ids(self):
        await asyncio.sleep(5)
    
    @tasks.loop(minutes=5.0)
    async def reload_pages(self):
        reloaded = [False, False]
        for i in range(len(self.pages)):
            if not self.tracking[i] and not reloaded[i]:
                self.tracking[i] = True
                await self.pages[i].close()
                self.pages[i] = await self.browser.newPage()
                await self.setup_page(self.pages[i])
                reloaded[i] = True
                self.tracking[i] = False
            else:
                await asyncio.sleep(1)
                
            if reloaded[0] == reloaded[1] == True:
                break
            

def setup(bot: commands.Bot):
    bot.add_cog(Acs(bot))
