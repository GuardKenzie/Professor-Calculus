import discord
from discord.ext import commands
import sqlite3
import json
from datetime import datetime
from datetime import timedelta
import asyncio

conn = sqlite3.connect("events.db")
c = conn.cursor()

keyFile = open("key", "r")
key = keyFile.read()
print(key)
keyFile.close()

prefix = ".f "

fenrir = commands.Bot(command_prefix = prefix)

# TODO
# Lofi
# Sýna sketch
# Help

def dcheck(x):
    _30 = [4,6,9,10]

    ok = True
    x = x.split(" ")

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

def allIds(c,h):
    c.execute("SELECT id FROM events WHERE server_hash='{0}'".format(h))
    a = c.fetchall()
    out = []
    for i in a:
        out.append(i[0])
    return out

async def checkIfNotification():
    await fenrir.wait_until_ready()
    while True:
        timetocheck = (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M")
        time = datetime.now().strftime("%d/%m/%Y %H:%M")
        for guild in fenrir.guilds:

            #notify
            c.execute("SELECT * FROM events WHERE server_hash='{0}' AND date='{1}'".format(hash(guild), timetocheck))
            res = c.fetchall()
            if res != None:
                for i in res:
                    h = i[0]
                    numer = i[1]
                    date = i[2]
                    name = i[3]
                    description = i[4]
                    people = json.loads(i[5])

                    for channel in guild.text_channels:
                        if channel.name == "events" and channel.category.name == "Fenrir":
                            print("sss")
                            attendees = ""
                            for person in people:
                                attendees += "\n   " + person
                            await channel.send(content="**Event starting in 1 hour:**\n>>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(name,date,description,attendees))
            #starting
            c.execute("SELECT * FROM events WHERE server_hash='{0}' AND date='{1}'".format(hash(guild), time))
            res = c.fetchall()
            if res != None:
                for i in res:
                    h = i[0]
                    numer = i[1]
                    date = i[2]
                    name = i[3]
                    description = i[4]
                    people = json.loads(i[5])
                    c.execute("DELETE FROM events WHERE id={0} AND server_hash='{1}'".format(numer,h))
                    conn.commit()

                    for channel in guild.text_channels:
                        if channel.name == "events" and channel.category.name == "Fenrir":
                            print("sss")
                            attendees = ""
                            for person in people:
                                attendees += "\n   " + person
                            await channel.send(content="**Event starting now:**\n>>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(name,date,description,attendees))
        await asyncio.sleep(60)



@fenrir.event
async def on_ready():
    print('Logged on as {0}!'.format(fenrir.user))
    # TODO:
    # Activity
    # Athuga events

@fenrir.event
async def on_guild_join(guild):
    cat = await guild.create_category("Fenrir")
    channel = await guild.create_text_channel("events", category=cat)
    await channel.send(content="Hello! I'm Fenrisúlfur or Fenrir for short. Nice to meet you :D\nThis is my events channel. Here I will post notifications for upcoming FC events!\nPlease type `"+prefix+"help` in chat to see what I'm capable of.")

@fenrir.command()
async def events(ctx):
    msg = ""
    c.execute("SELECT * FROM events WHERE server_hash='{0}'".format(hash(ctx.guild)))
    for i in c.fetchall():
        numer = i[1]
        name = i[3]
        time = i[2].split(" ")[1]
        date = i[2].split(" ")[0]
        attendants = json.loads(i[5])

        msg += "{0}. {1} on {2} at {3}:\n".format(numer, name, date, time)
        for name in attendants:
            msg += "    " + name + "\n"
    await ctx.channel.send(content="Scheduled events and attendees:\n>>> "+msg)
    print("1")

@fenrir.command()
async def schedule(ctx, date, time, *, name):
    if dcheck(date + " " + time):
        c.execute("SELECT id FROM events WHERE server_hash={0}".format(hash(ctx.guild)))
        i = 1
        a = c.fetchall()
        used = []
        for entry in a:
            used.append(entry[0])
        print(used)
        while i in used:
            i += 1
        c.execute("INSERT INTO events VALUES ('{0}', {1}, '{2}', '{3}', '', '[]')".format(hash(ctx.guild), i, date + " " + time, name))
        conn.commit()
        await ctx.channel.send(content="Event `{0}` at `{1}` created with id `{2}`.".format(name, time + "` on `" + date, i))
    else:
        await ctx.channel.send(content="Please enter a valid date in the format `D/M/Y hour:minute`")
    print("2")

@fenrir.command()
async def remove(ctx, *, numer):
    print("5")
    print(numer)
    try:
        numer = int(numer)

        if numer in allIds(c, hash(ctx.guild)):
            i = ctx.args[0]
            c.execute("DELETE FROM events WHERE id={0} AND server_hash='{1}';".format(int(numer), hash(ctx.guild)))
            conn.commit()
            await ctx.channel.send(content="Event with id `{0}` successfully deleted!".format(numer))
        else:
            await ctx.channel.send(content="That event does not exist!")
    except TypeError:
        await ctx.channel.send(content="Usage: `remove [event id]` where `[event id]` is a number")
    # TODO:
    # Fjarlægir event af dagskránni

@fenrir.command()
async def attend(ctx, *, numer):
    try:
        numer = int(numer)
        author = ctx.message.author.display_name

        c.execute("SELECT * FROM events WHERE server_hash='{0}' AND id={1}".format(hash(ctx.guild), numer))

        res = c.fetchone()
        if res == None:
            await ctx.channel.send(content="That event does not exist!")
        else:
            l = json.loads(res[5])

            if author not in l:
                l.append(author)
                c.execute("UPDATE events SET people='{0}' WHERE server_hash='{1}' AND id={2}".format(json.dumps(l), hash(ctx.guild), numer))
                conn.commit()
                await ctx.channel.send(content="{0} is now attending `{1}`".format(author, res[3]))
            else:
                await ctx.channel.send(content="You are already attending that event!")
    except TypeError:
         await ctx.channel.send(content="Usage: `attend [event id]` where `[event id]` is a number")
    print("3")
    # TODO:
    # Bætir þér á listann af fólki sem mætir í event med id sem er gefið

@fenrir.command()
async def leave(ctx, *, numer):
    try:
        numer = int(numer)
        author = ctx.message.author.display_name

        c.execute("SELECT * FROM events WHERE server_hash='{0}' AND id={1}".format(hash(ctx.guild), numer))

        res = c.fetchone()

        if res == None:
            await ctx.channel.send(content="That event does not exist!")
        else:
            l = json.loads(res[5])
            if author in l:
                l.remove(author)
                c.execute("UPDATE events SET people='{0}' WHERE server_hash='{1}' AND id={2}".format(json.dumps(l), hash(ctx.guild), numer))
                conn.commit()
                await ctx.channel.send(content="{0} is no longer attending `{1}`".format(author, res[3]))
            else:
                await ctx.channel.send(content="You are not attending that event!")
    except TypeError:
        await ctx.channel.send(content="Usage: `leave [event id]` where `[event id]` is a number")
    print("6")

@fenrir.command()
async def event(ctx, *, numer):
    try:
        numer = int(numer)
        c.execute("SELECT * FROM events WHERE server_hash='{0}' AND id={1}".format(hash(ctx.guild), numer))
        res = c.fetchone()
        print(res)
        if res == None:
            await ctx.channel.send(content="That event does not exist!")
        else:
            attendees = ""
            for name in json.loads(res[5]):
                attendees += "\n   " + name

            await ctx.channel.send(content=">>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(res[3],res[2],res[4],attendees))
    except TypeError:
        await ctx.channel.send(content="Usage: `event [event id]` where `[event id]` is a number")
    print("4")
    # TODO:
    # Öfugt við attend

@fenrir.command()
async def update(ctx, numer, what, *, instead):
    try:
        numer = int(numer)
        if numer in allIds(c, hash(ctx.guild)):
            valid = ["name", "date", "description", "people"]
            if what in valid:
                if (what == "date" and dcheck(instead)) or what != "date":
                    c.execute("UPDATE events SET {0}='{1}' WHERE server_hash='{2}' AND id={3}".format(what,instead,hash(ctx.guild),numer))
                    conn.commit()
                    await ctx.channel.send(content="Event `{0}`'s `{1}` updated to `{2}`".format(numer, what, instead))
                else:
                    await ctx.channel.send(content="Please enter a valid date in the format `D/M/Y hour:minute`")
        else:
            await ctx.channel.send(content="That event does not exist!")
    except TypeError:
        await ctx.channel.send(content="Usage: `Update: [event id] [update catagory] [new value]` where `[event id]` is a number and Valid update catagories are\n```name\ndate\ndescription\npeople (format: \"['name1', 'name2',...]\")```")


@fenrir.command()
async def nei(ctx):
    await fenrir.logout()

@fenrir.event
async def on_command_error(ctx, error):
    print(error)
    print(ctx)
    if ctx.command.name == "schedule":
        await ctx.channel.send(content="Usage: schedule [event date (DD/MM/YYY)] [event time (hh:mm)] [event name]")
    if ctx.command.name == "remove":
        await ctx.channel.send(content="Usage: `remove [event id]` where `[event id]` is a number")
    if ctx.command.name == "attend":
        await ctx.channel.send(content="Usage: `attend [event id]` where `[event id]` is a number")
    if ctx.command.name == "leave":
        await ctx.channel.send(content="Usage: `leave [event id]` where `[event id]` is a number")
    if ctx.command.name == "event":
        await ctx.channel.send(content="Usage: `attend [event id]` where `[event id]` is a number")
    if ctx.command.name == "update":
        await ctx.channel.send(content="Usage: `update: [event id] [update catagory] [new value]` where `[event id]` is a number and Valid update catagories are\n```name\ndate\ndescription\npeople (format: \"['name1', 'name2',...]\")```")

fenrir.loop.create_task(checkIfNotification())
fenrir.run(key)
