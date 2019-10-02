# Author: Tristan Ferrua
# 2019-09-27 17:52
# Filename: eventsDatabase.py

import math
import discord
import json
import asyncio
from datetime import datetime
from datetime import timedelta
import re
import sqlite3

leftarrow = "\u2B05"
rightarrow = "\u27A1"

conn = sqlite3.connect("events.db")
c = conn.cursor()

async def updatePinned(guild,page, fenrir, myMessage="",myChannel=""):
    if myMessage == "":
        eventlist = await getEventList(guild,fenrir)
        myMessage = eventlist[1]
    if myMessage == "":
        myMessage = await eventlist[0].send(content="Pinned event list:", embed=eventsList(guild,1))
        await myMessage.add_reaction(leftarrow)
        await myMessage.add_reaction(rightarrow)
        await myMessage.pin()
    else:
        await myMessage.edit(content="Pinned event list:".format(), embed=eventsList(guild,page))

async def pageUpdate(react, user,fenrir):
    if react.me and user != fenrir.user:
        page = await getCurrentPage(react.message.guild,fenrir)
        lastpage = page[1]
        page = page[0]

        if react.emoji == leftarrow:
            if page == 1:
                page = lastpage+1
            await updatePinned(react.message.guild, page-1, fenrir, react.message)
        elif react.emoji == rightarrow:
            if page == lastpage:
                page = 0
            await updatePinned(react.message.guild,page+1, fenrir, react.message)
        await react.remove(user)

async def checkIfNotification(fenrir):
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

                    page = await getCurrentPage(guild,fenrir)
                    page = page[0]

                    await updatePinned(guild, page,fenrir)

                    for channel in guild.text_channels:
                        if channel.name == "events" and channel.category.name == "Fenrir":
                            msg = discord.Embed(title=name, description=description, colour=discord.Colour.red(), delete_after=1800)
                            msg.add_field(name="When?", value=gmt(date))
                            msg.add_field(name="Id:", value=str(numer))
                            msg.add_field(name="Party:", value="\n".join(attendants), inline=False)
                            await channel.send(content="**Event starting now:**", embed=msg)
                            # await channel.send(content="**Event starting now:**\n>>> *Name*: __**{0}**__\n*Date*: __{1}__\n*Description*: {2}\n*Attendees*:{3}".format(name,date,description,attendees))
        await asyncio.sleep(60)

async def getCurrentPage(guild,fenrir):
    myMessage = await getEventList(guild,fenrir)
    myMessage = myMessage[1]

    if myMessage == "":
        return [1,1]
    txt = myMessage.embeds[0].title
    pagelist = re.findall("[0-9]+",txt)
    return list(map(int, pagelist))

async def getEventList(guild,fenrir):
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

def allIds(h):
    c.execute("SELECT id FROM events WHERE server_hash=?", (h,))
    a = c.fetchall()
    out = []
    for i in a:
        out.append(i[0])
    return out

def eventsList(guild, page):
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
