import sqlite3
import json
import discord

# This is a class that handles permissions. Permission strings are as follows:
#
# --- Events ---
# Schedule: es
# Remove:   er
# Update:   eu
# Kick:     ek
#
# --- Soundboard ---
# Add:      sa
# Remove:   sr
#
# --- Configure ---
# Channel:  cc
# Role:     cr
#
# --- Setup ---
# Setup:    is

permissionResolver = {"schedule": "es",
                      "remove": "er",
                      "update": "eu",
                      "kick": "ek",
                      "soundboard add": "sa",
                      "soundboard remove": "sr",
                      "configure channel": "cc",
                      "configure role": "cr",
                      "setup": "is"
                      }


def resolveCommand(command):
    if command in permissionResolver.keys():
        return permissionResolver[command]
    else:
        return None


def resolvePermission(permission):
    reversePermissionResolver = {v: u for u,v in permissionResolver.items()}

    if permission in reversePermissionResolver.keys():
        return reversePermissionResolver[permission]
    else:
        return None


class Permissions:

    def __init__(self, guildHash):
        self.guildHash = guildHash
        self.conn = sqlite3.connect("permissiondb.db")
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
        print("Permissions for {} online".format(guildHash))

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

        return False
