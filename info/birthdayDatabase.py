# Author: Tristan Ferrua
# 2019-10-01 15:35
# Filename: birthdayDatabase.py

import math
from datetime import datetime
import discord
import asyncio

def inDatabase(c,uid,server_hash):
    i = c.execute("SELECT * FROM birthdays WHERE uid=? AND server_hash=?",(uid,server_hash))
    i = i.fetchall()
    if i:
        return True
    else:
        return False

def updateBday(c,uid,server_hash,bday):
    exists = inDatabase(c,uid,server_hash)
    if exists:
        c.execute("UPDATE birthdays SET birthday=? WHERE uid=? AND server_hash=?", (bday,uid,server_hash))
        return 1
    else:
        c.execute("INSERT INTO birthdays VALUES (?,?,?)",(uid, bday, server_hash))
        return 1

def getBday(c,uid,server_hash):
    exists = inDatabase(c,uid,server_hash)
    if exists:
        c.execute("SELECT birthday FROM birthdays WHERE uid=? AND server_hash=?",(uid,server_hash))
        return c.fetchone()[0]
    else:
        return -1

def isBday(c,uid,server_hash):
    time = datetime.now().strftime("%d/%m")
    if time in str(getBday(c,uid,server_hash)):
        return True
    else:
        return False

async def checkIfBirthday(c,fenrir):
    time = datetime.now().strftime("%d/%m")
    for guild in fenrir.guilds:
        for member in guild.members:
            if isBday(c, member.id, hash(guild)):
                await guild.text_channels[0].send(content="Happy birthday {}!".format(member.display_name))
    await asyncio.sleep(10)
