import discord
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
from PIL import Image

# Mine
import events
import helper
import salt.salty as salty
import soundb
import permissions


# Bot key
keyFile = open(sys.argv[1], "r")

key = keyFile.read().strip()
keyFile.close()

# Events dict. Index = guild hash
eventsDict = {}

# Soundboard dict. Index = guild hash
soundBoardDict = {}

# Permissions dict. Index = guild hash
permissionsDict = {}

# Command prefix
prefixes = ["f? ", "f?", "p? ", "p?"]
prefix = "p? "

# Load messages
with open("messages.json", "r") as f:
    infoMessages = json.loads(f.read())

# Activity
activity = discord.Game(infoMessages["activity"])

# initiate bot
professor = commands.Bot(case_insensitive=True,
                         command_prefix=prefixes,
                         activity=activity)

professor.remove_command("help")

# Emotes
leftarrow = "\u2B05\uFE0F"
rightarrow = "\u27A1\uFE0F"

party = "\U0001F389"
calculator = "\U0001F5A9"

# Color
accent_colour = discord.Colour(int("688F56", 16))

# Salt initialisation
saltWraper = salty.saltClass()

everyone = "@everyone"

# event check loop
eventCheckerLoop = None

# Reddit
with open("reddit", "r") as f:
    r_id = f.readline().strip()
    r_secret = f.readline().strip()
    r_ua = f.readline().strip()

    reddit = praw.Reddit(client_id=r_id,
                         client_secret=r_secret,
                         user_agent=r_ua)

# Wolfram
with open("wolfram", "r") as f:
    wa_app_id = f.readline().strip()
    wolf = wolframalpha.Client(wa_app_id)


# dummy parameter for discord.ext.commands.errors.MissingRequiredArgumentError
class dummyparam:
    def __init__(self, name):
        self.name = name

# ==========================================
# Functions
# ==========================================


@professor.check
async def permissioncheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        check = permissionsDict[hash(ctx.guild)].hasPermission(ctx)
        if not check:
            await ctx.author.send(content="You do not have permission to do execute the command `{}`.".format(ctx.message.content))
    else:
        return True

    return check


def delperm(ctx):
    return ctx.channel.permissions_for(ctx.guild.me).manage_messages


async def notEventChannelCheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        if hash(ctx.guild) in eventsDict.keys():
            return ctx.channel.id != eventsDict[hash(ctx.guild)].getMyChannelId("events")
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

    def dform(d):
        d = datetime.strptime(d, "%m/%d/%y %H:%M:%S")
        return "`" + datetime.strftime(d, "%a. %H:%M") + "`"

    # Updates the pinned event list
    guildHash = hash(guild)
    guildMembers = dictFromMembersName(guild.members)
    update = eventsDict[guildHash].generateEventsMessage(guildMembers)

    mylog = eventsDict[guildHash].getLog()
    mylog = [dform(u) + "\t" + v for u, v in mylog][-3:]

    if mylog:
        mylog[0] = ">>> " + mylog[0]
    else:
        mylog = [">>> The log is empty"]

    # Find the message
    myMessageId = eventsDict[guildHash].myMessageId
    myLogMessageId = eventsDict[guildHash].myLogMessageId

    # Get my nick
    nick = guild.me.display_name

    # Update the message if it exists, else post new one
    try:
        myMessage = await myChannel.fetch_message(myMessageId)
        await myMessage.edit(content="Notice: all times are in GMT", embed=update)
        myLogMessage = await myChannel.fetch_message(myLogMessageId)
        await myLogMessage.edit(content="\n".join(mylog))
        await myLogMessage.clear_reactions()

    except (discord.errors.HTTPException, discord.errors.NotFound):
        await myChannel.purge()
        helloMessage = await myChannel.send(content=infoMessages["helloMessage"].format(nick, prefix))
        myMessage = await myChannel.send(content="Notice: all times are in GMT", embed=update)
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


async def friendly_notification(e):
    # Friendly reminder for recurring events
    eventName = e["event"]["name"]
    eventDesc = e["event"]["description"]
    weekday = e["date"]

    # Find my friendly channel
    channelId = e["channelId"]
    guild = e["guild"]

    # everyone = guild.me.roles[0].mention

    friendlyChannel = guild.get_channel(channelId)

    msgContent = "Today is \"{} {}\". \n {} \n Remember to sign up in the events channel!".format(eventName, weekday, eventDesc)

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
    for member in event["people"]:
        attendants.append(str(event["rolesdict"][member]) + " " + str(guildMembers[member].display_name))

        if eventRole != 0:
            await guildMembers[member].add_roles(eventRole)

    if len(attendants) == 0:
        attendants = ["Nobody :("]
    if event["description"] == "":
        event["description"] = "No description yet."

    if now:
        messageTitle = mention + " Event starting now!"
        deleteTime = 600
    else:
        messageTitle = mention + " Event starting in an hour!"
        deleteTime = 3600

    # Generate message
    if (event["limit"] != 0):
        limitstr = "({}/{})".format(len(event["people"]), event["limit"])
    else:
        limitstr = "({})".format(str(len(event["people"])))
    message = discord.Embed(title=event["name"], description=event["description"], color=color)
    message.add_field(name="When?", value=event["date"])
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
            for e in eventOut:
                # If there is a notification, send it and update events list
                try:
                    if e["friendly"]:
                        await friendly_notification(e)
                    else:
                        await updatePinned(eventsDict[hash(guild)].channel, guild)
                        await event_notification(e)
                except:
                    continue

# ==========================================
# Bot events
# ==========================================


@professor.event
async def on_ready():
    global eventCheckerLoop
    print("User:\t\t\t{}".format(professor.user))
    # Set activity
    print("Activity:\t\t{}".format(activity))
    print()

    # Initiate Events class for each guild
    for guild in professor.guilds:
        guildHash = hash(guild)
        print("Guild:\t\t\t{}".format(guildHash))

        eventsDict[guildHash] = events.Events(guildHash)
        soundBoardDict[guildHash] = soundb.SoundBoard(guildHash)

        # Find my channel
        myChannelId = eventsDict[guildHash].getMyChannelId("events")
        if myChannelId != 0:
            myChannel = guild.get_channel(myChannelId)
        else:
            myChannel = None

        def purgecheck(m):
            return not m.pinned

        # If I have a channel, purge and post event list
        if myChannel:
            eventsDict[guildHash].channel = myChannel
            await myChannel.purge(check=purgecheck)
            await updatePinned(myChannel, guild)

        # Initiate permissions
        permissionsDict[hash(guild)] = permissions.Permissions(hash(guild))

        print()
    if eventCheckerLoop not in asyncio.all_tasks():
        print("Starting event checking loop")
        eventCheckerLoop = professor.loop.create_task(notification_loop())


@professor.event
async def on_command_completion(ctx):
    # List of commands for events
    if ctx.guild:
        eventCommands = ["attend", "leave", "schedule", "remove", "update", "kick"]

        guildHash = hash(ctx.guild)

        # Update pinned list if command is for event
        if ctx.command.name in eventCommands and guildHash in eventsDict.keys():
            await updatePinned(eventsDict[guildHash].channel, ctx.guild)


@professor.event
async def on_message(message):
    # Process command and then delete the message if it wasn't a command in events channel
    await professor.process_commands(message)

    # Check if we are in dm
    guildMessage = isinstance(message.channel, discord.abc.GuildChannel)
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
    eventsDict[hash(guild)] = events.Events(hash(guild), None)
    soundBoardDict[hash(guild)] = soundb.SoundBoard(hash(guild))
    permissionsDict[hash(guild)] = permissions.Permissions(hash(guild))
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

@professor.group(aliases=["config", "conf"])
async def configure(ctx):
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
    availablePerms = ["es", "er", "eu", "ek", "sa", "sr", "cc", "cr"]
    rolePerms = permissionsDict[hash(ctx.guild)].getPermissions(role.id)

    with open("foodemojis.txt", "r") as f:
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

        # Categorize the permissions and check their values
        for p in permissions.permissionResolver.values():
            commandName = permissions.resolvePermission(p).split()[-1]
            if p[0] == "e":
                eventsPermissions[commandName] = p in rolePerms
            elif p[0] == "s":
                soundboardPermissions[commandName] = p in rolePerms
            elif p[0] == "c":
                configurePermissions[commandName] = p in rolePerms

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


# --- Events ---


@professor.command(aliases=["s"], checks=[eventChannelCheck])
async def schedule(ctx):
    channel = ctx.channel
    author = ctx.author

    def check(m):
        if m.content.lower() == "cancel":
            raise asyncio.TimeoutError
        return m.channel == channel and m.author == author

    def pcheck(m):
        return not m.pinned
    if eventsDict[hash(ctx.guild)].scheduling > 0:
        await ctx.author.send(content="Someone else is scheduling an event. Please wait until they are done.")
        return
    try:
        # Announce that we are scheduling
        eventsDict[hash(ctx.guild)].scheduling += 1

        emb = discord.Embed(title="Title ", description="Time: \n Description:")

        startEvent = await channel.send(content="Scheduling started. Type `cancel` to cancel", embed=emb)

        # Title
        msg = await channel.send(content=infoMessages["eventTitle"])
        replyMsg = await professor.wait_for("message", check=check, timeout=120)

        title = replyMsg.content

        await replyMsg.delete()

        emb.title = title
        await startEvent.edit(embed=emb)

        # Time
        await msg.edit(content=infoMessages["eventTime"])
        replyMsg = await professor.wait_for("message", check=check, timeout=120)

        # Check if time is ok
        timeOk = eventsDict[hash(ctx.guild)].dateFormat(replyMsg.content)
        while timeOk is False:
            await replyMsg.delete()
            await channel.send(content=infoMessages["invalidDate"].format(replyMsg.content), delete_after=5)
            replyMsg = await professor.wait_for("message", check=check, timeout=120)
            timeOk = eventsDict[hash(ctx.guild)].dateFormat(replyMsg.content)

        time = replyMsg.content
        await replyMsg.delete()

        emb.description = "Time: {} \n Description:".format(time)
        await startEvent.edit(embed=emb)

        # Desc
        await msg.edit(content=infoMessages["eventDesc"])
        replyMsg = await professor.wait_for("message", check=check, timeout=120)

        desc = replyMsg.content

        await replyMsg.delete()

        emb.description = "Time: {} \n Description: {}".format(time, desc)
        await startEvent.edit(embed=emb)

        # Roles
        await msg.edit(content="React to this message with any event specific roles. Type `done` when done.")

        def donecheck(m):
            return check(m) and m.content.lower() == "done"

        replyMsg = await professor.wait_for("message", check=donecheck, timeout=120)
        await replyMsg.delete()
        emojis = []
        reactionNameMsg = await ctx.channel.send(content="-")

        msg = await ctx.channel.fetch_message(msg.id)

        def checklimit(m):
            try:
                int(m.content)
                out = check(m)
                return out
            except ValueError:
                return False

        for reaction in msg.reactions:
            await reactionNameMsg.edit(content="Please enter a name for {}".format(str(reaction)))
            nameRep = await professor.wait_for("message", check=check, timeout=120)
            name = nameRep.content
            await nameRep.delete()

            await reactionNameMsg.edit(content="Please enter the limit of people for {} (0 for no limit).".format(str(reaction)))
            limitRep = await professor.wait_for("message", check=checklimit, timeout=120)
            limit = int(limitRep.content)
            await limitRep.delete()

            emojis.append((str(reaction), name, limit))

        await reactionNameMsg.delete()
        await msg.clear_reactions()

        # Total limit
        await msg.edit(content="Please enter the total limit of people who can join the event (0 for no limit).")
        limitRep = await professor.wait_for("message", check=checklimit, timeout=120)
        limit = int(limitRep.content)
        await limitRep.delete()

        # Delete temp messages
        await msg.delete()
        await startEvent.delete()

        # Schedule events
        if eventsDict[hash(ctx.guild)].createEvent(time, title, desc, emojis, limit):
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
            eventsDict[hash(ctx.guild)].insertIntoLog("{} scheduled event `{}` for `{}`.".format(ctx.author.display_name, title, time))
        else:
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
            await ctx.channel.send(content=infoMessages["eventCreationFailed"].format(prefix), delete_after=15)
        eventsDict[hash(ctx.guild)].scheduling -= 1
    except asyncio.TimeoutError:
        if ctx.channel == eventsDict[hash(ctx.guild)].channel:
            await ctx.channel.purge(check=pcheck)

        eventsDict[hash(ctx.guild)].scheduling -= 1


@professor.command(aliases=["r"], checks=[eventChannelCheck])
async def remove(ctx, fakeId):
    # Remove an event
    # command syntax: remove [eventId]

    guildHash = hash(ctx.guild)

    event = eventsDict[guildHash].getEvent(fakeId)

    # Get actual event id
    eventId = eventsDict[guildHash].getEventId(fakeId)

    # Check if event id was found and if removal successful
    if eventId and eventsDict[guildHash].removeEvent(eventId):
        eventsDict[hash(ctx.guild)].insertIntoLog("{} removed event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.author.send(content=infoMessages["eventRemovalFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["a"], checks=[eventChannelCheck])
async def attend(ctx, eventId):
    # Attend an event
    # Command syntax: attend [eventId]
    role = ""

    emojis = []

    def check(payload):
        return payload.member == ctx.author and str(payload.emoji) in emojis

    # Fetch event
    event = eventsDict[hash(ctx.guild)].getEvent(eventId)

    # Check if event is full
    if len(event["people"]) >= event["limit"] and event["limit"] != 0:
        await ctx.channel.send(content="That event is already full!", delete_after=15)
        return

    # Get event roles
    if event["roles"] != []:
        try:
            for role in event["roles"]:
                if event["rolelimits"][role[0]] >= role[2] and role[2] != 0:
                    continue
                emojis.append(role[0])
            if len(emojis) == 0:
                role = ""
            else:
                rolelist = []
                for u, v, z in event["roles"]:
                    limitString = " ({}/{})".format(event["rolelimits"][u], z) if z != 0 else ""
                    rolelist.append(u + ": " + v + limitString)

                rolelist = "\n".join(rolelist)

                reactMsg = await ctx.channel.fetch_message(eventsDict[hash(ctx.guild)].myLogMessageId)
                await reactMsg.edit(content="Please pick a role by reacting to this message:\n{}".format(rolelist))
                for emoji in emojis:
                    await reactMsg.add_reaction(emoji)
                payload = await professor.wait_for("raw_reaction_add", check=check, timeout=60)
                # await reactMsg.delete()
                role = str(payload.emoji)
        except asyncio.TimeoutError:
            def pcheck(m):
                return not m.pinned
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)
                return

    # Attend event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, True, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        eventsDict[hash(ctx.guild)].insertIntoLog("{} joined event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.author.send(content=infoMessages["attendFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["l"], checks=[eventChannelCheck])
async def leave(ctx, eventId):
    # Leave an event
    # Command syntax: leave [eventId]

    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    try:
        role = event["rolesdict"][ctx.author.id]
    except KeyError:
        role = ""

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, False, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        eventsDict[hash(ctx.guild)].insertIntoLog("{} left event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.author.send(content=infoMessages["leaveFailed"].format(prefix), delete_after=15)


@professor.command(aliases=["u"], checks=[eventChannelCheck])
async def update(ctx, eventId, toUpdate, *, newInfo):
    # Updates eventId description or name to newInfo
    # Command syntax: update [eventId] [to update] [new info]

    # Check if usere is scheduler
    if toUpdate == "description" or toUpdate == "name" or toUpdate == "date" or ctx.author.id == 197471216594976768:
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        if eventsDict[hash(ctx.guild)].updateEvent(eventId, toUpdate, newInfo):
            eventsDict[hash(ctx.guild)].insertIntoLog("{} updated event `{}`'s `{}` from `{}` to `{}`.".format(ctx.author.display_name, event["name"], toUpdate, event[toUpdate], newInfo))

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
        role = event["rolesdict"][uid]
    except KeyError:
        role = ""

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, uid, False, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)
        eventsDict[hash(ctx.guild)].insertIntoLog("{} kicked {} from `{}`.".format(ctx.author.display_name, userToKick.display_name, event["name"]))
    else:
        await ctx.author.send(content="I could not kick {} from `{}`".format(userToKick.display_name, event["name"]))


# --- Misc ---


@professor.command(checks=[notEventChannelCheck], aliases=["cute", "cutestuff", "helppls", "pleasehelp"])
async def eyebleach(ctx):
    subreddit = reddit.subreddit("eyebleach")

    out = []
    ok_extensions = ["png", "gif", "jpg", "jpeg"]

    for submission in subreddit.hot(limit=15):
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
    await ctx.channel.send(content="From /r/eyebleach:\n{}\n{}".format(pick[0], pick[1]))
    # embed = discord.Embed(title=pick[0], url=pick[1], color=discord.Color.blue())
    # embed.set_image(url=pick[1])
    # embed.set_footer(text="from /r/eyebleach")
    # await ctx.channel.send(content="From https://reddit.com/r/eyebleach", embed=embed)


@professor.command()
async def help(ctx, *, cmd="none"):
    message = helper.helpCmd(prefix, cmd)
    if message != -1:
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
        await ctx.channel.purge()
    else:
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


# --- Salt ---


@professor.command(checks=[notEventChannelCheck])
async def salt(ctx):
    # Get a random nugg and increment count
    username = ctx.author.display_name
    insultMessage = saltWraper.insult(username)
    count = saltWraper.eatCookie(ctx.author)

    await ctx.send("Here is your little nugget of salt:\n{}".format(insultMessage))
    await asyncio.sleep(1)
    await ctx.send("{} has now had {} salty nuggs!".format(username, count))


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


@professor.group(checks=[notEventChannelCheck])
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


@chill.command(aliases=["v"])
async def volume(ctx, v):
    await ctx.message.delete()
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

# --- Log ---


@professor.command()
async def log(ctx):
    log = eventsDict[hash(ctx.guild)].getLog()
    embed = discord.Embed(title="Activity log", color=accent_colour)

    for e in log:
        embed.add_field(name=e[0], value=e[1], inline=False)

    await ctx.author.send(embed=embed, delete_after=300)

    if delperm(ctx):
        await ctx.message.delete()

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
                outmsg += str(i) + ": " + guild[0]
                avail.append(str(i))
                i += 1

            msg = await ctx.author.send(content=outmsg)

            def check(m):
                return ctx.author == m.author and m.content in avail

            rep = await professor.wait_for("message", check=check, timeout=100)

            e = eventsDict[guilds[int(rep.content)][1]].checkIfNotification(force=True)
            if e:
                if e["friendly"]:
                    await friendly_notification(e)

    except asyncio.TimeoutError:
        await msg.delete()


@professor.command()
async def readycheck(ctx, *args):
    # Emojis
    checkmark = "\u2705"
    cross = "\u274C"
    wait = "\U0001F552"

    users = []
    if len(args) == 0:
        raise discord.ext.commands.errors.MissingRequiredArgument(dummyparam("mentions"))

    usingRole = True

    # Convert arguments to members or role
    try:
        # Try to convert to members
        memconv = discord.ext.commands.MemberConverter()
        for user in args:
            users.append(await memconv.convert(ctx, user))
        usingRole = False

    except discord.ext.commands.CommandError:
        # If args are not members, try to convert to a role
        roleconv = discord.ext.commands.RoleConverter()
        role = await roleconv.convert(ctx, args[0])
        users = role.members

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
            payload = await professor.wait_for("raw_reaction_add", check=check, timeout=86400)
        except asyncio.TimeoutError:
            # After 24h timeout and try to delete the readycheck
            try:
                await readyCheckMsg.delete()
            except discord.errors.NotFound:
                return

        # Set the status of the member who reacted to the emoji reacted with
        userDict[payload.member] = payload.emoji.name

        # Update message
        await readyCheckMsg.edit(embed=outmsg())

        # Count how many members are ready
        count = 0
        for emoji in userDict.values():
            if emoji == checkmark:
                count += 1

    # Delete command and readycheck list and let people know everyone is ready
    if delperm(ctx):
        await readyCheckMsg.delete()
        await ctx.message.delete()

    if not usingRole:
        mentionstr = ""
        for user in users:
            mentionstr = mentionstr + user.mention + " "
    else:
        mentionstr = role.mention

    await ctx.channel.send(content=mentionstr + "\n Everyone is ready")


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
                await asyncio.sleep(0.3)
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
    with open("foodemojis.txt", "r") as f:
        emojis_avail = f.read().splitlines()

    random.shuffle(emojis_avail)

    # Cancel emoji
    x = "\U0000274C"
    emoji_dict = {}

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in (list(emoji_dict.keys()) + [x])

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


# Start bot
professor.run(str(key))
