import json
import datetime
import dateutil.parser
from dateutil import relativedelta
import pytz
import sqlite3
import random
import math
import discord
import re
import dateparser

from . import dags

accent_colour = discord.Colour(int("688F56", 16))


class Hook:
    def __init__(self, ctx, event):
        self.ctx = ctx

        # Get hooks for event
        conn = sqlite3.connect("db/hooks.db")
        c = conn.cursor()
        c.execute("SELECT toProcess, action, params FROM hooks WHERE eventId=?", (str(event.id), ))

        out = c.fetchall()
        conn.close()

        # Generate dict with commands as keys
        self.hooks = {}

        for o in out:
            if o[0] not in self.hooks.keys():
                self.hooks[o[0]] = [(o[1], o[2])]
            else:
                self.hooks[o[0]].append((o[1], o[2]))

    async def execute(self, toProcess):
        # Process the given toProcess
        # Check if there is anything to process
        if toProcess in self.hooks.keys():
            for hook in self.hooks[toProcess]:
                action = hook[0]
                params = hook[1]

                if action == "message":
                    await self.ctx.author.send(json.loads(params))

                if action == "poll":
                    await self.ctx.author.send("poll nings")


class Event:
    def __init__(self, guildHash, eventId, date, name, description, people, roles, limit, recurring, ownerId, timezone: pytz.timezone):
        self.hash = guildHash
        self.id = eventId
        self.name = name
        self.description = description
        self.roles = json.loads(roles)
        self.timezone = timezone
        self.date = self.timezone.localize(dateutil.parser.isoparse(date)).astimezone(pytz.utc)
        self.ownerId = int(ownerId)

        self.parray = json.loads(people)
        self.parray.sort(key=lambda x: ([x for x, y, z in (self.roles)] + [""]).index(x[1]))
        self.rolesdict = dict(self.parray)
        self.people = list(self.rolesdict.keys())
        self.limit = limit

        self.rolelimits = {u: v for u, w, v in self.roles}
        self.peopleInRole = {}

        for role in self.roles:
            self.peopleInRole[role[0]] = 0

        for p in self.people:
            r = self.rolesdict[p]
            if r:
                self.peopleInRole[r] += 1

        self.recurring = bool(recurring)

    def isTBD(self):
        return self.date == dateutil.parser.isoparse("9999-01-01 00:00:00+00:00")

    def now(self):
        # Check if event is now
        now = pytz.utc.localize(datetime.datetime.utcnow())
        return abs(now - self.date) < datetime.timedelta(minutes=1) and self.date < now

    def inHour(self):
        # Check if event is in 1 hour
        inHour = pytz.utc.localize(datetime.datetime.utcnow())
        inHour += datetime.timedelta(hours=1)
        return abs(inHour - self.date) < datetime.timedelta(minutes=1) and self.date < inHour

    def friendlyNotification(self):
        # Check if friendly notification
        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        event_at_10 = self.date.astimezone(self.timezone).replace(hour=10, minute=00)

        return abs(utc_now - event_at_10) < datetime.timedelta(minutes=1) and event_at_10 < utc_now

    def full(self):
        # Check if event is full
        return self.limit <= len(self.people) and self.limit != 0

    def fullRole(self, role):
        # Check if role is full
        return self.peopleInRole[role] >= self.rolelimits[role] and self.rolelimits[role] != 0

    def getRole(self, query):
        for role in self.roles:
            if role[0] == query or role[1].lower() == query.lower():
                return role
        else:
            return False

    def nextDay(self):
        # Get the next day a recurring event is gonna happen
        return str((self.date + datetime.timedelta(days=7)).replace(tzinfo=None))

    def getAdjustedDate(self):
        # Get the date as timezone
        return self.date.astimezone(self.timezone)

    def printableDate(self):
        # String for date
        if self.isTBD():
            return "TBD"

        if self.recurring:
            return self.date.astimezone(self.timezone).strftime("%As %H:%M")
        else:
            if self.date.astimezone(self.timezone).year == datetime.datetime.now().astimezone(self.timezone).year:
                return self.date.astimezone(self.timezone).strftime("%d %B %H:%M")
            else:
                return self.date.astimezone(self.timezone).strftime("%d %B %Y %H:%M")

    def offsetPrintableDate(self, offset: int):
        # Get the printable date for the event offset by offset
        if self.isTBD():
            return "TBD"

        offset = datetime.timedelta(hours=offset)
        date = self.date + offset
        return date.strftime("%d %B %Y %H:%M")

    def timeUntil(self):
        # Get the time until the event starts
        if self.isTBD():
            return "TBD"

        now = pytz.utc.localize(datetime.datetime.utcnow())
        delta = self.date - now

        timeReg = r"(\d+):(\d+):\d+"
        dayReg = r"(\d+ days)"

        time = re.search(timeReg, str(delta))
        days = re.search(dayReg, str(delta))

        out = ""
        if days:
            out += days.group(0) + " "
        if time:
            hours = time.group(1)
            minutes = time.group(2)

            if int(hours) != 0:
                out += hours + " hours "
            if int(minutes) != 0:
                out += minutes + " minutes"

        return out


class Events:
    def __init__(self, guildHash, channel=None, role=None, database=None):
        # Events database handler
        # Format for table 'events':
        # server_hash str, id int, date str, name str, description str, people str
        self.guildHash = guildHash
        self.channel = channel
        self.myMessage = ""
        self.myMessageId = None
        self.myLogMessageId = None
        self.schedulerRole = role

        self.conn = sqlite3.connect(database)
        self.c = self.conn.cursor()

        # Fetch my message from the database
        self.c.execute("SELECT messageId FROM myMessages WHERE server_hash=?", (guildHash, ))
        myMessageId = self.c.fetchone()
        if myMessageId:
            self.myMessageId = int(myMessageId[0])

        self.c.execute("SELECT messageId FROM myLogMessages WHERE server_hash=?", (guildHash, ))
        myLogMessageId = self.c.fetchone()
        if myLogMessageId:
            self.myLogMessageId = int(myLogMessageId[0])

        # Fetch my timezone
        self.c.execute("SELECT timezone FROM guildTimezones WHERE server_hash=?", (guildHash, ))
        timezone = self.c.fetchone()
        if timezone:
            self.timezone = pytz.timezone(timezone[0])
        else:
            self.timezone = pytz.timezone("UTC")
            self.c.execute("INSERT INTO guildTimezones VALUES (?, ?)", (guildHash, "UTC"))
            self.conn.commit()

        self.page = 1

        self.scheduling = 0
        self.attending = 0

        print("Events:\t\t\tonline for {}".format(guildHash))

    def createEvent(self, eventDate, eventName, eventDesc, eventRoles, eventLimit, ownerId):
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        recurring = False
        for day in weekdays:
            if day in eventDate.lower():
                recurring = True
                break

        eventDate = dags.parse(eventDate, self.timezone, allow_tbd=True)
        eventId = random.randint(1, 1000000000)
        eventRoles = json.dumps(eventRoles)

        if eventDate:
            e = self.c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, '[]', ?, ?, ?, ?)", (self.guildHash, eventId, eventDate, eventName, eventDesc, eventRoles, eventLimit, recurring, ownerId))
            self.conn.commit()
            return e
        else:
            return False

    def setTimezone(self, timezone):
        self.c.execute("UPDATE guildTimezones SET timezone=? WHERE server_hash=?", (timezone, self.guildHash))
        self.timezone = pytz.timezone(timezone)
        self.conn.commit()

    def getEvent(self, eventId, actualId=False):
        if not actualId:
            eventId = self.getEventId(eventId)

        self.c.execute("SELECT * FROM events where id=? AND server_hash=?", (eventId, self.guildHash))
        res = self.c.fetchone()
        if res:
            return Event(*res, self.timezone)
        else:
            return False

    def getChannel(self):
        # Get the events channel for the server
        return self.channel

    def getAllEvents(self):
        # Fetches all events from database and returns
        # Format of out:
        self.c.execute("SELECT * FROM events WHERE server_hash=?", (self.guildHash,))
        out = self.c.fetchall()
        return sorted(out, key=lambda x: dateutil.parser.isoparse(x[2]))

    def getEventId(self, eventNumber):
        # Takes event index and returns id
        try:
            # Check if eventNumber is int
            eventNumber = int(eventNumber)

            allEvents = self.getAllEvents()

            # Check if eventNumber is out of bounds
            if eventNumber <= len(allEvents) and eventNumber > 0:
                return allEvents[eventNumber - 1][1]
            else:
                return False

        except ValueError:
            return False

    def removeEvent(self, eventId):
        # Removes event with ID: eventId
        e = self.c.execute("DELETE FROM events WHERE id=? AND server_hash=?", (eventId, self.guildHash))
        self.conn.commit()
        return e

    def attendEvent(self, eventId, userId, attend, role=""):
        # Adds userId to list of attendants for event with id eventId

        # Get actual Id
        eventId = self.getEventId(eventId)
        if not eventId:
            return False

        # Get event
        self.c.execute("SELECT * FROM events WHERE server_hash=? AND id=?", (self.guildHash, eventId))
        event = self.c.fetchone()

        # Check if event was fetched
        if event is None:
            return False

        # Grab list of attendants and load from json
        attendantList = json.loads(event[5])

        # Check if attending and user not already in list
        if attend and userId not in dict(attendantList).keys():
            attendantList.append((userId, role))
        # Check if leaving and user in list
        elif not attend and userId in dict(attendantList).keys():
            attendantList.remove([userId, role])
        elif attend and userId in dict(attendantList).keys():
            aux = dict(attendantList)
            aux[userId] = role
            attendantList = list(aux.items())
        else:
            return False

        # Update database and commit
        e = self.c.execute("UPDATE events SET people=? WHERE server_hash=? AND id=?", (json.dumps(attendantList), self.guildHash, eventId))
        self.conn.commit()
        return e

    def updateEvent(self, eventId, toUpdate, newInfo, actualId=False, doNotSwitch=False):
        # updates field toUpdate to newInfo in database
        toRecurring = False

        # Get actual Id
        if not actualId:
            eventId = self.getEventId(eventId)
            if not eventId:
                return False

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # Check for date and set correct padding
        if toUpdate == "date":
            toRecurring = bool(newInfo.split()[0].lower() in weekdays)
            newInfo = dags.parse(newInfo, self.timezone)
            if not newInfo:
                return False

        # Check if we are updating roles
        if toUpdate == "role":
            fieldTranslator = {"emoji": 0, "name": 1, "limit": 2}
            roleEmoji, roleField, roleNewInfo = newInfo
            roleField = roleField.lower()

            event = self.getEvent(eventId, actualId=True)

            roles = event.roles
            i = 0
            while i < len(roles):
                if roles[i][0] == roleEmoji:
                    break
                i += 1

            oldRole = list(roles[i])
            fieldIndex = fieldTranslator[roleField]
            roles[i][fieldIndex] = roleNewInfo

            b = True

            if roleField == "emoji":
                people = event.parray
                i = 0
                while i < len(people):
                    person = people[i]
                    if person[1] == oldRole[0]:
                        people[i][1] = roleNewInfo
                    i += 1

                people = json.dumps(people)
                b = self.c.execute("UPDATE events SET people=? WHERE server_hash=? AND id=?;", (people, self.guildHash, eventId))

            roles = json.dumps(roles)
            a = self.c.execute("UPDATE events SET roles=? WHERE server_hash=? AND id=?;", (roles, self.guildHash, eventId))
            if a and b:
                self.conn.commit()
                return True
            else:
                return False


        # Update entry and check for success
        e = self.c.execute("UPDATE events SET {}=?  WHERE server_hash=? AND id=?".format(toUpdate), (newInfo, self.guildHash, eventId))
        if e:
            if toRecurring and toUpdate == "date":
                self.c.execute("UPDATE events SET recurring=1 WHERE server_hash=? AND id=?", (self.guildHash, eventId))
            elif toUpdate == "date":
                self.c.execute("UPDATE events SET recurring=0 WHERE server_hash=? AND id=?", (self.guildHash, eventId))
            self.conn.commit()
            return e
        else:
            return False

    def generateEventsMessage(self, guildMembers):
        eventList = self.getAllEvents()

        page = self.page

        numberOfPages = math.ceil(len(eventList) / 5)

        # Fix page 0
        if numberOfPages == 0:
            numberOfPages = 1

        # Check if at the last page
        if page > numberOfPages:
            page = numberOfPages

        # Define bounds for events list if not at last page
        if page != numberOfPages:
            begin = (page - 1) * 5
            end = begin + 5
        # if at last page then get all remaining events
        else:
            begin = (page - 1) * 5
            end = len(eventList)

        # Create embed
        message = discord.Embed(title="Scheduled events: (Page {}/{})".format(page, numberOfPages), color=accent_colour)

        # Narrow list of events to begin:end
        eventList = eventList[begin:end]

        # Create line for each event on page
        fakeId = 1 + (page - 1) * 5

        for event in eventList:
            # Check if last event
            lastEvent = (event == eventList[-1])
            # Get info
            event = Event(*event, self.timezone)
            attendants = []

            # Get display names for attendants and put them in a list
            for member in event.people:
                attendants.append(event.rolesdict[member] + " " + guildMembers[member])

            # Generate party title
            limitMessage = "({})".format(len(attendants)) if event.limit == 0 else "({}/{})".format(len(attendants), event.limit)

            # Check if noone is attending or no description
            if len(attendants) == 0:
                attendants = ["Nobody :("]
            if event.description == "":
                event.description = "No description yet."

            # Create the header
            fieldName = "{}. {} ({})".format(str(fakeId), event.name, event.printableDate())
            message.add_field(name=fieldName, value=event.description, inline=True)

            # Add party
            message.add_field(name="Party {}".format(limitMessage), value="\n".join(attendants))

            # Add a margin if it isn't the last event in list
            if not lastEvent:
                message.add_field(name="\u200b", value="\u200b", inline=False)
            fakeId += 1

        self.page = page
        return message

    def checkIfNotification(self, force=False):
        eventsList = self.getAllEvents()
        weekday = datetime.datetime.now().strftime("%A")

        # Check if notification for now or in an hour
        eventOut = []

        for event in eventsList:
            event = Event(*event, self.timezone)

            if event.friendlyNotification() and event.recurring:
                eventOut.append({"event": event,
                                 "date": weekday,
                                 "friendly": True,
                                 "channelId": self.getMyChannelId("friendly"),
                                 "guild": self.channel.guild
                                 })

            # If now then remove
            if event.now():
                if not event.recurring:
                    self.removeEvent(event.id)
                else:
                    self.updateEvent(event.id, "people", "[]", actualId=True)
                    self.c.execute("UPDATE events SET date=? WHERE server_hash=? AND id=?", (event.nextDay(), self.guildHash, event.id))
                    self.conn.commit()
                eventOut.append({"event": event,
                                 "color": discord.Color.red(),
                                 "date": event.printableDate(),
                                 "channel": self.channel,
                                 "now": True,
                                 "friendly": False})
                # (event, discord.Color.red(), dateNow, self.channel, True)

            elif event.inHour():
                eventOut.append({"event": event,
                                 "color": discord.Color.orange(),
                                 "date": event.printableDate(),
                                 "channel": self.channel,
                                 "now": False,
                                 "friendly": False})
                # (event, discord.Color.orange(), dateHour, self.channel, False)
        return eventOut

    def setMyChannelId(self, channelId, channelType):
        # Get my channel id from the database
        self.c.execute("SELECT * FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash, channelType))

        # Check if I have a channel id
        if self.c.fetchone():
            self.c.execute("UPDATE myChannels SET channelId=? WHERE guildHash=? AND channelType=?;", (channelId, self.guildHash, channelType))
        else:
            self.c.execute("INSERT INTO myChannels (guildHash, channelId, channelType) VALUES (?, ?, ?);", (self.guildHash, channelId, channelType))

        # Save
        self.conn.commit()

    def unsetMyChannelId(self, channelType):
        self.c.execute("DELETE FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash, channelType))
        if channelType == "events":
            self.channel = None
        self.conn.commit()

    def getMyChannelId(self, channelType):
        # Check if I have a channel and return
        self.c.execute("SELECT channelId FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash, channelType))
        res = self.c.fetchone()
        if res is not None:
            return res[0]
        else:
            return 0

    def getLog(self, dateform=None):
        self.c.execute("SELECT log FROM log WHERE server_hash=?;", (self.guildHash, ))
        log = self.c.fetchone()

        if log is not None:
            out = json.loads(log[0])
            if dateform is not None:
                out = [(dateparser.parse(u).astimezone(self.timezone).strftime(dateform), v) for u, v in out]
            return out
        else:
            self.c.execute("INSERT INTO log (server_hash, log) VALUES (?, ?)", (self.guildHash, "[]"))
            self.conn.commit()
            return []

    def insertIntoLog(self, message):
        oldLog = self.getLog()
        time = str(pytz.utc.localize(datetime.datetime.utcnow()))

        if len(oldLog) >= 5:
            newLog = oldLog[1:]
        else:
            newLog = oldLog

        newLog.append((time, message))
        self.c.execute("UPDATE log SET log=? WHERE server_hash=?", (json.dumps(newLog), self.guildHash))
        self.conn.commit()

    def setMyMessage(self, message, messageType):
        if messageType == "log":
            self.myLogMessageId = message.id
        else:
            self.myMessage = message
            self.myMessageId = message.id

        if messageType == "log":
            table = "myLogMessages"
        else:
            table = "myMessages"

        self.c.execute("SELECT messageId FROM {} WHERE server_hash=?;".format(table), (self.guildHash, ))
        res = self.c.fetchone()
        if res:
            self.c.execute("UPDATE {} SET messageId=? WHERE server_hash=?;".format(table), (str(message.id), self.guildHash))
        else:
            self.c.execute("INSERT INTO {} VALUES (?, ?);".format(table), (str(message.id), self.guildHash))

        self.conn.commit()

    def createHook(self, eventId, toProcess, action, params):
        # Add a new hook
        realId = self.getEventId(eventId)
        if not realId:
            return False

        conn = sqlite3.connect("db/hooks.db")
        c = conn.cursor()

        params = json.dumps(params)

        c.execute("INSERT INTO hooks (eventId, toProcess, action, params) VALUES (?, ?, ?, ?)", (realId, toProcess, action, params))

        conn.commit()
        conn.close()

        return True

    def getAllHooks(self, eventId):
        # Returns all hooks for the event
        eventId = self.getEventId(eventId)

        if not eventId:
            return False

        conn = sqlite3.connect("db/hooks.db")
        c = conn.cursor()

        c.execute("SELECT * FROM hooks WHERE eventId=?", (eventId, ))

        res = c.fetchall()
        hooks = []
        for hook in res:
            hooks.append({"eventId": eventId, "toProcess": hook[1], "action": hook[2], "params": json.loads(hook[3])})

        return hooks

    def removeHook(self, eventId, hookNumber):
        # Remove the given hook
        hooks = self.getAllHooks(eventId)
        conn = sqlite3.connect("db/hooks.db")
        c = conn.cursor()

        hook = hooks[hookNumber - 1]
        hook = (hook["eventId"], hook["toProcess"], hook["action"], json.dumps(hook["params"]))

        c.execute("DELETE FROM hooks WHERE eventId=? AND toProcess=? AND action=? AND params=?", hook)

        conn.commit()
        conn.close()

    def addSpoiler(self, messageid, userid, channelid):
        # Spoiler table:
        # (userid int, messageid int, channelid int, guildhash int)
        conn = sqlite3.connect("db/spoilers.db")
        c = conn.cursor()
        c.execute("INSERT INTO spoilers VALUES (?, ?, ?, ?)", (userid, messageid, channelid, self.guildHash))
        conn.commit()

    def popLastSpoiler(self, userid):
        conn = sqlite3.connect("db/spoilers.db")
        c = conn.cursor()
        c.execute("SELECT messageid, channelid FROM spoilers WHERE userid=? AND guildhash=?", (userid, int(self.guildHash)))
        res = c.fetchall()

        if res:
            res = res[-1]
            c.execute("DELETE FROM spoilers WHERE messageid=? AND channelid=?", (res[0], res[1]))
            conn.commit()
            return (res[0], res[1])
        else:
            return None


if __name__ == "__main__":
    print(dags.parse(input("Date: ")))
