# Author: Tristan Ferrua
# 2019-10-01 12:24
# Filename: cookieDatabase.py

import math
import discord
import asyncio


def getCookies(c, user):
    i = user.id
    c.execute("SELECT cookies FROM cookies WHERE uid=?",(i,))
    return c.fetchone()

def getCookieBoard(c, guild):
    out = {}
    for i in guild.members:
        current = getCookies(c, i)
        if current:
            out[i.display_name] = current[0]
    return out

def eatCookie(c, user):
    i=user.id
    current = getCookies(c,user)
    if current:
        current = current[0] + 1
        c.execute("UPDATE cookies SET cookies=? WHERE uid=?",(current,i))
    else:
        c.execute("INSERT INTO cookies VALUES (1,?)",(i,))
        current = 1
    return current


