import discord
import json
from discord.ext import commands
from urllib import request
import urllib
import asyncio
import random
import sys
import praw
import re

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
prefixes = ["f? ", "f?", "p? ", "p?"]
prefix = "p? "

# Load messages
with open("messages.json", "r") as f:
    infoMessages = json.loads(f.read())

# Activity
activity = discord.Game(infoMessages["activity"])

# initiate bot
professor = commands.Bot(case_insensitive = True,
                         command_prefix = prefixes,
                         activity=activity)

professor.remove_command("help")

# Emotes
leftarrow = "\u2B05\uFE0F"
rightarrow = "\u27A1\uFE0F"

party = "\U0001F389"
calculator = "\U0001F5A9"

# Color
accent_colour = discord.Colour(int("688F56",16))

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

    reddit = praw.Reddit(client_id = r_id,
                         client_secret = r_secret,
                         user_agent = r_ua)

# ==========================================
# Functions
# ==========================================

def eventChannelCheck(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        return ctx.channel.id != eventsDict[hash(ctx.guild)].getMyChannelId("events")
    else:
        return True

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
    myMessageId = eventsDict[guildHash].myMessageId

    # Get my nick
    nick = guild.me.display_name

    # Update the message if it exists, else post new one
    try:
        myMessage = await myChannel.fetch_message(myMessageId)
        await myMessage.edit(content="Notice: all times are in GMT", embed=update)
    except:
        await myChannel.purge()
        helloMessage = await myChannel.send(content=infoMessages["helloMessage"].format(nick, prefix))
        myMessage = await myChannel.send(content="Notice: all times are in GMT", embed=update)
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)
        eventsDict[guildHash].setMyMessage(myMessage)
        await myMessage.pin()
        await helloMessage.pin()

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
        attendants.append(str(event["rolesdict"][member]) + " " + str(guildMembers[member].display_name))
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
    message = discord.Embed(title = event["name"], description = event["description"], color=color)
    message.add_field(name="When?", value = event["date"])
    message.add_field(name="Party " + limitstr, value = "\n".join(attendants), inline=False)
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
            eventOut = eventsDict[hash(guild)].checkIfNotification()
            for e in eventOut:
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

        def purgecheck(m):
            return not m.pinned

        # If I have a channel, purge and post event list
        if myChannel:
            eventsDict[guildHash].channel = myChannel
            await myChannel.purge(check=purgecheck)
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
            and (message.author != professor.user or str(message.type) == "MessageType.pins_add") \
            and eventsDict[hash(message.guild)].scheduling == 0:
            await message.delete()

@professor.event
async def on_raw_reaction_add(payload):
    # Process pages
    guild = professor.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    myMessageId = eventsDict[hash(guild)].myMessageId

    # If react to me and was someone else
    if message.id == myMessageId and payload.member != professor.user:
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

@professor.event
async def on_guild_join(guild):
    # Print setup message in first text channel we can
    eventsDict[hash(guild)] = events.Events(hash(guild), None)
    for i in guild.text_channels:
        try:
            await i.send(content="Type `" +prefix+ "setup` to get started")
            break
        except discord.errors.Forbidden:
            pass

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
        eventsDict[hash(ctx.guild)].channel = channel
        eventsDict[hash(ctx.guild)].myMessage = None
        eventsDict[hash(ctx.guild)].setMyChannelId(channel.id, "events")

        # Update pinned
        await updatePinned(channel, ctx.guild)

@professor.command(checks=[eventChannelCheck])
async def setChannel(ctx, channelType):
    if channelType not in ["events", "friendly"]:
        await ctx.message.delete()
        await ctx.author.send(content="{} is not a valid channel type.".format(channelType))
        return

    if ctx.author == ctx.guild.owner or ctx.author.id == "197471216594976768":

        def check(m):
            return (m.content == "yes" or m.content == "no") and m.channel == ctx.channel and m.author == ctx.author

        if (channelType == "events"):
            confirmMsg = await ctx.channel.send(content=infoMessages["confirmEventsChannel"])
            confirmReply = await professor.wait_for("message", check = check)
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
            await ctx.message.delete()
            await ctx.channel.send(content="Channel registered as {}".format(channelType), delete_after=20)
            eventsDict[hash(ctx.guild)].setMyChannelId(ctx.channel.id, channelType)

# --- Events ---

@professor.command(aliases=["s"])
async def schedule(ctx):
    channel = ctx.channel
    author = ctx.author

    def check(m):
        if m.content.lower() == "cancel":
            raise asyncio.TimeoutError
        return m.channel == channel and m.author == author

    if isScheduler(author):
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
            while timeOk == False:
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
                    out = check(m)
                    int(m.content)
                    return out
                except TypeError:
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
                await ctx.channel.send(content=infoMessages["eventCreated"].format(title, time), delete_after=15)
                eventsDict[hash(ctx.guild)].insertIntoLog("{} scheduled event `{}` for `{}`.".format(ctx.author.display_name, title, time))
            else:
                await ctx.channel.send(content=infoMessages["eventCreationFailed"].format(prefix), delete_after=15)
            eventsDict[hash(ctx.guild)].scheduling -= 1
        except asyncio.TimeoutError:
            def pcheck(m):
                return not m.pinned
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)

            eventsDict[hash(ctx.guild)].scheduling -= 1
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
    role=""

    emojis = []
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in emojis

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
                for u,v,z in event["roles"]:
                    limitString = " ({}/{})".format(event["rolelimits"][u], z) if z != 0 else ""
                    rolelist.append(u + ": " + v + limitString)

                rolelist ="\n".join(rolelist)
                reactMsg = await ctx.channel.send(content="Please pick a role by reacting to this message:\n{}".format(rolelist))
                for emoji in emojis:
                    await reactMsg.add_reaction(emoji)
                reaction, user = await professor.wait_for("reaction_add", check=check, timeout=60)
                await reactMsg.delete()
                role = str(reaction.emoji)
        except asyncio.TimeoutError:
            def pcheck(m):
                return not m.pinned
            if ctx.channel == eventsDict[hash(ctx.guild)].channel:
                await ctx.channel.purge(check=pcheck)

    # Attend event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, True, role=role):
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

    event = eventsDict[hash(ctx.guild)].getEvent(eventId)
    try:
        role = event["rolesdict"][ctx.author.id]
    except KeyError:
        role = ""

    # Leave event and check for success
    if eventsDict[hash(ctx.guild)].attendEvent(eventId, ctx.author.id, False, role=role):
        event = eventsDict[hash(ctx.guild)].getEvent(eventId)

        await ctx.channel.send(content=infoMessages["leaveSuccess"].format(authorName, event["name"]), delete_after=15)
        eventsDict[hash(ctx.guild)].insertIntoLog("{} left event `{}`.".format(ctx.author.display_name, event["name"]))
    else:
        await ctx.channel.send(content=infoMessages["leaveFailed"].format(prefix), delete_after=15)

@professor.command(aliases=["u"])
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

@professor.command(checks=[eventChannelCheck], aliases=["cute", "cutestuff", "helppls", "pleasehelp" ])
async def eyebleach(ctx):
    subreddit = reddit.subreddit("eyebleach")

    out = []
    ok_extensions = ["png","gif","jpg","jpeg"]

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
    await ctx.channel.send(content="From /r/eyebleach:\n{}\n{}".format(pick[0],pick[1]))
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

@professor.command(checks=[eventChannelCheck],aliases=["dice", "random", "pick"])
async def roll(ctx, *, names):
    # Determine a random thing from a list
    await ctx.channel.send(content="And the winner is...")
    await asyncio.sleep(5)

    names = names.split(", ")
    winner = random.choice(names)

    await ctx.channel.send(content="{0} wins the roll! {1} {1} {1}".format(winner, party))

@professor.command(checks=[eventChannelCheck])
async def sorry(ctx):
    await ctx.channel.send(content="Oh, that's alright {}. Don't worry about it ^^".format(ctx.author.display_name))

@professor.command(checks=[eventChannelCheck],aliases=["orangejuice", "applejuice", "juice", "akidrugs"])
async def oj(ctx):
    with open("res/oj.png", "rb") as f:
        oj = discord.File(f, filename="High quality oj.png")
    await ctx.channel.send(file=oj);

@professor.command(checks=[eventChannelCheck])
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

@professor.command(checks=[eventChannelCheck], aliases=["trúðagrín"])
async def clowntime(ctx):
    await ctx.channel.send(content=":o)")

@professor.command(checks=[eventChannelCheck], aliases=["what?", "wat"])
async def what(ctx):
    i = random.randint(0,9)
    deltime=120
    if i == 1:
        with open("res/confused.jpg", "rb") as f:
            oj = discord.File(f, filename="confused.jpg")
        await ctx.channel.send(file=oj, delete_after=deltime)
    elif i == 2:
        with open("res/wat.jpg", "rb") as f:
            oj = discord.File(f, filename="wat.jpg")
        await ctx.channel.send(file=oj, delete_after=deltime)
    elif i == 3:
        await ctx.channel.send(content="I dunno, you tell me", delete_after=deltime)
    elif i == 4:
        await ctx.channel.send(content="Jeg har brug for mælk!\nhttps://www.youtube.com/watch?v=uYzJ-thBfIs", delete_after=deltime)
    elif i == 5:
        await ctx.channel.send(content="An important and fundamental axiom in set theory sometimes called Zermelo's axiom of choice. It was formulated by Zermelo in 1904 and states that, given any set of mutually disjoint nonempty sets, there exists at least one set that contains exactly one element in common with each of the nonempty sets. The axiom of choice is related to the first of Hilbert's problems.", delete_after=deltime)
    elif i == 6:
        with open("res/lahabread.png", "rb") as f:
            oj = discord.File(f, filename="lahabread.png")
        await ctx.channel.send(file=oj, delete_after=deltime)
    elif i == 7:
        await ctx.channel.send(content="https://www.youtube.com/watch?v=QK7oacKDt88", delete_after=deltime)
    elif i == 8:
        await ctx.channel.send(content="f? clowntime", delete_after=deltime)
    elif i == 9:
        await ctx.channel.send(content="f? what", delete_after=deltime)

# --- Salt ---

@professor.command(checks=[eventChannelCheck])
async def salt(ctx):
    # Get a random nugg and increment count
    username = ctx.author.display_name
    insultMessage = saltWraper.insult(username)
    count = saltWraper.eatCookie(ctx.author)

    await ctx.send("Here is your little nugget of salt:\n{}".format(insultMessage))
    await asyncio.sleep(1)
    await ctx.send("{} has now had {} salty nuggs!".format(username, count))

@professor.command(checks=[eventChannelCheck],aliases=["sb"])
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

# --- Lofi ---
@professor.event
async def on_voice_state_update(member, before, after):
    for i in professor.voice_clients:
        if i.channel == before.channel and len(before.channel.members) == 1:
            i.stop()
            await i.disconnect()
            break

@professor.group()
async def chill(ctx):
    if ctx.invoked_subcommand is None:
        try:
            await ctx.message.delete()
            vc = ctx.message.author.voice.channel
            s = await vc.connect()

            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("http://mystic.tokyo:8000/lofi.mp3"));
            s.play(source)
            source.volume = 0.1
        except AttributeError:
            await ctx.author.send(content="You have to be on voice to do that")



@chill.command()
async def stop(ctx):
    await ctx.message.delete()
    try:
        authorvc = ctx.message.author.voice.channel
        for i in professor.voice_clients:
            if i.channel == authorvc:
                i.stop()
                await i.disconnect()
                break
    except:
        await ctx.author.send(content="You have to be on voice to do that")

@chill.command(aliases=["v"])
async def volume(ctx, v):
    await ctx.message.delete()
    try:
        v = int(v)/100
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
    embed = discord.Embed(title= "Activity log", color=accent_colour)

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
