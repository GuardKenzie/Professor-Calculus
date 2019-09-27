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
import string

#custom libs
from extra.dateformat import *
from extra.eventsDatabase import *

#commands

conn = sqlite3.connect("events.db")
c = conn.cursor()

keyFile = open("key", "r")

key = keyFile.read().strip()
print(key)
keyFile.close()

prefix = "f? "

annad = [prefix + "eyebleach", prefix + "drinkbleach", prefix + "chill",prefix + "stress",prefix + "cringe", prefix + "chill", prefix + "stress", prefix + "volume", prefix + "help"]

fenrir = commands.Bot(command_prefix = prefix)
fenrir.remove_command("help")

# Functions
async def fashion_reply(message):
    m = "Good bot. /pat"
    if "Fashion Report" in message.embeds[0].title \
            and "Full Details" in message.embeds[0].title:
        await asyncio.sleep(3)
        await message.channel.send(content=m)

# Events
@fenrir.event
async def on_ready():
    print('Logged on as {0}!'.format(fenrir.user))
    act = discord.Game(name="with some adventurers in Snowcloak")
    await fenrir.change_presence(activity=act)

    for guild in fenrir.guilds:
        listi = await getEventList(guild,fenrir)

        messages = len(await listi[0].history().flatten())
        await listi[0].purge(limit=messages-2)

        await updatePinned(guild,1,fenrir,c)

@fenrir.event
async def on_command_completion(ctx):
    if isinstance(ctx.channel, discord.abc.GuildChannel):
        page = await getCurrentPage(ctx.guild,fenrir)
        page = page[0]
        await updatePinned(ctx.guild,page,fenrir,c)

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

    content = re.findall("f\? [a-z]*",message.content)
    if len(content) < 1:
        content =message.content
    else:
        content = content[0]

    if message.author.id == 619220397195264031 \
            and len(message.embeds) == 1:
        await fashion_reply(message)
    if isinstance(message.channel, discord.abc.GuildChannel):
        if (message.channel.name == "events" and message.channel.category.name == "Fenrir") \
                or content in annad:
            await fenrir.process_commands(message)
    else:
        await fenrir.process_commands(message)
    if isinstance(message.channel, discord.abc.GuildChannel) and message.channel.name == "events" and message.channel.category.name == "Fenrir":
        if message.author.id != fenrir.user.id:
            await message.delete()

@fenrir.event
async def on_reaction_add(re, user):
    await pageUpdate(re,user,fenrir)

# Commands
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
        await updatePinned(ctx.guild,1,fenrir,c)


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
        msg.add_field(name="cringe", value="Produces some cringe", inline=False)
        msg.add_field(name="drinkbleach", value="You die.", inline=False)
        msg.add_field(name="chill", value="Joins voice and plays some Lo-Fi", inline=False)
        msg.add_field(name="stress", value="Stops playing music.", inline=False)
        msg.add_field(name="volume", value="Sets lofi volume.", inline=False)
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
        elif cmd == "eyebleach":
            msg = discord.Embed(title="eyebleach")
            msg.add_field(name="\u200b", value="Produces some eyebleach", inline=False)
            await ctx.author.send(embed=msg)
        elif cmd == "cringe":
            msg = discord.Embed(title="cringe")
            msg.add_field(name="\u200b", value="Produces some cringe (thanks Elath'a)", inline=False)
            await ctx.author.send(embed=msg)
        elif cmd == "drinkbleach":
            msg = discord.Embed(title="drinkbleach")
            msg.add_field(name="\u200b", value="Kills you.", inline=False)
            await ctx.author.send(embed=msg)
        elif cmd == "chill":
            msg = discord.Embed(title="chill")
            msg.add_field(name="\u200b", value="The bot joins your voice channel and starts playing some chill tunes.", inline=False)
            await ctx.author.send(embed=msg)
        elif cmd == "stress":
            msg = discord.Embed(title="stress")
            msg.add_field(name="\u200b", value="Bot stops playing music and leaves voice.", inline=False)
            await ctx.author.send(embed=msg)
        elif cmd == "volume":
            msg = discord.Embed(title="volume [volume]")
            msg.add_field(name="[volume]", value="a number from 0-100", inline=False)
            await ctx.author.send(embed=msg)
        else:
            await ctx.author.send(content="Unrecognised command")
    await ctx.message.delete()

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
    await ctx.channel.send(content=link)

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
    await ctx.channel.send(content="From /r/{}: {}".format(subs[subreddit],link))

@fenrir.command()
async def new_feature(ctx, cmd, *, description):
    if ctx.author.id == 197471216594976768:
        msg = discord.Embed(title="New feature: {0}".format(cmd))
        msg.add_field(name="What does it do?", value=description)
        for guild in fenrir.guilds:
            for channel in guild.text_channels:
                if channel.name == "events" and channel.category.name == "Fenrir":
                    await channel.send(embed=msg,delete_after=86400)

@fenrir.command()
async def drinkbleach(ctx):
    await ctx.message.delete()
    user = ctx.message.author.display_name
    await ctx.channel.send("{} has drunk some bleach and is now dead.".format(user))

# Lofi
@fenrir.event
async def on_voice_state_update(member,before,after):
    for i in fenrir.voice_clients:
        if i.channel == before.channel and len(before.channel.members) == 1:
            i.stop()
            await i.disconnect()
            break

@fenrir.command()
async def chill(ctx):
    await ctx.message.delete()
    vc = ctx.message.author.voice.channel
    s = await vc.connect()

    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("http://127.0.0.1:8000/lofi.mp3"));
    s.play(source)
    source.volume = 0.1
    print(source.volume)



@fenrir.command()
async def stress(ctx):
    await ctx.message.delete()
    authorvc = ctx.message.author.voice.channel
    for i in fenrir.voice_clients:
        if i.channel == authorvc:
            i.stop()
            await i.disconnect()
            break

@fenrir.command()
async def volume(ctx, v):
    await ctx.message.delete()
    try:
        v = int(v)/100
        if v >= 0 and v <= 1:
            authorvc = ctx.message.author.voice.channel
            for i in fenrir.voice_clients:
                if i.channel == authorvc:
                    i.source.volume = v
                    break
        else:
            await ctx.send("Aðeins tölur frá 0 upp í 100 takk!")
    except TypeError:
        await ctx.send("Aðeins tölur frá 0 upp í 100 takk!")

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

fenrir.loop.create_task(checkIfNotification(c,fenrir))
fenrir.run(str(key))
