import discord
import json
from discord.ext import commands
from urllib import request
import urllib
import asyncio
import random
import sys

# Mine
import events
import helper
import salt.salty as salty


# Bot key
keyFile = open(sys.argv[1], "r")

key = keyFile.read().strip()
keyFile.close()

# Events dict. Index = guild hash
eventsDict = {}

# Command prefix
prefix = "f? "

# Load messages
with open("messages.json", "r") as f:
    infoMessages = json.loads(f.read())

# Activity
activity = discord.Game(infoMessages["activity"])

# initiate bot
professor = commands.Bot(command_prefix = prefix, activity=activity)
professor.remove_command("help")
professor.case_insensitive = True

# Emotes
leftarrow = "\u2B05\uFE0F"
rightarrow = "\u27A1\uFE0F"
party = "\U0001F389"
calculator = "\U0001F5A9"

# Salt initialisation
saltWraper = salty.saltClass()

everyone = "@everyone"

# event check loop
eventCheckerLoop = None

# ==========================================
# Functions
# ==========================================

def isScheduler(user):
    # Check if a user is a scheduler
    if 'Scheduler' in [role.name for role in user.roles]:
        return True
    else:
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
    # Updates the pinned event list
    guildHash = hash(guild)
    guildMembers = dictFromMembersName(guild.members)
    update = eventsDict[guildHash].generateEventsMessage(guildMembers)

    # Find the message
    myMessage = eventsDict[guildHash].myMessage

    # Get my nick
    nick = guild.me.display_name

    # Update the message if it exists, else post new one
    try:
        await myMessage.edit(content="-", embed=update)
    except:
        await myChannel.purge()
        await myChannel.send(content=infoMessages["helloMessage"].format(nick, prefix))
        myMessage = await myChannel.send(content="-", embed=update)
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)
        eventsDict[guildHash].myMessage = myMessage

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

    msgContent = "Today is \"{} {}\". \n {} \n Remember to sign up in the events channel!.".format(eventName, weekday, eventDesc)

    await friendlyChannel.send(content=msgContent)

async def event_notification(e):
    # Parse event
    event = e["event"]
    date = e["date"]
    channel = e["channel"]
    color = e["color"]
    now = e["now"]

    # everyone = channel.guild.me.roles[0].mention

    guildMembers = dictFromMembers(channel.guild.members)
    attendants = []

    # Create event role
    eventRole = await channel.guild.create_role(name="event", mentionable=True)
    mention = eventRole.mention

    # Get names of attendants and give them the event role
    for member in event["people"]:
        attendants.append(guildMembers[member].display_name)
        await guildMembers[member].add_roles(eventRole)

    if len(attendants) == 0:
        attendants = ["Nobody :("]
    if event["description"] == "":
        event["description"] = "No description yet."

    if now:
        messageTitle = mention + " Event starting now!"
        deleteTime = 60
    else:
        messageTitle = mention + " Event starting in an hour!"
        deleteTime = 3600

    # Generate message
    message = discord.Embed(title = event["name"], description = event["description"], color=color)
    message.add_field(name="When?", value = event["date"])
    message.add_field(name="Party:", value = "\n".join(attendants), inline=False)
    await channel.send(content=messageTitle, embed=message, delete_after=deleteTime)
    await eventRole.delete()

async def notification_loop():
    # Wait until bot is ready
    await professor.wait_until_ready()
    while True:
        # Check every 60s
        await asyncio.sleep(60)
        for guild in professor.guilds:
            # Check every guild for notifications
            e = eventsDict[hash(guild)].checkIfNotification()
            if e:
                # If there is a notification, send it and update events list
                if e["friendly"]:
                    await friendly_notification(e)
                else:
                    await updatePinned(eventsDict[hash(guild)].channel, guild)
                    await event_notification(e)

# ==========================================
# Bot events
# ==========================================

@professor.event
async def on_ready():
    global eventCheckerLoop
    print("User:\t\t\t{}".format(professor.user))
    # Set activity
    print("Activity:\t\t{}".format(activity))

    # Initiate Events class for each guild
    for guild in professor.guilds:
        guildHash = hash(guild)

        eventsDict[guildHash] = events.Events(guildHash, None)

        # Find my channel
        myChannelId = eventsDict[guildHash].getMyChannelId("events")
        myChannel = guild.get_channel(myChannelId)

        print("Cid:\t\t\t{}".format(myChannelId))

        # If I have a channel, purge and post event list
        if myChannel:
            eventsDict[guildHash].channel = myChannel
            await myChannel.purge()
            await updatePinned(myChannel, guild)
    print()
    if not eventCheckerLoop in asyncio.all_tasks():
        print("Starting event checking loop")
        eventCheckerLoop = professor.loop.create_task(notification_loop())

@professor.event
async def on_command_completion(ctx):
    # List of commands for events
    if ctx.guild:
        eventCommands = ["attend", "leave", "schedule", "remove", "update"]

        guildHash = hash(ctx.guild)
        members = ctx.guild.members

        # Update pinned list if command is for event
        if ctx.command.name in eventCommands:
            await updatePinned(eventsDict[guildHash].channel, ctx.guild)

@professor.event
async def on_command_error(ctx, error):
    # Send user an error message when command throws an error.
    print(error)
    print(ctx.message.content)

    await ctx.author.send(content=infoMessages["commandError"].format(ctx.message.content))

@professor.event
async def on_message(message):
    # Process command and then delete the message if it wasn't a command in events channel
    a = await professor.process_commands(message)

    # Check if we are in dm
    guildMessage = isinstance(message.channel, discord.abc.GuildChannel)
    if guildMessage \
            and message.channel == eventsDict[hash(message.guild)].channel \
            and message.author != professor.user \
            and eventsDict[hash(message.guild)].scheduling == 0:
            await message.delete()

@professor.event
async def on_reaction_add(react, user):
    # Process pages
    guild = react.message.guild

    # If react to me and was someone else
    if react.me and user != professor.user:
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

@professor.event
async def on_guild_join(guild):
    # Print setup message in first text channel we can
    for i in guild.text_channels:
        try:
            await i.send(content="Type `" +prefix+ "setup` to get started")
            break
        except discord.errors.Forbidden:
            pass
    eventsDict[hash(guild)] = events.Events(hash(guild), None)

# ==========================================
# Bot commands
# ==========================================


# --- Setup and stuff ---

@professor.command()
async def setup(ctx):
    # Create events channel in professor category
    # Initiate Events class for guild

    # Check if server owner is seting up
    if ctx.author == ctx.guild.owner:
        # Delete message
        await ctx.message.delete()

        # Get nickname
        nick = ctx.guild.me.display_name

        # Create category and channel
        category = await ctx.guild.create_category("Events")
        channel = await ctx.guild.create_text_channel("events", category=category)

        await channel.send(content=infoMessages["helloMessage"].format(nick, prefix))

        # Create scheduler rank and let owner know
        await ctx.guild.create_role(name="Scheduler")
        await ctx.author.send(content=infoMessages["schedulerMessage"])

        # Initiate Events class
        eventsDict[hash(ctx.guild)].setMyChannelId(channel.id, "events")

        # Update pinned
        await updatePinned(channel, ctx.guild)

@professor.command()
async def setChannel(ctx, channelType):
    if channelType not in ["events", "friendly"]:
        await ctx.message.delete()
        await ctx.author.send(content="{} is not a valid channel type.".format(channelType))
        return

    if ctx.author == ctx.guild.owner or ctx.author.id == "197471216594976768":
        eventsDict[hash(ctx.guild)].setMyChannelId(ctx.channel.id, channelType)

        def check(m):
            return (m.content == "yes" or m.content == "no") and m.channel == ctx.channel and m.author == ctx.author

        if (channelType == "events"):
            confirmMsg = await ctx.channel.send(content=infoMessages["confirmEventsChannel"])
            confirmReply = await professor.wait_for("message", check = check)
            confirm = confirmReply.content == "yes"

            if confirm:
                eventsDict[hash(ctx.guild)].channel = ctx.channel
                eventsDict[hash(ctx.guild)].myMessage = None
                await updatePinned(ctx.channel, ctx.guild)
            else:
                await confirmMsg.delete()
                await confirmReply.delete()
        else:
            await ctx.message.delete()
            await ctx.channel.send(content="Channel registered as {}".format(channelType), delete_after=20)

# --- Events ---

@professor.command(aliases=["s"])
async def schedule(ctx):
    channel = ctx.channel
    author = ctx.author

    def check(m):
        return m.channel == channel and m.author == author
    def cancelCheck(m):
        if m.lower() == "cancel":
            raise asyncio.TimeoutError

    if isScheduler(author):
        try:
            # Announce that we are scheduling
            eventsDict[hash(ctx.guild)].scheduling += 1

            emb = discord.Embed(title="Title ", description="Time: \n Description:")

            startEvent = await channel.send(content="Scheduling started. Type `cancel` to cancel", embed=emb)

            # Title
            msg = await channel.send(content=infoMessages["eventTitle"])
            replyMsg = await professor.wait_for("message", check=check, timeout=120)

            title = replyMsg.content
            cancelCheck(title)

            await replyMsg.delete()

            emb.title = title
            await startEvent.edit(embed=emb)

            # Time
            await msg.edit(content=infoMessages["eventTime"])
            replyMsg = await professor.wait_for("message", check=check, timeout=120)

            cancelCheck(replyMsg.content)

            # Check if time is ok
            timeOk = eventsDict[hash(ctx.guild)].dateFormat(replyMsg.content)
            while timeOk == False:
                await replyMsg.delete()
                await channel.send(content=infoMessages["invalidDate"].format(replyMsg.content), delete_after=5)
                replyMsg = await professor.wait_for("message", check=check, timeout=120)
                cancelCheck(replyMsg.content)
                timeOk = eventsDict[hash(ctx.guild)].dateFormat(replyMsg.content)

            time = replyMsg.content
            await replyMsg.delete()

            emb.description = "Time: {} \n Description:".format(time)
            await startEvent.edit(embed=emb)

            # Desc
            await msg.edit(content=infoMessages["eventDesc"])
            replyMsg = await professor.wait_for("message", check=check, timeout=120)

            desc = replyMsg.content
            cancelCheck(desc)

            await replyMsg.delete()

            emb.description = "Time: {} \n Description: {}".format(time, desc)
            await startEvent.edit(embed=emb)

            # Delete temp messages
            await msg.delete()
            await startEvent.delete()

            # Schedule events
            if eventsDict[hash(ctx.guild)].createEvent(time, title, desc):
                await ctx.channel.send(content=infoMessages["eventCreated"].format(title, time), delete_after=15)
                eventsDict[hash(ctx.guild)].insertIntoLog("{} scheduled event `{}` for `{}`.".format(ctx.author.display_name, title, time))
            else:
                await ctx.channel.send(content=infoMessages["eventCreationFailed"].format(prefix), delete_after=15)
            eventsDict[hash(ctx.guild)].scheduling -= 1
        except asyncio.TimeoutError:
            eventsDict[hash(ctx.guild)].scheduling -= 1
            await msg.delete()
            await startEvent.delete()
            await replyMsg.delete()
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])


@professor.command(aliases=["r"])
async def remove(ctx, *args):
    # Remove an event
    # command syntax: remove [eventId]

    # Check if user is scheduler
    if isScheduler(ctx.author):
        guildHash = hash(ctx.guild)

        event = eventsDict[guildHash].getEvent(args[0])

        # Get actual event id
        eventId = eventsDict[guildHash].getEventId(args[0])

        # Check if event id was found and if removal successful
        if eventId and eventsDict[guildHash].removeEvent(eventId):
            await ctx.channel.send(content=infoMessages["eventRemoved"].format(event["name"]), delete_after=15)
            eventsDict[hash(ctx.guild)].insertIntoLog("{} removed event `{}`.".format(ctx.author.display_name, event["name"]))
        else:
            await ctx.channel.send(content=infoMessages["eventRemovalFailed"].format(prefix), delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])

@professor.command(aliases = ["a"])
async def attend(ctx, *, eventId):
    # Attend an event
    # Command syntax: attend [eventId]
    authorName = ctx.author.display_name

    # Attend event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, True):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        await ctx.channel.send(content=infoMessages["attendSuccess"].format(authorName, event["name"]), delete_after=15)
        eventsDict[hash(ctx.guild)].insertIntoLog("{} joined event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.channel.send(content=infoMessages["attendFailed"].format(prefix), delete_after=15)

@professor.command(aliases=["l"])
async def leave(ctx, *, eventId):
    # Leave an event
    # Command syntax: leave [eventId]
    authorName = ctx.author.display_name

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, False):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        await ctx.channel.send(content=infoMessages["leaveSuccess"].format(authorName, event["name"]), delete_after=15)
        eventsDict[hash(ctx.guild)].insertIntoLog("{} left event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.channel.send(content=infoMessages["leaveFailed"].format(prefix), delete_after=15)

@professor.command(aliases="u")
async def update(ctx, eventId, toUpdate, *, newInfo):
    # Updates eventId description or name to newInfo
    # Command syntax: update [eventId] [to update] [new info]

    # Check if usere is scheduler
    if isScheduler(ctx.author):
        if toUpdate == "description" or toUpdate == "name" or toUpdate == "date" or ctx.author.id == 197471216594976768:
            event = eventsDict[hash(ctx.guild)].getEvent(eventId)

            if eventsDict[hash(ctx.guild)].updateEvent(eventId, toUpdate, newInfo):
                await ctx.channel.send(content=infoMessages["updateSuccess"].format(eventId, toUpdate, newInfo), delete_after=15)
                eventsDict[hash(ctx.guild)].insertIntoLog("{} updated event `{}`'s `{}` from `{}` to `{}`.".format(ctx.author.display_name, event["name"], toUpdate, event[toUpdate], newInfo))

            else:
                await ctx.channel.send(content=infoMessages["updateFailed"].format(prefix), delete_after=15)
        else:
            await ctx.channel.send(content=infoMessages["invalidUpdateField"], delete_after=15)
    else:
        await ctx.author.send(content=infoMessages["userNotScheduler"])

# --- Misc ---

@professor.command(aliases=["cute", "cutestuff", "helppls", "pleasehelp" ])
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

@professor.command()
async def sorry(ctx):
    await ctx.channel.send(content="Oh, that's alright {}. Don't worry about it ^^".format(ctx.author.display_name))

@professor.command(aliases=["orangejuice", "applejuice", "juice", "akidrugs"])
async def oj(ctx):
    with open("res/oj.png", "rb") as f:
        oj = discord.File(f, filename="High quality oj.png")
    await ctx.channel.send(file=oj);

@professor.command()
async def subwoah(ctx):
    try:
        voiceChannel = ctx.author.voice.channel
        connection = await voiceChannel.connect()

        source = discord.FFmpegPCMAudio("res/subwoah.mp3")
        connection.play(source)
        while connection.is_playing():
            await asyncio.sleep(0.3)
        await connection.disconnect()
    except AttributeError:
        await ctx.author.send(content="You need to be connected to voice chat to do that!")
    await ctx.message.delete()

@professor.command(aliases=["trúðagrín"])
async def clowntime(ctx):
    await ctx.channel.send(content=":o)")

# --- Salt ---

@professor.command()
async def salt(ctx):
    # Get a random nugg and increment count
    username = ctx.author.display_name
    insultMessage = saltWraper.insult(username)
    count = saltWraper.eatCookie(ctx.author)

    await ctx.send("Here is your little nugget of salt:\n{}".format(insultMessage))
    await asyncio.sleep(1)
    await ctx.send("{} has now had {} salty nuggs!".format(username, count))

@professor.command(aliases=["sb"])
async def saltboard(ctx):
    # Display leaderboard of salt
    board = saltWraper.getCookieBoard(ctx.guild)

    # Check if empty
    if board:
        out= ""
    else:
        out = "Nothing here yet"

    # Make message
    msg = discord.Embed(title="Salt leaderboards:", description="")
    for entry in board:
        out += entry[0] + ":\u2003" + str(entry[1]) + "\n"
    msg.add_field(name="\u200b", value=out,inline=0)

    await ctx.send(embed=msg)

# --- Log ---
@professor.command()
async def log(ctx):
    log = eventsDict[hash(ctx.guild)].getLog()
    embed = discord.Embed(title= "Activity log", color=discord.Color.blue())

    for e in log:
        embed.add_field(name=e[0], value=e[1], inline=False)

    await ctx.author.send(embed=embed,delete_after=300)

# --- Maintenance ---

@professor.command()
async def refresh(ctx):
    with open("messages.json", "r") as f:
        infoMessages = json.loads(f.read())
    activity = discord.Game(infoMessages["activity"])
    await professor.change_presence(activity=activity)

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



# Start bot
professor.run(str(key)) 
