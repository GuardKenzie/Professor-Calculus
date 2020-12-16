import discord
import sqlite3
import re
import json
from discord.ext import commands
import asyncio
import random
import sys
from datetime import datetime
import praw
import wolframalpha
import urllib.request
import io
from PIL import Image, ImageDraw, ImageFont
import dbl
import math
import pytz
import dateutil.parser
import pickle
from imgurpython import ImgurClient

# Mine
import bokasafn.breytugreinir as breytugreinir
import bokasafn.events as events
import bokasafn.helper as helper
import bokasafn.permissions as permissions
import bokasafn.salty as salty
import bokasafn.soundb as soundb
import bokasafn.reminders as reminders
import bokasafn.dags as dags
import bokasafn.emojis as foodEmojis
import bokasafn.notice as noticelib

# Bot key
with open(sys.argv[1], "r") as keyFile:
    key = keyFile.read().strip()

# Events dict. Index = guild hash
eventsDict = {}

# Soundboard dict. Index = guild hash
soundBoardDict = {}

# Permissions dict. Index = guild hash
permissionsDict = {}

# Command prefix
prefixes = ["p? ", "p?"]
prefix = "p? "

# Load messages
with open("res/messages.json", "r") as f:
    infoMessages = json.loads(f.read())

# Activity
activity = discord.Game(infoMessages["activity"])

# Intent
intent = discord.Intents.default()
intent.members = True

# initiate bot
professor = commands.Bot(case_insensitive=True,
                         command_prefix=prefixes,
                         activity=activity,
                         intents=intent)

professor.remove_command("help")

# Emotes
leftarrow = "\u2B05\uFE0F"
rightarrow = "\u27A1\uFE0F"

party = "\U0001F389"
calculator = "\U0001F5A9"

# Color
accent_colour = discord.Colour(int("688F56", 16))

# Salt initialisation
saltWraper = salty.saltClass(database="db/salt.db", insults="res/insults.txt")

everyone = "@everyone"

# event check loop
eventCheckerLoop = None

# Activity loop
activityLoop = None

# Reminders
reminderLoop = None
reminderWrapper = reminders.Reminders(database="db/reminders.db")

# Reddit
with open("keys/reddit", "r") as f:
    r_id = f.readline().strip()
    r_secret = f.readline().strip()
    r_ua = f.readline().strip()

    reddit = praw.Reddit(client_id=r_id,
                         client_secret=r_secret,
                         user_agent=r_ua)

# Wolfram
with open("keys/wolfram", "r") as f:
    wa_app_id = f.readline().strip()
    wolf = wolframalpha.Client(wa_app_id)

# Imgur
with open("keys/imgur.json", "r") as f:
    aux = json.loads(f.read())
    imgur = ImgurClient(aux["clientid"], aux["secret"])


# dummy parameter for discord.ext.commands.errors.MissingRequiredArgumentError
class dummyparam:
    def __init__(self, name):
        self.name = name


# Server count for top.gg
class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("keys/topgg", "r") as f:
            self.token = f.read().strip()

        self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=True)

    async def on_guild_post():
        print("\nEVENT:\nServer count posted successfully")


# ==========================================
# Functions
# ==========================================


@professor.check
async def permissioncheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        check = permissionsDict[hash(ctx.guild)].hasPermission(ctx)
        if not check:
            await ctx.author.send(content="You do not have permission to execute the command `{}`.".format(ctx.message.content))
    else:
        return True

    return check


def delperm(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        return ctx.channel.permissions_for(ctx.guild.me).manage_messages
    else:
        return False


async def notEventChannelCheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        if hash(ctx.guild) in eventsDict.keys():
            if ctx.channel.id != eventsDict[hash(ctx.guild)].getMyChannelId("events"):
                return True
            else:
                await ctx.author.send(content="You cannot use this command in the events channel.")
                return False
        else:
            await ctx.author.send(content="You cannot use this command here.")
            return False
    else:
        return True


async def eventChannelCheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel) and hash(ctx.guild) in eventsDict.keys():
        if eventsDict[hash(ctx.guild)].channel is None:
            await ctx.author.send(content="I have not yet been assigned an `events` channel. Please assign me to an `events` channel with the `configure channel events` command.")
            return
        if ctx.channel.id == eventsDict[hash(ctx.guild)].getMyChannelId("events"):
            if not delperm(ctx):
                await ctx.author.send(content="I need permission to manage messages in my events channel.")
                return False
            return True
        else:
            await ctx.author.send(content="You need to be in the events channel to do that.")
    else:
        await ctx.author.send(content="This command can only be used in the events channel.")
        return False


def dictFromMembersName(members):
    # Generate dictionary with key: member id and value: display name
    out = {}
    for member in members:
        out[member.id] = member.display_name
    return out


def dictFromMembers(members):
    # Generate dictionary with key: member id and value: member
    out = {}
    for member in members:
        out[member.id] = member
    return out


async def updatePinned(myChannel, guild):
    if myChannel is None:
        return

    # Updates the pinned event list
    guildHash = hash(guild)
    guildMembers = dictFromMembersName(guild.members)
    update = eventsDict[guildHash].generateEventsMessage(guildMembers)

    mylog = eventsDict[guildHash].getLog(dateform="%a. %H:%M")
    mylog = ["`{}`\t{}".format(u, v) for u, v in mylog][-3:]

    if mylog:
        mylog[0] = ">>> " + mylog[0]
    else:
        mylog = [">>> The log is empty"]

    # Find the message
    myMessageId = eventsDict[guildHash].myMessageId
    myLogMessageId = eventsDict[guildHash].myLogMessageId

    # Get my nick
    nick = guild.me.display_name

    # Calculate timezone offset from UTC
    utcoffset = eventsDict[guildHash].timezone.utcoffset(datetime.utcnow()).total_seconds() / 60 / 60
    utcoffset = " (UTC+{})".format(int(utcoffset)) if utcoffset >= 0 else " (UTC-{})".format(abs(int(utcoffset)))

    if str(eventsDict[guildHash].timezone) == "UTC":
        utcoffset = ""

    # Update the message if it exists, else post new one
    try:
        myMessage = await myChannel.fetch_message(myMessageId)
        await myMessage.edit(content="**Notice:** All times are in `{}{}` time.".format(str(eventsDict[guildHash].timezone), utcoffset), embed=update)
        myLogMessage = await myChannel.fetch_message(myLogMessageId)
        await myLogMessage.edit(content="\n".join(mylog))
        await myLogMessage.clear_reactions()

    except discord.errors.Forbidden:
        await guild.owner.send("Something went wrong with my event channel in f{guild.name}. Please configure a new one to be able to use event features again.")
        eventsDict[guildHash].setMyChannelId(0, "events")
        return

    except (discord.errors.HTTPException, discord.errors.NotFound):
        await myChannel.purge()
        helloMessage = await myChannel.send(content=infoMessages["helloMessage"].format(nick, prefix))
        myMessage = await myChannel.send(content="**Notice:** All times are in `{}{}` time".format(str(eventsDict[guildHash].timezone), utcoffset), embed=update)
        myLogMessage = await myChannel.send(content="\n".join(mylog))
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)

        eventsDict[guildHash].setMyMessage(myMessage, "normal")
        eventsDict[guildHash].setMyMessage(myLogMessage, "log")

        await myMessage.pin()
        await asyncio.sleep(2)
        await helloMessage.pin()
        await asyncio.sleep(2)
        await myLogMessage.pin()


async def friendly_notification(e, number):
    # Friendly reminder for recurring events
    eventName = e["event"].name
    eventDesc = e["event"].description
    weekday = e["date"]

    # Find my friendly channel
    channelId = e["channelId"]
    guild = e["guild"]

    # everyone = guild.me.roles[0].mention

    friendlyChannel = guild.get_channel(channelId)

    msgContent = "Today is "
    if number > 0:
        msgContent += " also "

    msgContent += "**{} {}**. \n> {} \n Remember to sign up in the events channel!".format(eventName, weekday, eventDesc)

    await friendlyChannel.send(content=msgContent)


async def event_notification(e):
    # Parse event
    event = e["event"]
    channel = e["channel"]
    color = e["color"]
    now = e["now"]

    # everyone = channel.guild.me.roles[0].mention

    guildMembers = dictFromMembers(channel.guild.members)
    attendants = []

    # Create event role
    try:
        eventRole = await channel.guild.create_role(name="event", mentionable=True)
        mention = eventRole.mention
    except discord.errors.Forbidden:
        mention = ""
        eventRole = 0

    # Get names of attendants and give them the event role
    for member in event.people:
        attendants.append(str(event.rolesdict[member]) + " " + str(guildMembers[member].display_name))

        if eventRole != 0:
            await guildMembers[member].add_roles(eventRole)

    if len(attendants) == 0:
        attendants = ["Nobody :("]
    if event.description == "":
        event.description = "No description yet."

    if now:
        messageTitle = mention + " Event starting now!"
        deleteTime = 600
    else:
        messageTitle = mention + " Event starting in an hour!"
        deleteTime = 3600

    # Generate message
    if (event.limit != 0):
        limitstr = "({}/{})".format(len(event.people), event.limit)
    else:
        limitstr = "({})".format(str(len(event.people)))
    message = discord.Embed(title=event.name, description=event.description, color=color)
    message.add_field(name="When?", value=event.printableDate())
    message.add_field(name="Party " + limitstr, value="\n".join(attendants), inline=False)
    await channel.send(content=messageTitle, embed=message, delete_after=deleteTime)

    if eventRole != 0:
        await eventRole.delete()


async def notification_loop():
    # Wait until bot is ready
    await professor.wait_until_ready()
    while True:
        # Check every 60s
        await asyncio.sleep(60)
        for guild in professor.guilds:

            if eventsDict[hash(guild)].channel is None:
                continue

            # Check every guild for notifications
            eventOut = eventsDict[hash(guild)].checkIfNotification()

            i = 0
            for e in eventOut:
                # If there is a notification, send it and update events list
                try:
                    if e["friendly"]:
                        await friendly_notification(e, i)
                        i += 1
                    else:
                        asyncio.create_task(updatePinned(eventsDict[hash(guild)].channel, guild))
                        await event_notification(e)
                except:
                    continue


async def activity_changer():
    await professor.wait_until_ready()
    professor.add_cog(TopGG(professor))
    currentActivity = 1
    while True:
        await asyncio.sleep(30)
        if currentActivity == 0:
            activity = discord.Game(infoMessages["activity"])
            currentActivity = 1
        else:
            activity = discord.Game("p? help")
            currentActivity = 0
        await professor.change_presence(activity=activity)


async def reminder_checker():
    await professor.wait_until_ready()
    while True:
        for reminder in reminderWrapper.checkIfRemind():
            user = professor.get_user(reminder["id"])

            await user.send(embed=reminder["embed"])
        await asyncio.sleep(10)

# ==========================================
# Bot events
# ==========================================


@professor.event
async def on_ready():
    global eventCheckerLoop
    global activityLoop
    global reminderLoop
    print("User:\t\t\t{}".format(professor.user))
    # Set activity
    print("Activity:\t\t{}".format(activity))
    print()

    # Initiate Events class for each guild
    for guild in professor.guilds:
        guildHash = hash(guild)
        print("Guild:\t\t\t{}".format(guild.name))

        eventsDict[guildHash] = events.Events(guildHash, database="db/events.db")
        soundBoardDict[guildHash] = soundb.SoundBoard(guildHash, database="db/sounds.db")

        # Find my channel
        myChannelId = eventsDict[guildHash].getMyChannelId("events")
        if myChannelId != 0:
            myChannel = guild.get_channel(myChannelId)
        else:
            myChannel = None

        def purgecheck(m):
            return not m.pinned or m.content == infoMessages["new_update"]

        # If I have a channel, purge and post event list
        if myChannel:
            eventsDict[guildHash].channel = myChannel
            asyncio.create_task(myChannel.purge(check=purgecheck))
            asyncio.create_task(updatePinned(myChannel, guild))

        # Initiate permissions
        permissionsDict[hash(guild)] = permissions.Permissions(hash(guild), database="db/permissions.db")

        print()
    if eventCheckerLoop not in asyncio.all_tasks():
        print("Starting event checking loop")
        eventCheckerLoop = professor.loop.create_task(notification_loop())

    if activityLoop not in asyncio.all_tasks():
        print("Starting activity loop")
        activityLoop = professor.loop.create_task(activity_changer())

    if reminderLoop not in asyncio.all_tasks():
        print("Starting reminders")
        reminderLoop = professor.loop.create_task(reminder_checker())


@professor.event
async def on_command_completion(ctx):
    # List of commands for events

    if ctx.guild:
        eventCommands = ["timezone", "attend", "leave", "schedule", "remove", "update", "kick", "config"]

        guildHash = hash(ctx.guild)

        # Update pinned list if command is for event
        if ctx.command.name in eventCommands and guildHash in eventsDict.keys() and eventsDict[guildHash].attending == 0:
            asyncio.create_task(updatePinned(eventsDict[guildHash].channel, ctx.guild))

    await asyncio.sleep(2)


@professor.event
async def on_message(message):
    # Process command and then delete the message if it wasn't a command in events channel
    await professor.process_commands(message)

    # Check if we are in dm
    guildMessage = isinstance(message.channel, discord.abc.GuildChannel)
    if hash(message.guild) in eventsDict.keys():
        if guildMessage \
                and message.channel == eventsDict[hash(message.guild)].channel \
                and (message.author != professor.user or str(message.type) == "MessageType.pins_add") \
                and eventsDict[hash(message.guild)].scheduling == 0:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass
            except discord.errors.Forbidden:
                pass


@professor.event
async def on_raw_reaction_add(payload):
    # Process pages
    guild = professor.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)

    myMessageId = eventsDict[hash(guild)].myMessageId

    # If react to me and was someone else
    if payload.message_id == myMessageId and payload.member != professor.user:
        try:
            message = await channel.fetch_message(payload.message_id)
            # Page down if left arrow
            if payload.emoji.name == leftarrow:
                if eventsDict[hash(guild)].page > 1:
                    eventsDict[hash(guild)].page -= 1
                await updatePinned(eventsDict[hash(guild)].channel, guild)
                await message.remove_reaction(payload.emoji, payload.member)

            # Page up if rightarrow
            elif payload.emoji.name == rightarrow:
                eventsDict[hash(guild)].page += 1
                await updatePinned(eventsDict[hash(guild)].channel, guild)
                await message.remove_reaction(payload.emoji, payload.member)
        except discord.errors.Forbidden:
            return


@professor.event
async def on_guild_join(guild):
    # Print setup message in first text channel we can
    eventsDict[hash(guild)] = events.Events(hash(guild), None, database="db/events.db")
    soundBoardDict[hash(guild)] = soundb.SoundBoard(hash(guild), database="db/sounds.db")
    permissionsDict[hash(guild)] = permissions.Permissions(hash(guild), database="db/permissions.db")
    for i in guild.text_channels:
        try:
            await i.send(content="Type `" + prefix + "setup` to get started")
            break
        except discord.errors.Forbidden:
            pass


@professor.event
async def on_command_error(ctx, error):

    print("COMMAND ERROR")
    print("Command:\t{}".format(ctx.message.content))
    print("Error:\t\t{}".format(error))
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.author.send(content="There was an error executing your command `{}`. Incorrect number of arguments passed.".format(ctx.message.content))
    elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await ctx.author.send(content="The command `{}` is unknown.".format(ctx.message.content))
    elif isinstance(error, discord.ext.commands.errors.CheckFailure):
        pass
    else:
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            await ctx.author.send(content="There was an unknown error executing your command `{}`.".format(ctx.message.content))
        else:
            await ctx.author.send(content="There was an unknown error executing your command `{}`. Perhaps you should not be executing it in a dm channel.".format(ctx.message.content))


# ==========================================
# Bot commands
# ==========================================


# --- Setup and stuff ---

@professor.command()
async def setup(ctx):
    # Create events channel in professor category
    # Initiate Events class for guild

    # Delete message
    try:
        await ctx.message.delete()
    except discord.errors.Forbidden:
        pass

    # Get nickname
    nick = ctx.guild.me.display_name

    # Create category and channel
    try:
        category = await ctx.guild.create_category("Events")
        channel = await ctx.guild.create_text_channel("events", category=category)

        await channel.send(content=infoMessages["helloMessage"].format(nick, prefix))

    except discord.errors.Forbidden:
        await ctx.author.send(content=infoMessages["cannotCreateEventsChannel"].format(prefix))

    # Let owner know about configuring role
    await ctx.author.send(content=infoMessages["schedulerMessage"].format(prefix))

    # Initiate Events class
    try:
        eventsDict[hash(ctx.guild)].channel = channel
        eventsDict[hash(ctx.guild)].myMessage = None
        eventsDict[hash(ctx.guild)].setMyChannelId(channel.id, "events")
    except NameError:
        return

    # Update pinned
    await updatePinned(channel, ctx.guild)


# --- Configuration ---

@professor.group(invoke_without_command=True)
async def configureold(ctx):
    if ctx.invoked_subcommand is None:
        # Give an overview of roles with permissions
        embed = discord.Embed(title="Permissions overveiw for {}".format(ctx.guild.name), color=accent_colour)

        # Check all the roles
        for role in ctx.guild.roles:
            # Get permissions for role
            perms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)
            perms.sort()

            # Check if there are any permissions
            if perms == []:
                continue
            else:
                out = "\n".join(map(permissions.resolvePermission, perms))

            # Add field for role
            embed.add_field(name=role.name, value=out)

        await ctx.author.send(embed=embed)

    if delperm(ctx):
        await ctx.message.delete()


@professor.group(invoke_without_command=True, aliases=["config", "conf"])
async def configure(ctx):
    # Todo:
    # Comments

    if not delperm(ctx):
        await ctx.channel.send("I do not have permission to manage messages in this channel so the interactive configuration will not work properly. Please use the other configuration commands found under \"Configuration\" in `p? help`.")
        return

    events_channel = eventsDict[hash(ctx.guild)].channel
    friendly_channel = ctx.guild.get_channel(eventsDict[hash(ctx.guild)].getMyChannelId("friendly"))

    events_channel_mention = None if events_channel is None else events_channel.mention
    friendly_channel_mention = None if friendly_channel is None else friendly_channel.mention

    timezone = eventsDict[hash(ctx.guild)].timezone

    TextChannelConverter = discord.ext.commands.TextChannelConverter()
    RoleConverter = discord.ext.commands.RoleConverter()

    emojis = foodEmojis.foodEmojis("res/foodemojis.txt")
    emojis_avail = emojis.getEmojis(4)

    async def editChannel(msg, channelType):
        await msg.clear_reactions()
        ghost = "\U0001F47B"

        embed = discord.Embed(colour=accent_colour, title=f"Please select an option for configuring the {channelType} channel", description=f"{emojis.checkmark} Change the channel\n\n{ghost} Unset the channel\n\n{emojis.cancel} Cancel")
        await msg.edit(embed=embed)

        await msg.add_reaction(emojis.checkmark)
        await msg.add_reaction(ghost)
        await msg.add_reaction(emojis.cancel)

        try:
            r, _ = await professor.wait_for("reaction_add", check=lambda r, u: u == ctx.author and r.emoji in [ghost, emojis.checkmark, emojis.cancel])
        except asyncio.TimeoutError:
            return -1

        if r.emoji == emojis.cancel:
            return -1

        if r.emoji == ghost:
            eventsDict[hash(ctx.guild)].unsetMyChannelId(channelType)
            return 1

        await msg.clear_reactions()

        if channelType == "events":
            embed = discord.Embed(colour=accent_colour, title="Editing events channel", description=f"Currently configured to: {events_channel_mention}\nPlease specify the new events channel and then press {emojis.checkmark} to confirm.\n**WARNING: THIS WILL DELETE ALL MESSAGES IN THAT CHANNEL.**\nType `back` to go back to the main menu.")

            await msg.edit(embed=embed)

            def check_channel(m):
                return m.author == ctx.author

            def check_confirm(r, u):
                return r.emoji in [emojis.checkmark, emojis.cancel] and u == ctx.author

            try:
                while True:
                    rep = await professor.wait_for("message", check=check_channel)
                    try:
                        if rep.content.lower() == "back":
                            if delperm(ctx):
                                await rep.delete()

                            raise asyncio.TimeoutError

                        channel = await TextChannelConverter.convert(ctx, rep.content)
                        if delperm(ctx):
                            await rep.delete()

                        break
                    except discord.ext.commands.CommandError:
                        pass

                embed.add_field(name="New channel", value=channel.mention)
                await msg.edit(embed=embed)

                await msg.add_reaction(emojis.checkmark)
                await msg.add_reaction(emojis.cancel)

                r, _ = await professor.wait_for("reaction_add", check=check_confirm)
                if r.emoji == emojis.checkmark:
                    eventsDict[hash(ctx.guild)].channel = channel
                    eventsDict[hash(ctx.guild)].myMessage = None
                    eventsDict[hash(ctx.guild)].setMyChannelId(channel.id, channelType)
                    asyncio.create_task(updatePinned(channel, ctx.guild))
                    return 1
                else:
                    return 1

            except asyncio.TimeoutError:
                return -1

        elif channelType == "friendly":
            embed = discord.Embed(colour=accent_colour, title="Editing the friendly channel", description=f"Currently configured to: {friendly_channel_mention}\nPlease specify the new friendly channel.\nType `back` to go back to the main menu.")

            await msg.edit(embed=embed)

            def check_channel(m):
                return m.author == ctx.author

            try:
                while True:
                    rep = await professor.wait_for("message", check=check_channel)
                    try:
                        if rep.content.lower() == "back":
                            if delperm(ctx):
                                await rep.delete()

                            raise asyncio.TimeoutError

                        channel = await TextChannelConverter.convert(ctx, rep.content)
                        if delperm(ctx):
                            await rep.delete()

                        break
                    except discord.ext.commands.CommandError:
                        pass

                eventsDict[hash(ctx.guild)].setMyChannelId(channel.id, channelType)

                return 1

            except asyncio.TimeoutError:
                return -1

    async def editTz(msg):
        await msg.clear_reactions()

        tzdict = {"Other": []}
        regions = set()

        for entry in pytz.all_timezones:
            entry = entry.split("/")
            if len(entry) == 1:
                tzdict["Other"].append("/".join(entry))
            elif entry[0] in regions:
                tzdict[entry[0]].append("/".join(entry[1:]))
            else:
                tzdict[entry[0]] = []
                regions.add(entry[0])

        regions = list(tzdict.keys())
        regionsStr = ""

        i = 1
        for r in regions:
            regionsStr += "{}. {}\n".format(i, r)
            i += 1

        embed = discord.Embed(title="Please select a region by replying with the corresponding number.", description=regionsStr, colour=accent_colour)
        await msg.edit(embed=embed)

        def checkRegion(message):
            try:
                return int(message.content) <= len(regions) and message.author == ctx.message.author
            except ValueError:
                return False

        try:
            regionMsg = await professor.wait_for("message", check=checkRegion, timeout=120)
        except asyncio.TimeoutError:
            return -1

        regionIndex = int(regionMsg.content) - 1

        if delperm(ctx):
            await regionMsg.delete()

        zones = tzdict[regions[regionIndex]]

        def checkZone(message):
            if message.content.lower() in ["back", "next"]:
                return message.author == ctx.message.author
            else:
                try:
                    return int(message.content) <= len(zones) and message.author == ctx.message.author
                except ValueError:
                    return False

        done = False
        page = 0
        pages = math.ceil(len(zones) / 20)
        while not done:
            zonesStr = ""
            i = 20 * (page) + 1
            snid = zones[20 * (page):20 * (page + 1)] if page < pages else zones[20 * (page):]
            for z in snid:
                zonesStr += "{}. {}\n".format(i, z)
                i += 1
            embed = discord.Embed(title="Time zone (Page {}/{})\nPlease select a region by replying with the corresponding number. Reply with `next` for the next page.\nReply with `back` for the previous page.".format(page + 1, pages),
                                  description=zonesStr,
                                  colour=accent_colour)

            await msg.edit(embed=embed)

            try:
                zoneMsg = await professor.wait_for("message", check=checkZone, timeout=120)
            except asyncio.TimeoutError:
                return -1

            if zoneMsg.content == "next":
                page = (page + 1) % pages
            elif zoneMsg.content == "back":
                page = (page - 1) % pages
            else:
                done = True
                zoneIndex = int(zoneMsg.content) - 1

            if delperm(ctx):
                await zoneMsg.delete()

        if regions[regionIndex] != "Other":
            timezone = "{}/{}".format(regions[regionIndex], zones[zoneIndex])
        else:
            timezone = zones[zoneIndex]

        eventsDict[hash(ctx.guild)].setTimezone(timezone)

    async def editRoles(msg):
        await msg.clear_reactions()
        embed = discord.Embed(title="Configuring role permissions",
                              description="Please mention the role you want to configure.\nType `back` to go back to the main menu.",
                              colour=accent_colour)
        await msg.edit(embed=embed)

        try:
            while True:
                rep = await professor.wait_for("message", check=lambda m: m.author == ctx.author)
                if rep.content.lower() == "back":
                    if delperm(ctx):
                        await rep.delete()
                    raise asyncio.TimeoutError
                try:
                    role = await RoleConverter.convert(ctx, rep.content)
                    break
                except discord.ext.commands.CommandError:
                    pass

            if delperm(ctx):
                await rep.delete()
        except asyncio.TimeoutError:
            return -1

        cross = "\u274C"
        # Permissions that can be set
        availablePerms = permissions.availablePerms
        rolePerms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)

        permEmojis = foodEmojis.foodEmojis("res/foodemojis.txt")
        perm_emojis_avail = permEmojis.getEmojis(len(availablePerms))

        done = False

        initial = True

        message = msg

        # Continue until done

        while not done:
            # Initialize
            embed = discord.Embed(title="Permissions for {}".format(role.name), color=accent_colour)
            eventsPermissions = {}
            configurePermissions = {}
            soundboardPermissions = {}

            # Categorize the permissions and check their values
            for p in permissions.permissionResolver.values():
                commandName = permissions.resolvePermission(p).split()[-1]
                if p[0] == "e" and p in availablePerms:
                    eventsPermissions[commandName] = p in rolePerms
                elif p[0] == "s" and p in availablePerms:
                    soundboardPermissions[commandName] = p in rolePerms
                elif p[0] == "c" and p in availablePerms:
                    configurePermissions[commandName] = p in rolePerms

            # Function to generate the permission list for each category
            def genstr(d, currentemoji):
                out = ""
                for i in d.items():
                    out += perm_emojis_avail[currentemoji] + " " + str(i[0]) + ": " + str(i[1]) + "\n"
                    currentemoji += 1

                return out

            currentemoji = 0

            # Add the fields
            embed.add_field(name="Events", value=genstr(eventsPermissions, currentemoji), inline=False)
            currentemoji += len(eventsPermissions)

            embed.add_field(name="Soundboard", value=genstr(soundboardPermissions, currentemoji), inline=False)
            currentemoji += len(soundboardPermissions)

            embed.add_field(name="Configure", value=genstr(configurePermissions, currentemoji), inline=False)
            currentemoji += len(configurePermissions)

            await message.edit(content="", embed=embed)

            # Add emojis if this is the first loop
            if initial:
                for k in range(currentemoji):
                    await message.add_reaction(perm_emojis_avail[k])

                await message.add_reaction(cross)
                initial = False

            # Check function for reaction
            def check(payload):
                i = permEmojis.getIndex(payload.emoji.name)
                emojiok = i >= 0 or i == -2
                memberok = payload.member == ctx.author
                messageok = payload.message_id == message.id

                if emojiok and memberok and messageok:
                    return True
                else:
                    return False

            try:
                payload = await professor.wait_for("raw_reaction_add", check=check, timeout=300)
            except asyncio.TimeoutError:
                await message.delete()
                return

            # Break if done
            if payload.emoji.name == cross:
                done = True
                break
            else:
                # Try to remove the reaction
                if delperm(ctx):
                    await message.remove_reaction(payload.emoji, ctx.author)

                # Add or remove the permission selected from the permission array
                p = availablePerms[permEmojis.getIndex(payload.emoji.name)]
                if p in rolePerms:
                    del rolePerms[rolePerms.index(p)]
                else:
                    rolePerms.append(p)

        # Update the permissions
        permissionsDict[hash(ctx.guild)].setPermissions(role.id, rolePerms)

    embed = discord.Embed(title=f"Configuration for {ctx.guild.name}",
                          description="React with the relevant emoji to change a setting.",
                          colour=accent_colour)

    roles = ""

    for role in ctx.guild.roles:
        # Get permissions for role
        perms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)
        perms.sort()

        # Check if there are any permissions
        if perms == []:
            continue
        else:
            out = ", ".join(map(permissions.resolvePermission, perms))

        # Add field for role
        roles += f"{role.mention}: {out}\n\n"

    if roles == "":
        roles = "None"

    embed.add_field(name=f"{emojis_avail[0]} Events channel", value=events_channel_mention, inline=False)
    embed.add_field(name=f"{emojis_avail[1]} Friendly channel", value=friendly_channel_mention, inline=False)
    embed.add_field(name=f"{emojis_avail[2]} Guild time zone", value=str(timezone), inline=False)
    embed.add_field(name=f"{emojis_avail[3]} Role permissions", value=roles, inline=False)

    msg = await ctx.channel.send(embed=embed)

    for e in emojis_avail:
        await msg.add_reaction(e)

    await msg.add_reaction(emojis.cancel)

    def check(r, u):
        if u != ctx.author:
            return False

        i = emojis.getIndex(r.emoji)
        if i >= 0:
            return True
        elif i == -2:
            raise asyncio.TimeoutError

    while True:
        try:
            r, _ = await professor.wait_for("reaction_add", check=check, timeout=300)
            cmd = emojis.getIndex(r.emoji)

            # Events channel
            if cmd == 0:
                await editChannel(msg, "events")

            # Friendly channel
            elif cmd == 1:
                await editChannel(msg, "friendly")

            # Timezone
            elif cmd == 2:
                await editTz(msg)

            elif cmd == 3:
                await editRoles(msg)

            await msg.clear_reactions()

            events_channel = eventsDict[hash(ctx.guild)].channel
            friendly_channel = ctx.guild.get_channel(eventsDict[hash(ctx.guild)].getMyChannelId("friendly"))
            timezone = eventsDict[hash(ctx.guild)].timezone

            events_channel_mention = None if events_channel is None else events_channel.mention
            friendly_channel_mention = None if friendly_channel is None else friendly_channel.mention

            roles = ""

            for role in ctx.guild.roles:
                # Get permissions for role
                perms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)
                perms.sort()

                # Check if there are any permissions
                if perms == []:
                    continue
                else:
                    out = ", ".join(map(permissions.resolvePermission, perms))

                # Add field for role
                roles += f"{role.mention}: {out}\n\n"

            if roles == "":
                roles = "None"

            embed.set_field_at(0, name=f"{emojis_avail[0]} Events channel", value=events_channel_mention, inline=False)
            embed.set_field_at(1, name=f"{emojis_avail[1]} Friendly channel", value=friendly_channel_mention, inline=False)
            embed.set_field_at(2, name=f"{emojis_avail[2]} Guild time zone", value=timezone, inline=False)
            embed.set_field_at(3, name=f"{emojis_avail[3]} Role permissions", value=roles, inline=False)

            await msg.edit(embed=embed)

            for e in emojis_avail:
                await msg.add_reaction(e)

            await msg.add_reaction(emojis.cancel)

        except asyncio.TimeoutError:
            await msg.delete()
            return

    if delperm(ctx):
        await ctx.message.delete()


@configure.command(checks=[notEventChannelCheck])
async def channel(ctx, channelType):
    if channelType not in ["events", "friendly"]:
        await ctx.author.send(content="{} is not a valid channel type.".format(channelType))
        return

    def check(m):
        return (m.content == "yes" or m.content == "no") and m.channel == ctx.channel and m.author == ctx.author

    if (channelType == "events"):
        if not delperm(ctx):
            await ctx.author.send(content=infoMessages["cannotManageMessages"])
            return

        confirmMsg = await ctx.channel.send(content=infoMessages["confirmEventsChannel"])
        confirmReply = await professor.wait_for("message", check=check)
        confirm = confirmReply.content == "yes"

        if confirm:
            eventsDict[hash(ctx.guild)].channel = ctx.channel
            eventsDict[hash(ctx.guild)].myMessage = None
            eventsDict[hash(ctx.guild)].setMyChannelId(ctx.channel.id, channelType)
            await updatePinned(ctx.channel, ctx.guild)
        else:
            await confirmMsg.delete()
            await confirmReply.delete()
    else:
        await ctx.channel.send(content="Channel registered as {}".format(channelType), delete_after=20)
        eventsDict[hash(ctx.guild)].setMyChannelId(ctx.channel.id, channelType)

    try:
        await ctx.message.delete()
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


@configure.command()
async def role(ctx, role: discord.Role):
    cross = "\u274C"
    # Permissions that can be set
    availablePerms = ["es", "er", "eu", "ek", "sa", "sr", "cc", "cr", "ct", "no"]
    rolePerms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)

    with open("res/foodemojis.txt", "r") as f:
        emojis_avail = f.read().splitlines()
        random.shuffle(emojis_avail)

    done = False

    initial = True

    message = await ctx.channel.send(content="-")

    # Continue until done

    while not done:
        # Initialize
        embed = discord.Embed(title="Permissions for {}".format(role.name), color=accent_colour)
        eventsPermissions = {}
        configurePermissions = {}
        soundboardPermissions = {}
        miscPermissions = {}

        # Categorize the permissions and check their values
        for p in permissions.permissionResolver.values():
            commandName = permissions.resolvePermission(p).split()[-1]
            if p[0] == "e":
                eventsPermissions[commandName] = p in rolePerms
            elif p[0] == "s":
                soundboardPermissions[commandName] = p in rolePerms
            elif p[0] == "c":
                configurePermissions[commandName] = p in rolePerms
            elif p[0] == "n":
                miscPermissions[commandName] = p in rolePerms

        # Function to generate the permission list for each category
        def genstr(d, currentemoji):
            out = ""
            for i in d.items():
                out += emojis_avail[currentemoji] + " " + str(i[0]) + ": " + str(i[1]) + "\n"
                currentemoji += 1

            return out

        currentemoji = 0

        # Add the fields
        embed.add_field(name="Events", value=genstr(eventsPermissions, currentemoji), inline=False)
        currentemoji += len(eventsPermissions)

        embed.add_field(name="Soundboard", value=genstr(soundboardPermissions, currentemoji), inline=False)
        currentemoji += len(soundboardPermissions)

        embed.add_field(name="Configure", value=genstr(configurePermissions, currentemoji), inline=False)
        currentemoji += len(configurePermissions)

        embed.add_field(name="Misc", value=genstr(miscPermissions, currentemoji), inline=False)
        currentemoji += len(miscPermissions)

        await message.edit(content="", embed=embed)

        # Add emojis if this is the first loop
        if initial:
            for k in range(currentemoji):
                await message.add_reaction(emojis_avail[k])

            await message.add_reaction(cross)
            initial = False

        # Check function for reaction
        def check(payload):
            emojiok = payload.emoji.name in (emojis_avail[:currentemoji] + [cross])
            memberok = payload.member == ctx.author
            messageok = payload.message_id == message.id

            if emojiok and memberok and messageok:
                return True
            else:
                return False

        try:
            payload = await professor.wait_for("raw_reaction_add", check=check, timeout=300)
        except asyncio.TimeoutError:
            await message.delete()
            return

        # Break if done
        if payload.emoji.name == cross:
            done = True
            break
        else:
            # Try to remove the reaction
            if delperm(ctx):
                await message.remove_reaction(payload.emoji, ctx.author)

            # Add or remove the permission selected from the permission array
            p = availablePerms[emojis_avail.index(payload.emoji.name)]
            if p in rolePerms:
                del rolePerms[rolePerms.index(p)]
            else:
                rolePerms.append(p)

    # Update the permissions
    permissionsDict[hash(ctx.guild)].setPermissions(role.id, rolePerms)
    await message.delete()


@configure.command()
async def timezone(ctx):
    tzdict = {"Other": []}
    regions = set()

    for entry in pytz.all_timezones:
        entry = entry.split("/")
        if len(entry) == 1:
            tzdict["Other"].append("/".join(entry))
        elif entry[0] in regions:
            tzdict[entry[0]].append("/".join(entry[1:]))
        else:
            tzdict[entry[0]] = []
            regions.add(entry[0])

    regions = list(tzdict.keys())
    regionsStr = ""

    i = 1
    for r in regions:
        regionsStr += "{}. {}\n".format(i, r)
        i += 1

    embed = discord.Embed(title="Regions", description=regionsStr, colour=accent_colour)
    msg = await ctx.channel.send(content="Please select a region by replying with the corresponding number.", embed=embed)

    def checkRegion(message):
        try:
            return int(message.content) <= len(regions) and message.author == ctx.message.author
        except ValueError:
            return False

    try:
        regionMsg = await professor.wait_for("message", check=checkRegion, timeout=120)
    except asyncio.TimeoutError:
        await msg.delete()
        return

    regionIndex = int(regionMsg.content) - 1

    if delperm(ctx):
        await regionMsg.delete()

    zones = tzdict[regions[regionIndex]]

    def checkZone(message):
        if message.content.lower() in ["back", "next"]:
            return message.author == ctx.message.author
        else:
            try:
                return int(message.content) <= len(zones) and message.author == ctx.message.author
            except ValueError:
                return False

    done = False
    page = 0
    pages = math.ceil(len(zones) / 20)
    while not done:
        zonesStr = ""
        i = 20 * (page) + 1
        snid = zones[20 * (page):20 * (page + 1)] if page < pages else zones[20 * (page):]
        for z in snid:
            zonesStr += "{}. {}\n".format(i, z)
            i += 1
        embed = discord.Embed(title="Time zone (Page {}/{})".format(page + 1, pages), description=zonesStr, colour=accent_colour)
        await msg.edit(content="Please select a region by replying with the corresponding number.\nReply with `next` for the next page.\nReply with `back` for the previous page.", embed=embed)

        try:
            zoneMsg = await professor.wait_for("message", check=checkZone, timeout=120)
        except asyncio.TimeoutError:
            await msg.delete()
            return

        if zoneMsg.content == "next":
            page = (page + 1) % pages
        elif zoneMsg.content == "back":
            page = (page - 1) % pages
        else:
            done = True
            zoneIndex = int(zoneMsg.content) - 1
        if delperm(ctx):
            await zoneMsg.delete()

    if regions[regionIndex] != "Other":
        timezone = "{}/{}".format(regions[regionIndex], zones[zoneIndex])
    else:
        timezone = zones[zoneIndex]

    await msg.delete()

    eventsDict[hash(ctx.guild)].setTimezone(timezone)
    await ctx.channel.send("Time zone set to `{}`".format(timezone), delete_after=60)

    # eventsDict[hash(ctx.guild)].setTimezone(timezone)

# --- Events ---


@professor.command(aliases=["s"], checks=[eventChannelCheck])
async def schedule(ctx, *args):
    channel = ctx.channel
    author = ctx.author

    def gt0(x):
        try:
            x = int(x)
            if x < 0:
                raise ValueError
            return True
        except ValueError:
            return False

    # Pad args
    aux = []
    roles = True

    for arg in args:
        if arg == "-noroles":
            roles = False
        else:
            aux.append(arg)

    args = aux
    args = args + [None]*(5 - len(args))

    title = args[0]

    time = args[1]
    # Check time ok
    if time is not None:
        if not dags.parse(time, allow_tbd=True):
            await ctx.author.send(f"The date `{time}` is invalid. You will be asked to provide a new date and time.")
            time = None

    desc = args[2]
    if desc is not None:
        if len(desc) > 1024:
            await ctx.author.send(f"The description you provided is too long. The maximum is 1024 characters.")
            await ctx.author.send(f"{desc}")
            desc = None

    limit = args[3]
    # Check if limit ok
    if limit is not None:
        if not gt0(limit):
            await ctx.author.send(f"A limit of `{limit}` people is not a valid integer >= 0. You will be asked to specify a new limit.")
            limit = None

    def check(m):
        if m.content.lower() == "cancel":
            raise asyncio.TimeoutError
        return m.channel == channel and m.author == author

    def pcheck(m):
        return not m.pinned
    if eventsDict[hash(ctx.guild)].scheduling > 0:
        await ctx.author.send(content="Someone else is scheduling an event. Please wait until they are done.")
        return

    def checklimit(m):
        try:
            int(m.content)
            out = check(m)
            return out
        except ValueError:
            return False

    try:
        # Announce that we are scheduling
        eventsDict[hash(ctx.guild)].scheduling = 1

        emb = discord.Embed(title="Title ", description="Time: \n Description:")

        startEvent = await channel.send(content="Scheduling started. Type `cancel` to cancel", embed=emb)

        msg = None

        # Title
        if title is None:
            msg = await channel.send(content=infoMessages["eventTitle"])
            replyMsg = await professor.wait_for("message", check=check, timeout=120)

            title = replyMsg.content

            await replyMsg.delete()

        emb.title = title
        await startEvent.edit(embed=emb)

        # Time
        if time is None:
            if msg is not None:
                await msg.edit(content=infoMessages["eventTime"].format(str(eventsDict[hash(ctx.guild)].timezone)))
            else:
                msg = await ctx.channel.send(content=infoMessages["eventTime"].format(str(eventsDict[hash(ctx.guild)].timezone)))
            replyMsg = await professor.wait_for("message", check=check, timeout=120)

            # Check if time is ok
            timeOk = dags.parse(replyMsg.content, allow_tbd=True)
            while timeOk is False:
                await replyMsg.delete()
                await channel.send(content=infoMessages["invalidDate"].format(replyMsg.content), delete_after=5)
                replyMsg = await professor.wait_for("message", check=check, timeout=120)
                timeOk = dags.parse(replyMsg.content)

            time = replyMsg.content
            await replyMsg.delete()

        emb.description = "Time: {} \n Description:".format(time)
        await startEvent.edit(embed=emb)

        # Desc
        if desc is None:
            if msg is not None:
                await msg.edit(content=infoMessages["eventDesc"])
            else:
                msg = await ctx.channel.send(content=infoMessages["eventDesc"])

            descOk = False
            while not descOk:
                replyMsg = await professor.wait_for("message", check=check, timeout=120)
                desc = replyMsg.content
                await replyMsg.delete()

                if len(desc) > 1024:
                    await ctx.author.send(f"The description you provided is too long. The maximum is 1024 characters.")
                    await ctx.author.send(f"{desc}")
                else:
                    descOk = True

        emb.description = "Time: {} \n Description: {}".format(time, desc)
        await startEvent.edit(embed=emb)

        # Roles
        emojis = []
        if roles:
            roleInfoMsg = "React to this message with any event specific roles. Type `done` when done."
            if msg is not None:
                await msg.edit(content=roleInfoMsg)
            else:
                msg = await ctx.channel.send(content=roleInfoMsg)

            def donecheck(m):
                return check(m) and m.content.lower() == "done"

            replyMsg = await professor.wait_for("message", check=donecheck, timeout=120)
            await replyMsg.delete()

            msg = await ctx.channel.fetch_message(msg.id)

            reactionsOnMsg = msg.reactions
            await msg.clear_reactions()

            for reaction in reactionsOnMsg:
                await msg.edit(content="Please enter a name for {}".format(str(reaction)))
                nameRep = await professor.wait_for("message", check=check, timeout=120)
                name = nameRep.content
                await nameRep.delete()

                await msg.edit(content="Please enter the limit of people for {} (0 for no limit).".format(str(reaction)))
                rlimitRep = await professor.wait_for("message", check=checklimit, timeout=120)
                rlimit = int(rlimitRep.content)
                await rlimitRep.delete()

                emojis.append((str(reaction), name, rlimit))

        # Total limit
        if limit is None:
            limitInfoMsg = "Please enter the total limit of people who can join the event (0 for no limit)."
            if msg is not None:
                await msg.edit(content=limitInfoMsg)
            else:
                msg = await ctx.channel.send(content=limitInfoMsg)

            limitRep = await professor.wait_for("message", check=checklimit, timeout=120)
            limitOk = gt0(limitRep.content)
            limit = limitRep.content

            # Check >= 0
            while not limitOk:
                await msg.edit(content=f"`{limit}` is not an integer >= 0. \nPlease enter a limit for the event (0 for no limit).")
                limitRep = await professor.wait_for("message", check=checklimit, timeout=120)
                limitOk = gt0(limitRep.content)
                limit = limitRep.content

            await limitRep.delete()

        # Delete temp messages
        if msg is not None:
            await msg.delete()
        await startEvent.delete()

        # Schedule events
        if eventsDict[hash(ctx.guild)].createEvent(time, title, desc, emojis, limit, ctx.author.id):
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
            eventsDict[hash(ctx.guild)].insertIntoLog("{} scheduled event `{}` for `{}`.".format(ctx.author.display_name, title, time))
        else:
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
            await ctx.channel.send(content=infoMessages["eventCreationFailed"].format(prefix), delete_after=15)
        eventsDict[hash(ctx.guild)].scheduling = 0
    except asyncio.TimeoutError:
        if ctx.channel == eventsDict[hash(ctx.guild)].channel:
            await ctx.channel.purge(check=pcheck)
    finally:
        eventsDict[hash(ctx.guild)].scheduling = 0


@professor.command(aliases=["r"], checks=[eventChannelCheck])
async def remove(ctx, fakeId):
    # Remove an event
    # command syntax: remove [eventId]

    guildHash = hash(ctx.guild)

    event = eventsDict[guildHash].getEvent(fakeId)

    # Get actual event id
    eventId = eventsDict[guildHash].getEventId(fakeId)

    # Confirmation check
    reactMsg = await ctx.channel.fetch_message(eventsDict[hash(ctx.guild)].myLogMessageId)

    await reactMsg.edit(content="Are you sure you want to remove the event\n> {}".format(event.name))

    # Emojis
    emojis = foodEmojis.foodEmojis("res/foodemojis.txt")

    await reactMsg.add_reaction(emojis.checkmark)
    await reactMsg.add_reaction(emojis.cancel)

    def check(r):
        emojiOk = str(r.emoji) in [emojis.checkmark, emojis.cancel]
        userOk = r.user_id == ctx.author.id
        messageOk = r.message_id == reactMsg.id
        return emojiOk and userOk and messageOk

    # Wait for rection
    try:
        payload = await professor.wait_for("raw_reaction_add", check=check)
        if str(payload.emoji) == emojis.cancel:
            raise asyncio.TimeoutError
    except asyncio.TimeoutError:
        return

    # Check if event id was found and if removal successful
    if eventId and eventsDict[guildHash].removeEvent(eventId):
        eventsDict[hash(ctx.guild)].insertIntoLog("{} removed event `{}`.".format(ctx.author.display_name, event.name))
    else:
        await ctx.author.send(content=infoMessages["eventRemovalFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["a", "join", "j"], checks=[eventChannelCheck])
async def attend(ctx, eventId):
    # Attend an event
    # Command syntax: attend [eventId]
    try:
        int(eventId)
    except TypeError:
        await ctx.author.send(f"Event id must be an integer. You entered `{eventId}`.")
        return

    role = ""

    emojis = []

    # Fetch event
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)

    # Check if event is full
    if event.full() and ctx.author.id not in event.people:
        await ctx.channel.send(content="That event is already full!", delete_after=15)
        return

    # Get event roles
    if event.roles != []:
        if eventsDict[hash(ctx.guild)].attending > 0:
            await ctx.author.send("Someone else is joining an event. Wait until they are finished and try again.")
            return
        else:
            eventsDict[hash(ctx.guild)].attending = 1
        try:
            for role in event.roles:
                if event.fullRole(role[0]):
                    continue
                emojis.append(role[0])
            if len(emojis) == 0:
                role = ""
            else:
                rolelist = []
                for u, v, z in event.roles:
                    limitString = " ({}/{})".format(event.peopleInRole[u], event.rolelimits[u]) if event.rolelimits[u] != 0 else ""
                    rolelist.append(u + ": " + v + limitString)

                rolelist = "\n".join(rolelist)

                reactMsg = await ctx.channel.fetch_message(eventsDict[hash(ctx.guild)].myLogMessageId)

                def check(payload):
                    return payload.member == ctx.author and str(payload.emoji) in emojis and payload.message_id == reactMsg.id

                await reactMsg.edit(content="{} Please pick a role by reacting to this message:\n{}".format(ctx.author.mention, rolelist))

                for emoji in emojis:
                    await reactMsg.add_reaction(emoji)

                payload = await professor.wait_for("raw_reaction_add", check=check, timeout=60)

                role = str(payload.emoji)

                eventsDict[hash(ctx.guild)].attending = 0


        except asyncio.TimeoutError:
            def pcheck(m):
                return not m.pinned
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
                return
        finally:
            eventsDict[hash(ctx.guild)].attending = 0

    # Attend event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, True, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        eventsDict[hash(ctx.guild)].insertIntoLog("{} joined event `{}`.".format(ctx.author.display_name, event.name))

        hook = events.Hook(ctx, event)
        asyncio.create_task(hook.execute("attend"))
    else:
        await ctx.author.send(content=infoMessages["attendFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["l"], checks=[eventChannelCheck])
async def leave(ctx, eventId):
    # Leave an event
    # Command syntax: leave [eventId]

    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    try:
        role = event.rolesdict[ctx.author.id]
    except KeyError:
        role = ""

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, False, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        eventsDict[hash(ctx.guild)].insertIntoLog("{} left event `{}`.".format(ctx.author.display_name, event.name))

        hook = events.Hook(ctx, event)
        asyncio.create_task(hook.execute("leave"))

    else:
        await ctx.author.send(content=infoMessages["leaveFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["u"], checks=[eventChannelCheck])
async def update(ctx, eventId, toUpdate, *, newInfo):
    # Updates eventId description or name to newInfo
    # Command syntax: update [eventId] [to update] [new info]

    # Check if usere is scheduler
    if toUpdate in ["description", "name", "date", "owner", "limit", "role"]:

        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        if toUpdate == "description":
            if len(newInfo) > 1024:
                await ctx.author.send(f"The description you provided is too long. The maximum is 1024 characters.")
                await ctx.author.send(f"{desc}")
                return
            oldMsg = (event.description[:150] + "...") if len(event.description) > 150 else event.description
            newInfoMsg = newInfo
            toUpdateMsg = toUpdate
        elif toUpdate == "name":
            oldMsg = event.name
            newInfoMsg = newInfo
            toUpdateMsg = toUpdate
        elif toUpdate == "date":
            if not dags.parse(newInfo, allow_tbd=True):
                await ctx.author.send("`{}` is not a valid date format".format(newInfo))
                return
            oldMsg = event.printableDate()
            newInfoMsg = newInfo
            toUpdateMsg = toUpdate
        elif toUpdate == "owner":
            memconv = discord.ext.commands.MemberConverter()

            newOwner = await memconv.convert(ctx, newInfo)
            oldOwner = await memconv.convert(ctx, str(event.ownerId))

            toUpdate = "ownerId"
            newInfo = newOwner.id

            toUpdateMsg = "owner"
            newInfoMsg = newOwner.display_name
            oldMsg = oldOwner.display_name

        elif toUpdate == "limit":
            try:
                newInfo = int(newInfo)
                if newInfo < 0:
                    raise ValueError
            except ValueError:
                await ctx.author.send(f"`{newInfo}` is not a valid number!")
                return
            toUpdate = "eventLimit"
            toUpdateMsg = "limit"
            newInfoMsg = newInfo
            oldMsg = event.limit

        elif toUpdate == "role":
            # Split our arguments
            args = newInfo.split()

            # Check if we have enough args
            if len(args) < 2:
                await ctx.author.send("Not enough arguments were supplied to update the role. Please check `p? help update`")
                return

            # Only allow 2 args if we are updating emoji
            if args[1].lower() != "emoji" and len(args) == 2:
                await ctx.author.send("Not enough arguments were supplied to update the role. Please check `p? help update`")
                return

            # Unpack args
            roleEmoji = args[0]

            roleField = args[1]
            roleField = roleField.lower()

            if len(args) == 2:
                roleNewInfo = ""
            else:
                roleNewInfo = args[2]


            # Check if we can update the event's roles
            if event.roles == []:
                await ctx.author.send(f"Event `{eventId}` has no roles!")
                return

            # Fetch the role and check if our emoji is valid
            role = event.getRole(roleEmoji)
            if role is False:
                await ctx.author.send(f"{roleEmoji} is not a valid role for event `{eventId}`!")
                return
            elif role[0] != roleEmoji:
                await ctx.author.send(f"{roleEmoji} is not a valid role emoji for event `{eventId}`!")
                return

            # Check if our role field is valid
            if roleField not in ["emoji", "name", "limit"]:
                await ctx.author.send(f"The field `{roleField}` is invalid. Please check `p? help update`.")
                return

            # If we are updating the limit, we need to validate the number
            if roleField == "limit":
                try:
                    roleNewInfo = int(roleNewInfo)
                    if roleNewInfo < 0:
                        raise ValueError
                except ValueError:
                    await ctx.author.send(f"`{roleNewInfo}` is not a valid number!")
                    return


            # If we are updating emoji we need a special prompt
            if roleField == "emoji":
                # Ask for reaction
                reactMsg = await ctx.channel.fetch_message(eventsDict[hash(ctx.guild)].myLogMessageId)

                await reactMsg.edit(content=f"{ctx.author.mention} Please react to this message with the new emoji for role {role[1]}.")

                def check(p):
                    a = (p.user_id == ctx.author.id and p.message_id == reactMsg.id)
                    return a

                try:
                    # Wait for new emoji
                    r = await professor.wait_for("raw_reaction_add", check=check, timeout=120)
                    roleNewInfo = str(r.emoji)
                except asyncio.TimeoutError:
                    return
                finally:
                    await reactMsg.clear_reactions()

                # Check for dupes
                if event.getRole(roleNewInfo):
                    await ctx.author.send("You cannot set the new emoji to on that is already assigned to a role for this event!")
                    return

            toUpdate = "role"
            toUpdateMsg = f"{role[1]} role's {roleField}"
            newInfoMsg = roleNewInfo
            oldMsg = ""
            newInfo = [roleEmoji, roleField, roleNewInfo]
        else:
            oldMsg = ""
            toUpdateMsg = toUpdate

        if eventsDict[hash(ctx.guild)].updateEvent(eventId, toUpdate, newInfo):
            if oldMsg:
                oldMsg = f"from `{oldMsg}` "
            eventsDict[hash(ctx.guild)].insertIntoLog("{} updated event `{}`'s `{}` {}to `{}`.".format(ctx.author.display_name, event.name, toUpdateMsg, oldMsg, newInfoMsg))

        else:
            await ctx.author.send(content=infoMessages["updateFailed"].format(prefix), delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["invalidUpdateField"], delete_after=15)


@professor.command(checks=[eventChannelCheck], aliases=["k", "puntcunt"])
async def kick(ctx, userToKick: discord.Member, eventId):
    # Leave an event
    # Command syntax: leave [eventId]

    uid = userToKick.id
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    try:
        role = event.rolesdict[uid]
    except KeyError:
        role = ""

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, uid, False, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)
        eventsDict[hash(ctx.guild)].insertIntoLog("{} kicked {} from `{}`.".format(ctx.author.display_name, userToKick.display_name, event.name))
    else:
        await ctx.author.send(content="I could not kick {} from `{}`".format(userToKick.display_name, event.name))


@professor.command()
async def when(ctx, eventId, offset):
    try:
        offset = int(offset)
    except ValueError:
        await ctx.author.send("The time offset you provided (`{}`) is invalid. Valid offsets are positive and negative whole numbers.")
        return

    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    if not event:
        await ctx.author.send("Invalid event id.")
        return

    if offset >= 0:
        offsetStr = "UTC+{}".format(offset)
    else:
        offsetStr = "UTC-{}".format(abs(offset))

    embed = discord.Embed(title=event.name, colour=accent_colour)
    embed.add_field(name="Start time in {}".format(offsetStr), value=event.offsetPrintableDate(offset))
    embed.add_field(name="Time until the event starts", value=event.timeUntil())
    await ctx.author.send(embed=embed)


@professor.command()
async def owner(ctx, eventId):
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    if event:
        memconv = discord.ext.commands.MemberConverter()
        try:
            owner = await memconv.convert(ctx, str(event.ownerId))
            ownerMention = owner.mention
        except discord.ext.commands.CommandError:
            ownerMention = "Noone"

        await ctx.channel.send("The current owner of event `{}` is {}".format(eventId, ownerMention))
    else:
        await ctx.author.send("`{}` is not a valid event id.".format(eventId))


@professor.group(invoke_without_command=True)
async def hook(ctx, eventId, toProcess):
    if ctx.invoked_subcommand is None:
        # Check if I can process hook
        availToProcess = ["attend", "leave"]

        if toProcess.lower() not in availToProcess:
            await ctx.author.send("`{}` is not an available command to hook into.".format(toProcess))
            return

        toProcess = toProcess.lower()

        # Check if event exists
        if not eventsDict[hash(ctx.guild)].getEvent(int(eventId)):
            await ctx.channel.send("Invalid event id.")
            return

        # Send initial message
        await ctx.author.send("What action would you like me to execute on `{}`?\nAvailable actions are:\n>>> `message`".format(toProcess))

        try:
            # Check function
            def check(m):
                return m.author == ctx.author and m.content.lower() in ["message", "cancel"]
            # Wait for reply with action
            reply = await professor.wait_for("message", check=check,  timeout=60)
            action = reply.content.lower()

            if action == "cancel":
                raise asyncio.TimeoutError

            elif action == "message":
                # Update my message and get message content
                mymsg = await ctx.author.send(content="What is the message you would like me to send users when they {}?".format(toProcess))

                def check(m):
                    return m.author == ctx.author

                reply = await professor.wait_for("message", check=check, timeout=300)
                params = reply.content

                await mymsg.delete()

            res = eventsDict[hash(ctx.guild)].createHook(eventId, toProcess, action, params)
            if res:
                event = eventsDict[hash(ctx.guild)].getEvent(eventId)

                embed = discord.Embed(title="Hook created for {}".format(event.name), description="On `{}`, {} users with\n>>> {}".format(toProcess, action, params), colour=accent_colour)

                await ctx.author.send(embed=embed)

        except asyncio.TimeoutError:
            await mymsg.delete()

        if delperm(ctx):
            await ctx.message.delete()


@hook.command(name="remove")
async def removeHook(ctx, eventId):
    hooks = eventsDict[hash(ctx.guild)].getAllHooks(eventId)
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)

    # Check if there are any hooks
    if not hooks:
        await ctx.author.send("There are no hooks for event `{}`.".format(eventId))
        return
    if not event:
        await ctx.author.send("No event with id `{}` exists.".format(eventId))
        return


    # Generate hook list
    embed = discord.Embed(title="Hooks for {}".format(event.name), colour=accent_colour)
    i = 1
    for h in hooks:
        embed.add_field(name="{}. On `{}`".format(i, h["toProcess"]), value="{}: {}".format(h["action"], h["params"]), inline=False)
        i += 1

    pickmessage = await ctx.author.send(content="Please pick a hook to remove by replying with the relevant number. Type `cancel` to cancel", embed=embed)

    # Check for validity of reply
    def check(m):
        if m.author == ctx.author:
            if m.content.lower() == "cancel":
                return True
            try:
                a = int(m.content)
                return a <= len(hooks)
            except ValueError:
                return False

    try:
        # Wait for user to pick hook to remove
        reply = await professor.wait_for("message", check=check, timeout=60)
        if reply.content.lower() == "cancel":
            raise asyncio.TimeoutError

        hookNumber = int(reply.content)

        # Remove hook
        eventsDict[hash(ctx.guild)].removeHook(eventId, hookNumber)
        await ctx.author.send("Hook successfully removed", delete_after=10)

        await pickmessage.delete()

        if delperm(ctx):
            await ctx.message.delete()

    except asyncio.TimeoutError:
        await pickmessage.delete()
        if delperm(ctx):
            await ctx.message.delete()


# --- Misc ---

@professor.group()
async def notice(ctx):
    return

@notice.command()
async def new(ctx):
    noticeCheck = noticelib.Notice(hash(ctx.guild), "db/notice.db")
    msg = await ctx.channel.send("This is your brand new notice message!")
    await msg.edit(content=f"This is your brand new notice message!\n\nThis message's id is `{msg.id}`\nYou can edit this message with `p? notice edit {msg.id} [new message]`\n\nHave fun!")
    noticeCheck.create(msg.id)

@notice.command()
async def edit(ctx, msgid: int, *, newmessage):
    noticeCheck = noticelib.Notice(hash(ctx.guild), "db/notice.db")
    if noticeCheck.isNotice(msgid):
        try:
            msg = await ctx.channel.fetch_message(msgid)
            await msg.edit(content=newmessage)
        except discord.NotFound:
            await ctx.author.send("You need to be in the same channel as the notice message.")
    else:
        await ctx.author.send("That is not a notice message!")



@professor.command()
async def julia(ctx, *, c=""):
    # Constans
    THRESHOLD = 10**20

    if "value" in c:
        c = re.sub("value", "", c)
        style = "value"
    else:
        c = re.sub("hue", "", c)
        style = "hue"

    if style == "hue":
        ITERATIONS = 360
    elif style == "value":
        ITERATIONS = 255

    SIZEX_FINAL = 500
    SIZEY_FINAL = 500

    SIZEX = round(SIZEX_FINAL * 1.2)
    SIZEY = round(SIZEY_FINAL * 1.2)

    CENTERX = 0
    CENTERY = 0

    if c.strip() == "":
        CONSTANT = complex(0, 0)
        while abs(CONSTANT) < 0.4:
            CONSTANT = complex(random.random() * 2.3 - 1.3, random.random() * 1.4 - 0.7)
    else:
        c = re.sub(" ", "", c)
        c = re.sub("i", "j", c)
        CONSTANT = complex(c)

    ZOOM = 150

    OFFSETX = CENTERX * ZOOM
    OFFSETY = CENTERY * ZOOM

    # COLOURMAP
    HUEMAP = []
    VALMAP = []

    for a in range(0, ITERATIONS):
        HUEMAP.append((160 + round(360 * (((ITERATIONS - a) / ITERATIONS)))) % 361)
        VALMAP.append(round(255 * math.sqrt(a / ITERATIONS)))

    if style == "hue":
        MAP = HUEMAP
    else:
        MAP = VALMAP

    # Check for divergence
    def diverge(c, z=complex(0, 0), count=0):
        while count < ITERATIONS:
            # If length over threshhold diverges
            if abs(z) > THRESHOLD:
                return (True, count)
            z = (z**2 + c)
            count += 1
        # If max iters is reached, does not diverge
        return (False, count)

    # Image init
    img = Image.new("HSV", (SIZEX, SIZEY), (0, 0, 0))
    pixels = img.load()

    count = 0

    # Iterate over pixels, real values on X and imaginary on Y
    for R in range(img.size[0]):
        xval = (R - SIZEX / 2) / ZOOM
        for I in range(img.size[1]):
            # Update progress bar

            # Calculating actual coordinates
            zoom_offset_x = OFFSETX / ZOOM
            zoom_offset_y = OFFSETY / ZOOM

            yval = (I - SIZEY / 2) / ZOOM

            z = complex(xval + zoom_offset_x, yval + zoom_offset_y)

            # Get divergence
            out = diverge(CONSTANT, z=z)
            if out[0]:
                # Map degree of divergence to HSV value
                val = MAP[out[1]]

                # Edit pixel
                if MAP == HUEMAP:
                    pixels[R, I] = (val, 255, 255)
                elif MAP == VALMAP:
                    pixels[R, I] = (180, 100, val)
            count += 1

    # Save image
    img = img.resize((SIZEX_FINAL, SIZEY_FINAL), Image.ANTIALIAS)
    img = img.convert("RGB")

    imgio = io.BytesIO()
    img.save(imgio, "PNG")

    imgio.seek(0)

    # Read the image to a discord file object
    imgfile = discord.File(imgio, filename="result.png")

    await ctx.channel.send(file=imgfile, content=f"A julia set with c={str(CONSTANT)}")


@professor.group(checks=[notEventChannelCheck], invoke_without_command=True)
async def spoiler(ctx, *, content=None):
    outFiles = []

    if ctx.message.attachments == []:
        return

    for attachment in ctx.message.attachments:
        # Sækja skrá
        f = await attachment.to_file()
        # Fá nafn og breyta í spoiler
        fname = "SPOILER_" + f.filename

        # Actual skráin
        fp = f.fp

        # Bæta í út
        f = discord.File(fp, filename="SPOILER_" + fname)
        outFiles.append(f)

    await ctx.message.delete()

    if content is not None:
        content = "\n>>> {}".format(content)
    else:
        content = ""

    msg = await ctx.channel.send("From {}{}".format(ctx.author.mention, content), files=outFiles)
    eventsDict[hash(ctx.guild)].addSpoiler(msg.id, ctx.author.id, ctx.channel.id)


@spoiler.command()
async def delete(ctx):
    done = False

    while not done:
        lastid = eventsDict[hash(ctx.guild)].popLastSpoiler(ctx.author.id)

        if lastid is not None:
            try:
                msg = await ctx.guild.get_channel(lastid[1]).fetch_message(lastid[0])
                await msg.delete()
                if delperm(ctx):
                    await ctx.message.delete()
                done = True
            except discord.errors.NotFound:
                lastid = eventsDict[hash(ctx.guild)].popLastSpoiler(ctx.author.id)
        else:
            done = True


@professor.command(checks=[notEventChannelCheck], aliases=["cute", "cutestuff", "helppls", "pleasehelp"])
async def eyebleach(ctx):
    subs = ["eyebleach", "aww", "blep", "tuckedinkitties", "rarepuppers"]
    sub = random.choice(subs)
    subreddit = reddit.subreddit(sub)

    out = []
    ok_extensions = ["png", "gif", "jpg", "jpeg"]

    for submission in subreddit.top(time_filter="day", limit=15):
        url = submission.url
        if "gfycat" in url:
            url += ".gif"
        else:
            url = url.split(".")
            if url[-1] == "gifv":
                url[-1] = "gif"
            elif url[-1].lower() not in ok_extensions:
                continue
            url = ".".join(url)
        out.append((submission.title, url))

    pick = random.choice(out)
    await ctx.channel.send(content="From /r/{}:\n>>> {}\n{}".format(sub, pick[0], pick[1]))


@professor.command()
async def help(ctx, *, cmd=None):
    embeds = helper.helpCmd(prefix, cmd, "res/docs.json")
    if embeds is not None:
        for message in embeds:
            await ctx.author.send(embed=message)
    else:
        await ctx.author.send(content="Unrecognised command")


@professor.command(aliases=["dice", "random", "pick"])
async def roll(ctx, *, names):
    # Determine a random thing from a list

    await ctx.channel.send(content="And the winner is...")
    await asyncio.sleep(5)

    names = names.split(", ")

    winner = random.choice(names)

    await ctx.channel.send(content="{0} wins the roll! {1} {1} {1}".format(winner, party))


@professor.command(checks=[notEventChannelCheck])
async def sorry(ctx):
    await ctx.channel.send(content="Oh, that's alright {}. Don't worry about it ^^".format(ctx.author.display_name))


@professor.command(checks=[notEventChannelCheck], aliases=["orangejuice", "applejuice", "juice", "akidrugs"])
async def oj(ctx):
    with open("res/oj.png", "rb") as f:
        oj = discord.File(f, filename="High quality oj.png")
    await ctx.channel.send(file=oj)


@professor.command(checks=[notEventChannelCheck], aliases=["trúðagrín"])
async def clowntime(ctx):
    await ctx.channel.send(content=":o)")


@professor.command()
async def clean(ctx):
    def check(m):
        return m.author == ctx.author and m.content.lower() in ["yes", "no"]
    checkmsg = await ctx.channel.send(content="Are you sure you want to clear this channel?")
    rep = await professor.wait_for("message", check=check)
    if rep.content.lower() == "yes":
        await ctx.channel.purge(bulk=True)
        await ctx.channel.send("Finished deleting all I can! :sparkles:\nIf anything remains, run this command again.", delete_after=60)
    else:
        if delperm(ctx):
            await rep.delete()
        await checkmsg.delete()


@professor.command(checks=[notEventChannelCheck], aliases=["raidfrens", "plsrespec"])
async def respecraid(ctx):
    with open("res/raidfrens.png", "rb") as f:
        frens = discord.File(f, filename="raidfrens.png")
    await ctx.channel.send(file=frens, content="raid frens pls respec")


@professor.command()
async def calculate(ctx, *, query):
    # Get the results of the query

    primarypods = []
    imageUrlArray = []

    res = wolf.query(query)
    if res.success == "true":
        for pod in res.pods:
            if pod.primary:
                primarypods.append(pod)

        if len(primarypods) == 0:
            for pod in res.pods:
                primarypods.append(pod)

        for pod in primarypods:
            for sub in pod.subpods:
                if "img" in sub.keys():
                    imageUrlArray.append(sub["img"]["@src"])

        images = []
        widths = []
        heights = []

        # Read the primary image
        for url in imageUrlArray:
            img = io.BytesIO(urllib.request.urlopen(url).read())

            # Add a border to the image
            img = Image.open(img)

            width, height = img.size

            widths.append(width + 30)
            heights.append(height + 30)

            bg = Image.new("RGB", (width + 30, height + 15), (255, 255, 255))
            bg.paste(img, (15, 15))
            images.append(bg)

        bg = Image.new("RGB", (max(widths), sum(heights)), (255, 255, 255))

        i = 0
        h = 0
        while i < len(images):
            bg.paste(images[i], (0, h))
            h += heights[i]
            i += 1

        img = io.BytesIO()

        bg.save(img, "PNG")
        img.seek(0)

        # Read the image to a discord file object
        img = discord.File(img, filename="result.png")

        # Send results
        await ctx.channel.send(content=query.capitalize(), file=img)

    else:
        await ctx.author.send(content="Your query `{}` failed for some reason. Maybe wolfram alpha does not unterstand your query.".format(query))


@professor.group(invoke_without_command=True)
async def remindme(ctx, *, reminderString): # , *, reminderString):
    if ctx.invoked_subcommand is None:
        try:
            s = reminderString.split(" to ")
            time = s[0]
            reminder = " to ".join(s[1:])
        except IndexError:
            await ctx.author.send("Invalid reminder string. Please make sure it's in the format `[time] to [reminder]`.")
            return

        parsedTime = dags.parse(time)

        if not parsedTime:
            await ctx.author.send("The time you entered for the reminder `{}` is invalid.".format(reminder))
            return

        printableTime = parsedTime.strftime("%d %B %Y %H:%M")

        reminderWrapper.createReminder(ctx.author.id, reminderString)

        await ctx.author.send("I will remind you at `{} UTC` to `{}`.".format(printableTime, reminder))


@remindme.command(name="list")
async def listReminders(ctx, page=1):
    e = reminderWrapper.genList(ctx.author.id, page)
    if e is None:
        await ctx.author.send("You have no reminders.")
    elif e == -1:
        await ctx.author.send("That page does not exist.")
    else:
        await ctx.author.send(embed=e)


@remindme.command()
async def remove(ctx, reminder_id: int):
    r = reminderWrapper.removeReminder(ctx.author.id, reminder_id)
    if r:
        await ctx.author.send("Reminder successfully removed!")
    elif r == -1:
        await ctx.author.send("That reminder does not exist.")
    else:
        await ctx.author.send("An unknown error occured while removing that reminder.")


@professor.command()
async def pizza(ctx, link):
    if delperm(ctx):
        await ctx.message.delete()

    d = dags.parse("now", tz=eventsDict[hash(ctx.guild)].timezone, ignore_past=True)
    d = d.strftime("%d %b %Y %H:%M")

    embed = discord.Embed(title="Pizza ({})".format(d), description=link, colour=accent_colour)
    pizzaimages = imgur.subreddit_gallery("pizza", sort="hot")
    pizzaimage = pizzaimages[hash(link) % len(pizzaimages)].link

    embed.set_image(url=pizzaimage)
    await ctx.channel.send(embed=embed)


@professor.command()
async def forget_me(ctx):

    msg = await ctx.author.send("**ARE YOU SURE YOU WANT TO BE FORGOTTEN?**\nReply with `yes/no`")

    def check(m):
        return m.author == ctx.author and m.content.lower() in ["yes","no"]

    try:
        rep = await professor.wait_for("message", check=check)
    except asyncio.TimeoutError:
        await msg.delete()
        return

    if rep.content.lower() != "yes":
        await msg.delete()
        return


    if delperm(ctx):
        await ctx.messsage.delete()

    userid = ctx.author.id

    def henda(fname, table, col):
        conn = sqlite3.connect(fname)
        c = conn.cursor()

        c.execute(f'DELETE FROM {table} WHERE {col}=?', (userid, ))

        conn.commit()
        conn.close()

    henda("db/reminders.db", "reminders", "user_id")
    henda("db/salt.db", "salt", "userId")
    henda("db/spoilers.db", "spoilers", "userid")

    for guild in professor.guilds:
        member = guild.get_member(userid)

        if member is not None:
            allEvents = eventsDict[hash(guild)].getAllEvents()
            for event in allEvents:
                people = json.loads(event[5])
                out = []

                for person in people:
                    if person[0] != userid:
                        out.append(person)
                eventsDict[hash(guild)].updateEvent(event[1], "people", json.dumps(out), actualId=True)
                asyncio.create_task(updatePinned(eventsDict[hash(guild)].channel, guild))

    await msg.delete()
    await ctx.author.send("You have been forgotten.")



@professor.command()
async def secret_santa(ctx, eventId: int):
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    if event:
        people = event.people
        random.shuffle(people)
        i = 0

        memConv = discord.ext.commands.MemberConverter()
        while i < len(people):
            gifter = await memConv.convert(ctx, str(people[i]))
            rec = await memConv.convert(ctx, str(people[(i+1)%len(people)]))

            await gifter.send(f"For the {ctx.guild.name} secret santa event, you will be giving {rec.display_name} a little something.")
            i += 1
    else:
        await ctx.author.send("Invalid event id")


@professor.command()
async def poll(ctx, *options):
    if len(options) < 3:
        await ctx.author.send("Too few arguments passed to the `poll` command.")
        return

    if len(options) > 21:
        await ctx.author.send("Too many options for the poll. The maximum is 20 options.")

    name = options[0]
    options = options[1:]

    emojis = ["\U0001F1E6",
              "\U0001F1E7",
              "\U0001F1E8",
              "\U0001F1E9",
              "\U0001F1EA",
              "\U0001F1EB",
              "\U0001F1EC",
              "\U0001F1ED",
              "\U0001F1EE",
              "\U0001F1EF",
              "\U0001F1F0",
              "\U0001F1F1",
              "\U0001F1F2",
              "\U0001F1F3",
              "\U0001F1F4",
              "\U0001F1F5",
              "\U0001F1F6",
              "\U0001F1F7",
              "\U0001F1F8",
              "\U0001F1F9"]
    abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    emojis_avail = emojis[0:len(options)]

    votes = {a: 0 for a in options}

    votemap = {}

    def makePoll(votes):
        bars = len(votes)

        IMAGEMARGIN = 30

        BARHEIGHT = 100
        BARMARGIN = 100
        BARINNERMARGIN = 20

        FONTSIZE = 52

        HEIGHT = 2 * IMAGEMARGIN + bars * (BARHEIGHT + BARMARGIN) - BARMARGIN
        WIDTH = 1000

        img = Image.new("RGBA", (WIDTH, HEIGHT), color="#2C2F3300")
        draw = ImageDraw.Draw(img)

        for option in votes.items():
            msg = f"A. {option[0]} (10000) 100%"
            font = ImageFont.truetype("res/OpenSansEmoji.ttf", FONTSIZE)
            textSize = draw.textsize(msg, font=font)

            WIDTH = max((textSize[0] + 100, WIDTH))

        img = Image.new("RGBA", (WIDTH, HEIGHT), color="#2C2F3300")
        draw = ImageDraw.Draw(img)

        totalVotes = sum(votes.values())

        i = 0
        NextY = IMAGEMARGIN
        while i < bars:
            option = list(votes.items())[i]
            if option[1] == 0:
                barwidth = 1
            else:
                barwidth = (WIDTH - 2 * IMAGEMARGIN) * option[1] / totalVotes

            if i == 0:
                margin = 0
            else:
                margin = BARMARGIN

            # Rectangle coordinates
            x1 = IMAGEMARGIN
            y1 = NextY + margin
            x2 = barwidth + IMAGEMARGIN
            y2 = NextY + margin + BARHEIGHT

            draw.rectangle([x1, y1, x2, y2], fill="#7289DAFF")

            # Texti
            if totalVotes == 0:
                percent = 0
            else:
                percent = round(100 * option[1] / totalVotes)
            msg = f"{abc[i]}. {option[0]} ({option[1]}) {percent}%"

            font = ImageFont.truetype("res/OpenSansEmoji.ttf", FONTSIZE)

            textSize = draw.textsize(msg, font=font)

            textPos = [IMAGEMARGIN + BARINNERMARGIN,
                       ((y1 + y2) / 2) - textSize[1] / 2]

            if textSize[0] + BARINNERMARGIN >= barwidth - BARINNERMARGIN and textPos[0] + barwidth + textSize[0] <= WIDTH:
                textPos[0] += barwidth

            draw.text(textPos, msg, font=font, fill="white")

            NextY += margin + BARHEIGHT
            i += 1
        return img

    img = io.BytesIO()
    makePoll(votes).save(img, "PNG")

    img.seek(0)

    # Read the image to a discord file object
    img = discord.File(img, filename="result.png")

    embed = discord.Embed(title=name, description="Voted:", color=accent_colour)
    embed.set_image(url="attachment://result.png")

    pollmsg = await ctx.channel.send(embed=embed, file=img)

    for emoji in emojis_avail:
        await pollmsg.add_reaction(emoji)

    def check(payload):
        return not payload.member.bot and payload.emoji.name in emojis_avail and payload.message_id == pollmsg.id

    while True:
        try:
            payload = await professor.wait_for("raw_reaction_add", check=check, timeout=86400)
        except asyncio.TimeoutError:
            break

        i = emojis_avail.index(payload.emoji.name)
        u = payload.member
        try:
            if votemap[u] == options[i]:
                votemap.pop(u)
            else:
                votemap[u] = options[i]
        except KeyError:
            votemap[u] = options[i]

        votes = {a: 0 for a in options}
        for voter in votemap.keys():
            votes[votemap[voter]] += 1

        img = io.BytesIO()
        makePoll(votes).save(img, "PNG")

        img.seek(0)

        # Read the image to a discord file object
        img = discord.File(img, filename="result.png")
        await pollmsg.delete()

        votedmsg = "Voted: " + ', '.join([u.mention for u in votemap.keys()])

        embed = discord.Embed(title=name, description=f"{votedmsg}", colour=accent_colour)
        embed.set_image(url="attachment://result.png")

        pollmsg = await ctx.channel.send(embed=embed, file=img)
        for emoji in emojis_avail:
            await pollmsg.add_reaction(emoji)

    await pollmsg.edit(content="**POLL CLOSED**")


# --- Salt ---


@professor.command(checks=[notEventChannelCheck])
async def salt(ctx):
    # Ordinal from Stack Overflow
    def ordinal(n):
        return "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

    # Get a random nugg and increment count
    username = ctx.author.display_name
    insultMessage = saltWraper.insult(username)
    count = saltWraper.eatCookie(ctx.author)

    await ctx.send("Here is your {} nugget of salt, {}:\n> {}".format(ordinal(count), username, insultMessage))


@professor.command(checks=[notEventChannelCheck])
async def saltboard(ctx):
    # Display leaderboard of salt
    board = saltWraper.getCookieBoard(ctx.guild)

    # Check if empty
    if board:
        out = ""
    else:
        out = "Nothing here yet"

    # Make message
    msg = discord.Embed(title="Salt leaderboards:", description="")
    for entry in board:
        out += entry[0] + ":\u2003" + str(entry[1]) + "\n"
    msg.add_field(name="\u200b", value=out, inline=0)

    await ctx.send(embed=msg)

# --- Lofi ---
@professor.event
async def on_voice_state_update(member, before, after):
    for i in professor.voice_clients:
        if i.channel == before.channel and len(before.channel.members) == 1:
            i.stop()
            await i.disconnect()
            break


@professor.group(invoke_without_command=True, checks=[notEventChannelCheck])
async def chill(ctx):
    if ctx.invoked_subcommand is None:
        try:
            vc = ctx.message.author.voice.channel
            s = await vc.connect()

            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("http://mystic.tokyo:8000/lofi.mp3"))
            s.play(source)
            source.volume = 0.1
        except AttributeError:
            await ctx.author.send(content="You have to be on voice to do that")
        except discord.ClientException:
            await ctx.author.send(content="Sorry, I'm already connected to a voice channel.")
        except discord.errors.Forbidden:
            await ctx.author.send(content="I do not have permission to use voice chat.")

    if delperm(ctx):
        await ctx.message.delete()


@chill.command()
async def stop(ctx):
    try:
        authorvc = ctx.message.author.voice.channel
        for i in professor.voice_clients:
            if i.channel == authorvc:
                i.stop()
                await i.disconnect()
                break
    except AttributeError:
        await ctx.author.send(content="You have to be on voice to do that")

    if delperm(ctx):
        await ctx.message.delete()


@chill.command(aliases=["v"])
async def volume(ctx, v):
    try:
        v = int(v) / 100
        if v >= 0 and v <= 1:
            try:
                authorvc = ctx.message.author.voice.channel
                for i in professor.voice_clients:
                    if i.channel == authorvc:
                        i.source.volume = v
                        break
            except:
                await ctx.author.send(content="You have to be on voice to do that")
        else:
            await ctx.send("Please give a volume between 0 and 100")
    except TypeError:
        await ctx.send("Please give a volume between 0 and 100")

    if delperm(ctx):
        await ctx.message.delete()


@chill.command(aliases=["now", "playing"])
async def nowplaying(ctx):
    info = urllib.request.urlopen("https://mystic.tokyo/lofi/player/info.txt").read().decode("utf-8").strip()
    info = info.split(" - ")
    title = " - ".join(info[1:])
    artist = info[0]

    embed = discord.Embed(title="Now playing", description="{} by {}".format(title, artist), colour=accent_colour)
    embed.set_image(url="https://mystic.tokyo/lofi/player/cover.jpg?v={}".format(random.randint(0, 100000000000)))

    await ctx.send(embed=embed, delete_after=60)

    if delperm(ctx):
        await ctx.message.delete()

# --- Log ---


@professor.command()
async def log(ctx):
    log = eventsDict[hash(ctx.guild)].getLog(dateform="%D %T")
    embed = discord.Embed(title="Activity log", color=accent_colour)

    for e in log:
        embed.add_field(name=e[0], value=e[1], inline=False)

    await ctx.author.send(embed=embed, delete_after=300)

    if delperm(ctx):
        await ctx.message.delete()


@professor.command()
async def readycheck(ctx, *args):
    # check if expires is in args
    if "-expires" in args:
        args = list(args)
        i = args.index("-expires")
        if "-expires" == args[-1]:
            await ctx.author.send("Missing the `[date]` argument for `-expires`.")
            return

        expires = " ".join(args[i + 1:])

        date = dags.parse(expires, eventsDict[hash(ctx.guild)].timezone)
        if date:
            timeout = date - eventsDict[hash(ctx.guild)].timezone.localize(datetime.now())
            timeout = int(timeout.total_seconds())
            del args[i:]
        else:
            await ctx.author.send("Invalid date format: `{}`.".format(expires))
            return
    else:
        timeout = 86400

    # Emojis
    checkmark = "\u2705"
    cross = "\u274C"
    wait = "\U0001F552"

    mentionStrings = []
    users = []
    if len(args) == 0:
        raise discord.ext.commands.errors.MissingRequiredArgument(dummyparam("mentions"))

    usingRole = True

    # Convert arguments to members or role
    memconv = discord.ext.commands.MemberConverter()
    roleconv = discord.ext.commands.RoleConverter()
    for entry in args:
        try:
            u = await memconv.convert(ctx, entry)
            users.append(u)
            mentionStrings.append(u.mention)

        except discord.ext.commands.CommandError:
            role = await roleconv.convert(ctx, entry)
            users += role.members
            mentionStrings.append(role.mention)

    # Get the display names of all the users
    dnames = []
    for user in users:
        dnames.append(user.display_name)

    # Initialize dictionary for status of each user
    userDict = {}

    for user in users:
        userDict[user] = ""

    def outmsg():
        # Function to generate the ready check embed list
        out = discord.Embed(title="Readycheck!")

        field = []

        for user in users:
            field.append(userDict[user] + " " + user.display_name)

        out.add_field(name="Members", value="\n".join(field))

        return out

    # Post the readycheck
    readyCheckMsg = await ctx.channel.send(embed=outmsg())

    # Add reactions to the message
    await readyCheckMsg.add_reaction(checkmark)
    await readyCheckMsg.add_reaction(wait)
    await readyCheckMsg.add_reaction(cross)

    def check(payload):
        # Check if reaction is of a valid type
        # and that the user who reacted is in the list of users
        emojis = [checkmark, cross, wait]
        if payload.emoji.name in emojis and payload.member in users and payload.message_id == readyCheckMsg.id:
            return True
        else:
            return False

    # Loop until everyone is ready
    count = 0

    while count < len(users):
        try:
            # Wait for a reaction
            payload = await professor.wait_for("raw_reaction_add", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            # After 24h timeout and try to delete the readycheck
            try:
                await readyCheckMsg.delete()
            except discord.errors.NotFound:
                pass
            break

        # Set the status of the member who reacted to the emoji reacted with
        userDict[payload.member] = payload.emoji.name

        # Update message
        await readyCheckMsg.edit(embed=outmsg())

        # Count how many members are ready
        count = 0
        for emoji in userDict.values():
            if emoji == checkmark:
                count += 1

    mentionstr = " ".join(mentionStrings)

    if count == len(users):
        await ctx.channel.send(content=mentionstr + " Everyone is ready")
    else:
        await ctx.channel.send(content=mentionstr + " Ready check completed with `{}/{}` members ready.".format(count, len(users)), embed=outmsg())


# --- Soundboard ---

async def playFromSoundboard(ctx, name):
    sounds = soundBoardDict[hash(ctx.guild)].getSounds()
    if name in sounds.keys():
        url = sounds[name]

        try:
            voiceChannel = ctx.author.voice.channel
            connection = await voiceChannel.connect()

            source = discord.FFmpegPCMAudio(url)
            connection.play(source)
            while connection.is_playing():
                await asyncio.sleep(1)

            await asyncio.sleep(2)
            await connection.disconnect()
        except AttributeError:
            await ctx.author.send(content="You need to be connected to voice chat to do that!")
        except discord.ClientException:
            await ctx.author.send(content="Sorry, I'm already connected to a voice channel.")
        except discord.errors.Forbidden:
            await ctx.author.send(content="I do not have permission to use voice chat.")
    else:
        await ctx.author.send(content="No such sound `{}`. Notice that sound names are cases sensitive.".format(name))


@professor.group(aliases=["sb"])
async def soundboard(ctx):
    # Ávaxta emojis
    with open("res/foodemojis.txt", "r") as f:
        emojis_avail = f.read().splitlines()

    random.shuffle(emojis_avail)

    # Cancel emoji
    x = "\U0000274C"
    emoji_dict = {}

    if ctx.invoked_subcommand is None:
        # Ef engin subcommand þá gera lista
        sounds = soundBoardDict[hash(ctx.guild)].getSounds()

        if sounds == {}:
            await ctx.channel.send(content="There are no sounds yet. Please add some with the `soundboard add` command.")
            return

        # Búa til lista og velja emojis
        out = ">>> Available sounds:\n"
        i = 0
        for key in sounds.keys():
            out = out + "{}\t`{}`\n".format(emojis_avail[i], str(key))
            emoji_dict[emojis_avail[i]] = str(key)
            i += 1

        # Senda lista og bæta við emojis
        msg = await ctx.channel.send(content=out)

        for emoji in emoji_dict.keys():
            await msg.add_reaction(emoji)

        await msg.add_reaction(x)

        # Bíða eftir vali
        try:
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in (list(emoji_dict.keys()) + [x]) and msg.id == reaction.message.id

            reaction, user = await professor.wait_for("reaction_add", check=check, timeout=60)
            if delperm(ctx):
                await msg.delete()
                await ctx.message.delete()

            if (reaction.emoji != x):
                await playFromSoundboard(ctx, emoji_dict[reaction.emoji])

        except asyncio.TimeoutError:
            if delperm(ctx):
                await msg.delete()
                await ctx.message.delete()


@soundboard.command(aliases=["a"])
async def add(ctx, name):
    # Bæta við hljóði í soundboard
    extensions = ["mp3", "wav"]
    attachments = ctx.message.attachments
    sounds = soundBoardDict[hash(ctx.guild)].getSounds()
    if len(sounds) == 19:
        await ctx.author.send(content="Could not add sound `{}`. Maximum number of sounds reached. Please delete some before adding more.".format(name))
        return

    # Checka ef fæll
    if attachments:
        url = attachments[0].url
        filename = attachments[0].filename

        # Checka ef hljóðfæll
        if filename.split(".")[-1].lower() in extensions:
            # Bæta við
            if soundBoardDict[hash(ctx.guild)].createSound(name, url):
                await ctx.channel.send("Sound `{}` successfully added.".format(name))
            elif name in sounds.keys():
                await ctx.author.send("Could not add sound `{}` because a sound with that name already exists.".format(name))
            else:
                await ctx.aythor.send("Could not add sound `{}` for an unknown reason.".format(name))

        else:
            await ctx.author.send(content="Invalid file extension.")
    else:
        await ctx.author.send(content="You must attach a sound file to your command message.")


@soundboard.command(aliases=["r"])
async def remove(ctx, name):
    # Henda hljóði
    if soundBoardDict[hash(ctx.guild)].removeSound(name):
        await ctx.channel.send(content="Sound `{}` successfully removed.".format(name), delete_after=60)
    else:
        await ctx.author.send(content="Could not remove `{}`. Please verify that the name is correct.".format(name))
    if delperm(ctx):
        await ctx.message.delete()


@soundboard.command(aliases=["p"])
async def play(ctx, name):
    # Spila hljóð
    await playFromSoundboard(ctx, name)

    if delperm(ctx):
        await ctx.message.delete()


@soundboard.command(aliases=["rn"])
async def rename(ctx, oldname, newname):
    result = soundBoardDict[hash(ctx.guild)].renameSound(oldname, newname)
    if result == 1:
        await ctx.channel.send(content="Sound `{}` renamed to `{}`.".format(oldname, newname), delete_after=60)
    elif result == -1:
        await ctx.author.send(content="Unknown sound: `{}`. Notice that sound names are case sensitive.".format(oldname))
    elif result == -2:
        await ctx.author.send(content="The sound `{}` already exists.".format(newname))
    else:
        await ctx.author.send(content="Could not rename sound `{}` to `{}` for an unknown reason.".format(oldname, newname))


@professor.command()
async def f(ctx):
    if ctx.guild.id == 672945974586507295:
        with open("fdonos.pkl", "rb") as f:
            db = pickle.load(f)
        db = {k: v for k, v in sorted(db.items(), key=lambda x: x[1], reverse=True)}
        out = ""
        for i in db.items():
            out += "{}: {}\n".format(ctx.guild.get_member(i[0]).display_name, i[1])
        embed = discord.Embed(title="Ammount owed for using f?", description=out, color=accent_colour)

        await ctx.author.send(embed=embed)


# --- Maintenance ---


@professor.command()
async def force_friendly(ctx):
    try:
        if ctx.author.id == 197471216594976768:
            guilds = []

            for guild in professor.guilds:
                guilds.append((guild.name, hash(guild)))

            outmsg = ""
            avail = []
            i = 0
            for guild in guilds:
                outmsg += str(i) + ": " + guild[0] + "\n"
                avail.append(str(i))
                i += 1

            msg = await ctx.author.send(content=outmsg)

            def check(m):
                if ctx.author == m.author:
                    if m.content.lower() == "cancel":
                        raise asyncio.TimeoutError
                    else:
                        return m.content in avail

            rep = await professor.wait_for("message", check=check, timeout=100)

            events = eventsDict[guilds[int(rep.content)][1]].checkIfNotification(force=True)
            i = 0
            for e in events:
                if e:
                    if e["friendly"]:
                        await friendly_notification(e, i)
                        i += 1

    except asyncio.TimeoutError:
        await msg.delete()

@professor.command()
async def announce_update(ctx):
    if ctx.author.id == 197471216594976768:
        for guild in professor.guilds:
            if hash(guild) in eventsDict.keys():
                if eventsDict[hash(guild)].channel is not None:
                    try:
                        msg = await eventsDict[hash(guild)].channel.send(infoMessages["new_update"], delete_after=86400)
                        await msg.pin()
                    except discord.errors.NotFound:
                        pass

@professor.command()
async def test_error(ctx, arg):
    memc = discord.ext.commands.MemberConverter()
    try:
        a = await memc.convert(ctx, arg)
    except discord.ext.commands.BadArgument:
        print("nei")

@professor.command()
async def safe(ctx):
    running = sum([int(a.get_coro().__name__ == "_run_event") for a in asyncio.all_tasks()])
    await ctx.author.send("Ongoing events: {}".format(running))


# Start bot
professor.run(str(key))
