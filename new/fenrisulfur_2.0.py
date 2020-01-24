# TODO:
# - Help msg and command error handle 
# - Fix date padding when updating
import discord
import json
from discord.ext import commands
from urllib import request
import urllib
import asyncio
import random

# Mine
import events
import helper

# Bot key
keyFile = open("key", "r")

key = keyFile.read().strip()
keyFile.close()

# Events dict. Index = guild hash
eventsDict = {}

# Command prefix
prefix = "f? "

# initiate bot
fenrir = commands.Bot(command_prefix = prefix)
fenrir.remove_command("help")

# Load messages
with open("messages.json", "r") as f:
    infoMessages = json.loads(f.read())

# Emotes
leftarrow = "\u2B05"
rightarrow = "\u27A1"

# ==========================================
# Functions
# ==========================================

def isScheduler(user):
    # Check if a user is a scheduler
    if 'Scheduler' in [role.name for role in user.roles]:
        return True
    else:
        return False

def dictFromMembers(members):
    # Generate dictionary with key: member id and value: display name
    out = {}
    for member in members:
        out[member.id] = member.display_name
    return out

async def updatePinned(myChannel, guild):
    # Updates the pinned event list
    guildHash = hash(guild)
    guildMembers = dictFromMembers(guild.members)
    update = eventsDict[guildHash].generateEventsMessage(guildMembers)

    # Find the message
    myMessage = eventsDict[guildHash].myMessage

    # Update the message if it exists, else post new one
    if myMessage == "":
        await myChannel.purge()
        await myChannel.send(content=infoMessages["helloMessage"].format(prefix))
        myMessage = await myChannel.send(content="-", embed=update)
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)
        eventsDict[guildHash].myMessage = myMessage

    else:
        await myMessage.edit(content="-", embed=update)

async def notification(event, color, time, channel, now):
    # Parse eventf? update 7 )
    guildMembers = dictFromMembers(channel.guild.members)
    attendants = []

    for member in event["people"]:
        attendants.append(guildMembers[member])

    if len(attendants) == 0:
        attendants = ["Nobody :("]
    if event["description"] == "":
        event["description"] = "No description yet."

    if now:
        messageTitle = "Event starting now!"
        deleteTime = 60
    else:
        messageTitle = "Event starting in an hour!"
        deleteTime = 3600

    # Generate message
    message = discord.Embed(title = event["name"], description = event["description"], color=color)
    message.add_field(name="When?", value = event["date"])
    message.add_field(name="Party:", value = "\n".join(attendants), inline=False)
    await channel.send(content=messageTitle, embed=message, delete_after=deleteTime)

async def notification_loop():
    await fenrir.wait_until_ready()
    while True:
        await asyncio.sleep(60)
        for guild in fenrir.guilds:
            e = eventsDict[hash(guild)].checkIfNotification()
            if e:
                await notification(e[0], e[1], e[2], e[3], e[4])
                await updatePinned(eventsDict[hash(guild)].channel, guild)

# ==========================================
# Bot events
# ==========================================

@fenrir.event
async def on_ready():
    print("Logged on as {}!".format(fenrir.user))
    # Set activity
    activity = discord.Game(name="with some adventurers in Snowcloak")
    await fenrir.change_presence(activity=activity)

    # Initiate Events class for each guild
    for guild in fenrir.guilds:
        guildHash = hash(guild)

        # Find my channel
        myChannel = ""
        for channel in guild.text_channels:
            if channel.name == "events" and channel.category.name == "Fenrir":
                myChannel = channel
                break

        # If I have a channel, purge and post event list
        if myChannel:
            eventsDict[guildHash] = events.Events(guildHash, myChannel)
            await myChannel.purge()
            await updatePinned(myChannel, guild)
    fenrir.loop.create_task(notification_loop())

@fenrir.event
async def on_command_completion(ctx):
    # List of commands for events
    eventCommands = ["attend", "leave", "schedule", "remove", "update"]

    guildHash = hash(ctx.guild)
    members = ctx.guild.members

    # Update pinned list if command is for event
    if ctx.command.name in eventCommands:
        await updatePinned(eventsDict[guildHash].channel, ctx.guild)

@fenrir.event
async def on_message(message):
    # Process command and then delete the message if it wasn't a command in events channel
    a = await fenrir.process_commands(message)
    if message.channel == eventsDict[hash(message.guild)].channel and message.author != fenrir.user:
        await message.delete()

@fenrir.event
async def on_reaction_add(react, user):
    # Process pages
    guild = react.message.guild

    # If react to me and was someone else
    if react.me and user != fenrir.user:
        # Page down if left arrow
        if react.emoji == leftarrow:
            if eventsDict[hash(guild)].page > 1:
                eventsDict[hash(guild)].page -= 1
            await updatePinned(eventsDict[hash(guild)].channel, guild)
            await react.remove(user)

        # Page up if rightarrow
        elif react.emoji == rightarrow:
            eventsDict[hash(guild)].page += 1
            await updatePinned(eventsDict[hash(guild)].channel, guild)
            await react.remove(user)


# ==========================================
# Bot commands
# ==========================================


# --- Setup and stuff ---

@fenrir.command()
async def setup(ctx):
    # Create events channel in fenrir category
    # Initiate Events class for guild

    # Check if server owner is seting up
    if ctx.author == ctx.guild.owner:
        # Delete message
        await ctx.message.delete()

        # Create category and channel
        category = await ctx.guild.create_category("Fenrir")
        channel = await ctx.guild.create_text_channel("events", category=category)

        await channel.send(content=infoMessages["helloMessage"].format(prefix))

        # Create scheduler rank and let owner know
        await ctx.guild.create_role(name="Scheduler")
        await ctx.author.send(content=infoMessages["schedulerMessage"])

        # Initiate Events class
        eventsDict[hash(ctx.guild)] = events.Events(hash(ctx.guild), channel)

        # Update pinned
        await updatePinned(channel, ctx.guild)

# --- Events ---

@fenrir.command()
async def schedule(ctx, *args):
    # Schedule an event
    # command syntax: schedule [date] [name]

    # Check if user is scheduler
    if isScheduler(ctx.author):

        # Check if there are enough args
        enoughArgs = True
        if len(args) < 2:
            enoughArgs = False

        # Check if event is yet to be dated
        if "TBD" in args:
            eventDate = args[0]
            eventName = " ".join(args[1:])
        elif enoughArgs:
            eventDate = args[0] + " " + args[1]
            eventName = " ".join(args[2:])

        # Check if enough args to create event and if creation was successful
        if enoughArgs and eventsDict[hash(ctx.guild)].createEvent(eventDate, eventName):
            await ctx.channel.send(content=infoMessages["eventCreated"].format(eventName, eventDate), delete_after=15)
        else:
            await ctx.channel.send(content=infoMessages["eventCreationFailed"].format(prefix), delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])

@fenrir.command()
async def remove(ctx, *args):
    # Remove an event
    # command syntax: remove [eventId]

    # Check if user is scheduler
    if isScheduler(ctx.author):
        guildHash = hash(ctx.guild)

        # Get actual event id
        eventId = eventsDict[guildHash].getEventId(args[0])

        # Check if event id was found and if removal successful
        if eventId and eventsDict[guildHash].removeEvent(eventId):
            await ctx.channel.send(content=infoMessages["eventRemoved"], delete_after=15)
        else:
            await ctx.channel.send(content=infoMessages["eventRemovalFailed"].format(prefix), delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])

@fenrir.command()
async def attend(ctx, *, eventId):
    # Attend an event
    # Command syntax: attend [eventId]
    authorName = ctx.author.display_name

    # Attend event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, True):
        await ctx.channel.send(content=infoMessages["attendSuccess"].format(authorName, eventId), delete_after=15)
    else:
        await ctx.channel.send(content=infoMessages["attendFailed"].format(prefix), delete_after=15)

@fenrir.command()
async def leave(ctx, *, eventId):
    # Leave an event
    # Command syntax: leave [eventId]
    authorName = ctx.author.display_name

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, False):
        await ctx.channel.send(content=infoMessages["leaveSuccess"].format(authorName, eventId), delete_after=15)
    else:
        await ctx.channel.send(content=infoMessages["leaveFailed"].format(prefix), delete_after=15)

@fenrir.command()
async def update(ctx, eventId, toUpdate, *, newInfo):
    # Updates eventId description or name to newInfo
    # Command syntax: update [eventId] [to update] [new info]

    # Check if usere is scheduler
    if isScheduler(ctx.author):
        if toUpdate == "description" or toUpdate == "name" or toUpdate == "date":
            if eventsDict[hash(ctx.guild)].updateEvent(eventId, toUpdate, newInfo):
                await ctx.channel.send(content=infoMessages["updateSuccess"].format(eventId, toUpdate, newInfo), delete_after=15)
            else:
                await ctx.channel.send(content=infoMessages["updateFailed"].format(prefix), delete_after=15)
        else:
            await ctx.channel.send(content=infoMessages["invalidUpdateField"], delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])

# --- Misc ---

@fenrir.command()
async def eyebleach(ctx):
    success = False
    while not success:
        try:
            a = request.urlopen("https://www.reddit.com/r/Eyebleach/top/.json?t=day")
            success = True
        except urllib.error.HTTPError:
            success = False
        await asyncio.sleep(1)
    a = json.loads(a.read())
    ind = random.randint(0,len(a["data"]["children"]))
    link = a["data"]["children"][ind]["data"]["url"]
    await ctx.channel.send(content=link)

@fenrir.command()
async def help(ctx, *, cmd="none"):
    message = helper.helpCmd(prefix, cmd)
    if message != -1:
        await ctx.author.send(embed=message)
    else:
        await ctx.author.send(content="Unrecognised command")

# Start bot
fenrir.run(str(key))
