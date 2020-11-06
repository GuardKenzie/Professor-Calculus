import sqlite3
import json
import discord
from . import events
import re

# This is a class that handles permissions. Permission strings are as follows:
#
# --- Events ---
# Schedule: es
# Remove:   er
# Update:   eu
# Kick:     ek
# Hooks:    eh
#
# --- Soundboard ---
# Add:      sa
# Remove:   sr
#
# --- Configure ---
# Config:   c
# Channel:  cc
# Role:     cr
# Timezone: ct
#
# --- Maintenance ---
# Setup:    ms
# Clean:    mc
#
# --- Misc ---
# Notice:   no
availablePerms = ["es", "er", "eu", "ek", "sa", "sr", "cc", "cr", "ct", "no"]

permissionResolver = {"schedule": "es",
                      "remove": "er",
                      "update": "eu",
                      "kick": "ek",
                      "soundboard add": "sa",
                      "soundboard remove": "sr",
                      "configure channel": "cc",
                      "configure role": "cr",
                      "configure timezone": "ct",
                      "hook": "eh",
                      "setup": "ms",
                      "clean": "mc",
                      "notice": "no"
                      }


def resolveCommand(command):
    if command in permissionResolver.keys():
        return permissionResolver[command]
    else:
        return None


def resolvePermission(permission):
    reversePermissionResolver = {v: u for u, v in permissionResolver.items()}

    if permission in reversePermissionResolver.keys():
        return reversePermissionResolver[permission]
    else:
        return None


class Permissions:

    def __init__(self, guildHash, database=None):
        self.guildHash = guildHash
        self.conn = sqlite3.connect(database)
        self.c = self.conn.cursor()

        self.c.execute("SELECT permissionsDict FROM permissions WHERE guildHash=?", (self.guildHash, ))
        res = self.c.fetchone()
        if res:
            self.permissionsDict = json.loads(res[0])
        else:
            self.permissionsDict = {}
            self.c.execute("INSERT INTO permissions VALUES (?, ?)", (json.dumps({}), self.guildHash))
            self.conn.commit()
        self.permissionsDict = {int(u): v for u, v in self.permissionsDict.items()}
        print("Permissions:\t\tonline for {}".format(guildHash))

    def getPermissions(self, roleId):
        perms = self.permissionsDict

        if roleId in perms.keys():
            return perms[roleId]
        else:
            self.setPermissions(roleId, [])
            return []

    def setPermissions(self, roleId, newPermissions):
        self.permissionsDict[roleId] = newPermissions

        self.c.execute("UPDATE permissions SET permissionsDict=? WHERE guildHash=?", (json.dumps(self.permissionsDict), self.guildHash))
        self.conn.commit()

    def hasPermission(self, ctx: discord.ext.commands.Context):
        roleIds = [r.id for r in ctx.author.roles]
        if ctx.command.parent is None:
            command = ctx.command.name
        else:
            command = ctx.command.parent.name + " " + ctx.command.name

        permissionString = resolveCommand(command)

        if command == "configure":
            permissionString = "cr"

        if command == "hook remove":
            permissionString = "eh"

        if command.split()[0] == "notice":
            permissionString = "no"

        if permissionString is None:
            return True

        if ctx.author == ctx.guild.owner:
            return True

        for role in ctx.author.roles:
            if role.permissions.administrator:
                return True

        for roleId in roleIds:
            perms = self.getPermissions(roleId)
            if permissionString in perms:
                return True

        if permissionString[0] == "e":
            eventsClass = events.Events(self.guildHash, database="db/events.db")
            numbersInTheCommand = re.findall(r"(\d+)", ctx.message.content)
            try:
                eventId = numbersInTheCommand[0]
                event = eventsClass.getEvent(eventId)

                if event.ownerId == ctx.author.id:
                    return True
            except IndexError:
                pass

        return False
