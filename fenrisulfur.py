import discord
from discord.ext import commands
import sqlite3
import json
from datetime import datetime
from datetime import timedelta
import asyncio
from urllib import request
import urllib
import random
import re
import math

leftarrow = "\u2B05"
rightarrow = "\u27A1"

conn = sqlite3.connect("events.db")
c = conn.cursor()

keyFile = open("key", "r")
key = keyFile.read()
print(key)
keyFile.close()

prefix = "f? "

fenrir = commands.Bot(command_prefix = prefix)
fenrir.remove_command("help")

def dcheck(x):
    if "TBD" in x:
        return True
    _30 = [4,6,9,10]

    ok = True
    x = x.split(" ")

    if len(x) != 2:
        return False

    d = x[0]
    t = x[1]

    t = t.split(":")
    h = int(t[0])
    m = int(t[1])

    d = d.split("/")

    D = int(d[0])
    M = int(d[1])
    Y = int(d[2])

    if h not in range(0,24):
        return False
    if m not in range(0,61):
        return False
    if D not in range(1,32):
        return False
    if D not in range(1,31) and M in _30:
        return False
    if D not in range(1,29) and M == 2 and Y%4 != 0:
        return False
    if D not in range(1,30) and M == 2 and Y%4 == 0:
        return False
    if M not in range(1,13):
        return False
    return True

def add0(x):
    if len(x)<2:
        return "0" + x
    else:
        return x

def pad(x):
    if x == "TBD":
        return x
    x = x.split(" ")
    a = x[0]
    b = x[1]

    a = a.split("/")
    b = b.split(":")

    a = list(map(add0,a))
    b = list(map(add0,b))

    out = "/".join(a) + " " + ":".join(b)

    return out

def gmt(x):
    if x == "TBD":
        return x
    else:
        return x + " GMT"



def allIds(c,h):
    c.execute("SELECT id FROM events WHERE server_hash=?", (h,))
    a = c.fetchall()
    out = []
    for i in a:
        out.append(i[0])
    return out

async def getEventList(guild):
    myMessage = ""
    for t in guild.text_channels:
        if t.name == "events" and t.category.name == "Fenrir":
            myChannel = t
            async for message in t.history(oldest_first=True):
                if message.author.id == fenrir.user.id and message.content == "Pinned event list:":
                    myMessage = message
                    break
            if myMessage != "":
                break
    return [myChannel,myMessage]

async def getCurrentPage(guild):
    myMessage = await getEventList(guild)
    myMessage = myMessage[1]

    if myMessage == "":
        return [1,1]
    txt = myMessage.embeds[0].title
    pagelist = re.findall("[0-9]+",txt)
    return list(map(int, pagelist))


def eventsList(c, guild, page):
        c.execute("SELECT * FROM events WHERE server_hash=?", (str(hash(guild)),))

        eList = c.fetchall()

        pages = math.ceil(len(eList)/5)
        lastPage = len(eList)%5

        if page > pages:
            page = pages

        if page != pages:
            begin = (page-1)*5
            end = page*5
        else:
            begin = (page-1)*5
            end = len(eList)

        msg = discord.Embed(title="Scheduled events: (Page {}/{})".format(page,pages), colour=discord.Colour.purple())

        eList = eList[begin:end]

        for i in eList:
            numer = i[1]
            name = i[3]
            date = i[2]
            desc = i[4]
            attendantsIds = json.loads(i[5])
            attendants = []

            for member in guild.members:
                if member.id in attendantsIds:
                    attendants.append(member.display_name)

            if len(attendants) == 0:
                attendants = ["Nobody :("]
            if desc == "":
                desc = "No description yet."

            name = "{}. {} ({})".format(str(numer), name,date)
            msg.add_field(name=name, value=desc,inline = True)
            msg.add_field(name="Party", value="\n".join(attendants))
            if i != eList[-1]:
                msg.add_field(name="\u200b", value="\u200b", inline=False)

        return msg

async def updatePinned(guild,page, myMessage="",myChannel=""):
    eventlist = await getEventList(guild)
    if myMessage == "":
        myMessage = eventlist[1]
    if myMessage == "":
        myMessage = await eventlist[0].send(content="Pinned event list:", embed=eventsList(c,guild,1))
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)
        await myMessage.pin()
    else:
        await myMessage.edit(content="Pinned event list:".format(), embed=eventsList(c,guild,page))

async def pageUpdate(react, user):
    if react.me and user != fenrir.user:
        page = await getCurrentPage(react.message.guild)
        lastpage = page[1]
        page = page[0]

        if react.emoji == leftarrow:
            if page == 1:
                page = lastpage+1
            await updatePinned(react.message.guild, page-1, react.message)
        elif react.emoji == rightarrow:
            if page == lastpage:
                page = 0
            await updatePinned(react.message.guild,page+1, react.message)
        await react.remove(user)




async def checkIfNotification():
    await fenrir.wait_until_ready()
    while True:
        timetocheck = (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M")
        time = datetime.now().strftime("%d/%m/%Y %H:%M")
        for guild in fenrir.guilds:

            #notify
            c.execute("SELECT * FROM events WHERE server_hash=? AND date=?", (str(hash(guild)), timetocheck))
            res = c.fetchall()
            if res != None:
                for i in res:
                    h = i[0]
                    numer = i[1]
                    date = i[2]
                    name = i[3]
                    description = i[4]

                    attendantsIds = json.loads(i[5])
                    attendants = []

                    for member in guild.members:
                        if member.id in attendantsIds:
                            attendants.append(member.display_name)

                    if len(attendants) == 0:
                        attendants = ["Nobody :("]

                    for channel in guild.text_channels:
                        if channel.name == "events" and channel.category.name == "Fenrir":

                            msg = discord.Embed(title=name, description=description, colour=discord.Colour.orange())
                            msg.add_field(name="When?", value=gmt(date))
                            msg.add_field(name="Id:", value=str(numer))
                            msg.add_field(name="Party:", value="\n".join(attendants), inline=False)
                            # await channel.send(content="**Event starting in 1 hour:**\n>>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(name,date,description,attendees))
                            await channel.send(content="**Event starting in 1 hour:**", embed=msg, delete_after=3600)
            #starting
            c.execute("SELECT * FROM events WHERE server_hash=? AND date=?", (str(hash(guild)), time))
            res = c.fetchall()
            if res != None:
                for i in res:
                    h = i[0]
                    numer = i[1]
                    date = i[2]
                    name = i[3]
                    description = i[4]
                    people = json.loads(i[5])

                    attendantsIds = json.loads(i[5])
                    attendants = []

                    for member in guild.members:
                        if member.id in attendantsIds:
                            attendants.append(member.display_name)

                    if len(attendants) == 0:
                        attendants = ["Nobody :("]

                    c.execute("DELETE FROM events WHERE id=? AND server_hash=?", (numer,h))
                    conn.commit()

                    page = await getCurrentPage(guild)
                    page = page[0]

                    await updatePinned(guild, page)

                    for channel in guild.text_channels:
                        if channel.name == "events" and channel.category.name == "Fenrir":
                            msg = discord.Embed(title=name, description=description, colour=discord.Colour.red(), delete_after=1800)
                            msg.add_field(name="When?", value=gmt(date))
                            msg.add_field(name="Id:", value=str(numer))
                            msg.add_field(name="Party:", value="\n".join(attendants), inline=False)
                            await channel.send(content="**Event starting now:**", embed=msg)
                            # await channel.send(content="**Event starting now:**\n>>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(name,date,description,attendees))
        await asyncio.sleep(60)

@fenrir.event
async def on_ready():
    print('Logged on as {0}!'.format(fenrir.user))
    act = discord.Game(name="with some adventurers in Snowcloak")
    await fenrir.change_presence(activity=act)

    for guild in fenrir.guilds:
        listi = await getEventList(guild)

        messages = len(await listi[0].history().flatten())
        await listi[0].purge(limit=messages-2)

        await updatePinned(guild,1)

@fenrir.event
async def on_command_completion(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        page = await getCurrentPage(ctx.guild)
        page = page[0]
        await updatePinned(ctx.guild,page)

@fenrir.event
async def on_guild_join(guild):
    for i in guild.text_channels:
        try:
            await i.send(content="Type `" +prefix+ "setup` to get started")
            break
        except discord.errors.Forbidden:
            str(1)

@fenrir.event
async def on_message(message):
    if isinstance(message.channel, discord.abc.GuildChannel):
        if (message.channel.name == "events" and message.channel.category.name == "Fenrir") or message.content == prefix + "setup":
            await fenrir.process_commands(message)
    else:
        await fenrir.process_commands(message)
    if isinstance(message.channel, discord.abc.GuildChannel) and message.channel.name == "events" and message.channel.category.name == "Fenrir":
        if message.author.id != fenrir.user.id:
            await message.delete()

@fenrir.event
async def on_reaction_add(re, user):
    await pageUpdate(re,user)

@fenrir.command()
async def setup(ctx):
    if ctx.author == ctx.guild.owner:
        await ctx.channel.purge(limit=1)
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            cat = await ctx.guild.create_category("Fenrir")
            channel = await ctx.guild.create_text_channel("events", category=cat)
            await channel.send(content="Hello! I'm Fenrisúlfur or Fenrir for short. Nice to meet you :D\nThis is my events channel. Here I will post notifications for upcoming FC events!\nPlease type `"+prefix+"help` in chat to see what I'm capable of.")
            await ctx.guild.create_role(name="Scheduler")
            await channel.send(content="Assign the newly created role `Scheduler` to people you want to be able to schedule events.")
            await ctx.guild.create_text_channel("bot-help-and-discussion", category=cat)

@fenrir.command()
async def purge(ctx):
    if ctx.channel.name == "events" and ctx.channel.category.name == "Fenrir" and 'Scheduler' in [y.name for y in ctx.author.roles]:
        messages = len(await ctx.channel.history().flatten())
        await ctx.channel.purge(limit=messages-2)
        await updatePinned(ctx.guild,1)


@fenrir.command()
async def schedule(ctx, *arg):
    if isinstance(ctx.channel, discord.abc.GuildChannel) and 'Scheduler' in [y.name for y in ctx.author.roles] and len(arg) > 1:
        if "TBD" in arg:
            date = arg[0]
            name = " ".join(arg[1:])
            argnum = 2
            print(1)
        else:
            date = arg[0] + " " + arg[1]
            name = " ".join(arg[2:])
            argnum = 3
            print(2)
        if dcheck(date) and len(arg) >= argnum:
            c.execute("SELECT id FROM events WHERE server_hash=?", (str(hash(ctx.guild)),))
            i = 1
            a = c.fetchall()
            used = []
            for entry in a:
                used.append(entry[0])
            while i in used:
                i += 1
            c.execute("INSERT INTO events VALUES (?, ?, ?, ?, '', '[]')", (str(hash(ctx.guild)), i, pad(date), name))
            conn.commit()
            await ctx.channel.send(content="Event `{0}` at `{1}` created with id `{2}`.".format(name, gmt(date), i), delete_after=15)

@fenrir.command()
async def remove(ctx, *, numer):
    if isinstance(ctx.channel, discord.abc.GuildChannel) and 'Scheduler' in [y.name for y in ctx.author.roles]:
        try:
            numer = int(numer)

            if numer in allIds(c, str(hash(ctx.guild))):
                i = ctx.args[0]
                c.execute("DELETE FROM events WHERE id=? AND server_hash=?;", (int(numer), str(hash(ctx.guild))))
                conn.commit()
                await ctx.channel.send(content="Event with id `{0}` successfully deleted!".format(numer), delete_after=15)
            else:
                await ctx.channel.send(content="That event does not exist!")
        except TypeError:
            await ctx.author.send(content="Usage: `remove [event id]` where `[event id]` is a number")

@fenrir.command()
async def attend(ctx, *, numer):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        try:
            numer = int(numer)
            author = ctx.message.author.id

            c.execute("SELECT * FROM events WHERE server_hash=? AND id=?", (str(hash(ctx.guild)), numer))

            res = c.fetchone()
            if res == None:
                await ctx.channel.send(content="That event does not exist!")
            else:
                l = json.loads(res[5])

                if author not in l:
                    l.append(author)
                    json.dumps(l)
                    c.execute("UPDATE events SET people=? WHERE server_hash=? AND id=?", (json.dumps(l), str(hash(ctx.guild)), numer))
                    conn.commit()
                    await ctx.channel.send(content="{0} is now attending `{1}`".format(ctx.message.author.display_name, res[3]),delete_after=15)
                else:
                    await ctx.channel.send(content="You are already attending that event!",delete_after=15)
        except TypeError:
             await ctx.author.send(content="Usage: `attend [event id]` where `[event id]` is a number")

@fenrir.command()
async def leave(ctx, *, numer):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        try:
            numer = int(numer)
            author = ctx.message.author.id

            c.execute("SELECT * FROM events WHERE server_hash=? AND id=?", (str(hash(ctx.guild)), numer))

            res = c.fetchone()

            if res == None:
                await ctx.channel.send(content="That event does not exist!")
            else:
                l = json.loads(res[5])
                if author in l:
                    l.remove(author)
                    c.execute("UPDATE events SET people=? WHERE server_hash=? AND id=?", (json.dumps(l), str(hash(ctx.guild)), numer))
                    conn.commit()
                    await ctx.channel.send(content="{0} is no longer attending `{1}`".format(ctx.message.author.display_name, res[3]),delete_after=15)
                else:
                    await ctx.channel.send(content="You are not attending that event!",delete_after=15)
        except TypeError:
            await ctx.author.send(content="Usage: `leave [event id]` where `[event id]` is a number")

@fenrir.command()
async def update(ctx, numer, what, *, instead):
    if isinstance(ctx.channel, discord.abc.GuildChannel) and 'Scheduler' in [y.name for y in ctx.author.roles]:
        try:
            numer = int(numer)
            if numer in allIds(c, str(hash(ctx.guild))):
                valid = ["name", "date", "description", "people"]
                if what in valid:
                    if (what == "date" and dcheck(instead)) or what != "date":
                        if what == "date":
                            instead = pad(instead)
                        c.execute("UPDATE events SET {}=? WHERE server_hash=? AND id=?".format(what), (instead,str(hash(ctx.guild)),numer))
                        conn.commit()
                        await ctx.channel.send(content="Event `{0}`'s `{1}` updated to `{2}`".format(numer, what, instead), delete_after=15)
            else:
                await ctx.channel.send(content="That event does not exist!",delete_after=15)
        except TypeError:
            await ctx.author.send(content="Usage: `Update: [event id] [update catagory] [new value]` where `[event id]` is a number and Valid update catagories are\n```name\ndate\ndescription```")

@fenrir.command()
async def help(ctx, *, cmd="none"):
    if cmd == "none":
        msg = discord.Embed(title="Available commands:", description="Use `help [command]` for more information")
        msg.add_field(name="schedule", value="Schedules a new event", inline=False)
        msg.add_field(name="remove", value="Removes an event from the schedule", inline=False)
        msg.add_field(name="attend", value="Join an event", inline=False)
        msg.add_field(name="leave", value="Leave an event", inline=False)
        msg.add_field(name="update", value="Updates a scheduled event", inline=False)
        msg.add_field(name="eyebleach", value="Produces some eyebleach", inline=False)
        await ctx.author.send(embed=msg)
    else:
        if cmd == "schedule":
            msg = discord.Embed(title="schedule [event date (Format: 'DD/MM/YYYY hh:mm' or TBD)] [event name]")
            msg.add_field(name="[event date]", value="The day the event is to take place, for example 31/02/2019 20:41", inline = False)
            msg.add_field(name="[event name]", value="The name of the event", inline=False)
            msg.add_field(name="Examples", value=prefix+"schedule 21/09/2011 12:23 example event\n"+prefix+"schedule TBD example event")
            await ctx.author.send(embed=msg)
        elif cmd == "remove":
            msg = discord.Embed(title="remove [event id]")
            msg.add_field(name="[event id]", value="The id of the event to be removed", inline=False)
            msg.add_field(name="Example", value=prefix+"remove 1")
            await ctx.author.send(embed=msg)
        elif cmd == "attend":
            msg = discord.Embed(title="attend [event id]")
            msg.add_field(name="[event id]", value="The id of the event you would like to attend", inline=False)
            msg.add_field(name="Example", value=prefix+"attend 1")
            await ctx.author.send(embed=msg)
        elif cmd == "leave":
            msg = discord.Embed(title="leave [event id]")
            msg.add_field(name="[event id]", value="The id of the event you would like to leave", inline=False)
            msg.add_field(name="Example", value=prefix+"leave 1")
            await ctx.author.send(embed=msg)
        elif cmd == "update":
            msg = discord.Embed(title="update [event id] [update catagory] [new value]")
            msg.add_field(name="[event id]", value="The id of the event to update", inline=False)
            msg.add_field(name="[update catagory]", value="Available update catagories are:\nname\ndate\ndescription", inline=False)
            msg.add_field(name="[new value]", value="The new value for the catagory", inline=False)
            msg.add_field(name="Example", value=prefix+"update 1 date 03/02/2000 12:22")
            await ctx.author.send(embed=msg)
        else:
            await ctx.author.send(content="Unrecognised command")

# @fenrir.command()
# async def nei(ctx):
#     await fenrir.logout()

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
    await ctx.channel.send(content=link, delete_after=180.0)

@fenrir.command()
async def cringe(ctx):
    subs = ["trashy","cringe","cringepics","choosingbeggars","comedycemetery","awfuleverything","wholesomecringe"]
    success = False
    subreddit = random.randint(0,len(subs)-1)
    while not success:
        try:
            a = request.urlopen("https://www.reddit.com/r/{}/top/.json?t=day".format(subs[subreddit]))
            success = True
        except urllib.error.HTTPError:
            success = False
        await asyncio.sleep(1)
    a = json.loads(a.read())
    ind = random.randint(0,len(a["data"]["children"]))
    link = a["data"]["children"][ind]["data"]["url"]
    await ctx.channel.send(content="From /r/{}: {}".format(subs[subreddit],link), delete_after=180.0)

@fenrir.command()
async def new_feature(ctx, cmd, *, description):
    if ctx.author.id == 197471216594976768:
        msg = discord.Embed(title="New feature: {0}".format(cmd))
        msg.add_field(name="What does it do?", value=description)
        for guild in fenrir.guilds:
            for channel in guild.text_channels:
                if channel.name == "events" and channel.category.name == "Fenrir":
                    await channel.send(embed=msg,delete_after=86400)

@fenrir.event
async def on_command_error(ctx, error):
    print(error)
    print(ctx.message.content)
    await ctx.author.send(content="There was an error executing your command: `{}`".format(ctx.message.content))
    if ctx.command.name == "schedule":
        await ctx.author.send(content="Usage: `schedule [event date (DD/MM/YYYY or TBD)] [event time (hh:mm)] [event name]`")
    if ctx.command.name == "remove":
        await ctx.author.send(content="Usage: `remove [event id]` where `[event id]` is a number")
    if ctx.command.name == "attend":
        await ctx.author.send(content="Usage: `attend [event id]` where `[event id]` is a number")
    if ctx.command.name == "leave":
        await ctx.author.send(content="Usage: `leave [event id]` where `[event id]` is a number")
    if ctx.command.name == "event":
        await ctx.author.send(content="Usage: `event [event id]` where `[event id]` is a number")
    if ctx.command.name == "update":
        await ctx.author.send(content="Usage: `update: [event id] [update catagory] [new value]` where `[event id]` is a number and Valid update catagories are\n```name\ndate\ndescription\npeople (format: \"['name1', 'name2',...]\")```")

fenrir.loop.create_task(checkIfNotification())
fenrir.run(key)
