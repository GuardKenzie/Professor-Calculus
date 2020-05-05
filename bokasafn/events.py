import json
import datetime
import dateutil.parser
import pytz
import sqlite3
import random
import math
import discord

accent_colour = discord.Colour(int("688F56", 16))


class Event:
    def __init__(self, guildHash, eventId, date, name, description, people, roles, limit, recurring, timezone: pytz.timezone):
        self.hash = guildHash
        self.id = eventId
        self.date = dateutil.parser.isoparse(date)
        self.name = name
        self.description = description
        self.roles = json.loads(roles)
        self.timezone = timezone

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

    def now(self):
        now = pytz.utc.localize(datetime.datetime.utcnow())
        return abs(now - self.date) < datetime.timedelta(minutes=1) and self.date < now

    def inHour(self):
        inHour = pytz.utc.localize(datetime.datetime.utcnow())
        inHour += datetime.timedelta(hours=1)
        return abs(inHour - self.date) < datetime.timedelta(minutes=1) and self.date < inHour

    def friendlyNotification(self):
        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        event_at_10 = self.date.replace(hour=12, minute=31)

        return abs(utc_now - event_at_10) < datetime.timedelta(minutes=1) and event_at_10 < utc_now

    def full(self):
        return self.limit <= len(self.people) and self.limit != 0

    def fullRole(self, role):
        return self.peopleInRole[role] >= self.rolelimits[role] and self.rolelimits[role] != 0

    def roleEmoji(self, role):
        return self.roles[role]

    def roleName(self, emoji):
        reverseRoles = {v: u for u, v in self.roles.items()}
        return reverseRoles[emoji]

    def roleLimit(self, role):
        return self.rolelimits[role]

    def numberInRole(self, role):
        return self.peopleInRole[role]

    def nextDay(self):
        return str(self.date + datetime.timedelta(days=7))

    def getDate(self):
        return self.date.astimezone(self.timezone)

    def printableDate(self):
        if self.recurring:
            return self.date.astimezone(self.timezone).strftime("%A %H:%M")
        else:
            return self.date.astimezone(self.timezone).strftime("%d %B %Y %H:%M")


def parseDate(date, timezone=pytz.utc):
    done = False

    if not done:
        try:
            date = datetime.datetime.strptime(date, "%d %B %Y %H:%M")
            done = True
        except ValueError:
            pass

    if not done:
        try:
            date = datetime.datetime.strptime(date, "%d %b %Y %H:%M")
            done = True
        except ValueError:
            pass

    if not done:
        try:
            date = datetime.datetime.strptime(date, "%d/%m/%Y %H:%M")
            done = True
        except ValueError:
            pass

    if not done:
        try:
            today = datetime.datetime.now().weekday()
            weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
            delta = (weekdays[date.split()[0].lower()] - today) % 7
            try:
                date = datetime.datetime.strptime(date, "%A %H:%M")
            except ValueError:
                date = datetime.datetime.strptime(date, "%a %H:%M")
            date = datetime.datetime.utcnow().replace(hour=date.hour, minute=date.minute, second=0) + datetime.timedelta(days=delta)
            done = True
        except (AttributeError, ValueError, KeyError):
            pass

    try:
        return timezone.localize(date).astimezone(pytz.utc)
    except (AttributeError, ValueError):
        return False


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
        print("Events:\t\t\tonline for {}".format(guildHash))

    def createEvent(self, eventDate, eventName, eventDesc, eventRoles, eventLimit):
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if eventDate.split()[0].lower() in weekdays:
            recurring = True
        else:
            recurring = False

        eventDate = parseDate(eventDate, self.timezone)
        eventId = random.randint(1, 1000000000)
        eventRoles = json.dumps(eventRoles)

        if eventDate:
            e = self.c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, '[]', ?, ?, ?)", (self.guildHash, eventId, eventDate, eventName, eventDesc, eventRoles, eventLimit, recurring))
            self.conn.commit()
            return e
        else:
            return False

    def setTimezone(self, timezone):
        self.c.execute("UPDATE guildTimezones SET timezone=? WHERE server_hash=?", (timezone, self.guildHash))
        self.timezone = pytz.timezone(timezone)
        self.conn.commit()

    def getEvent(self, eventId):
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
        return out

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
            newInfo = parseDate(newInfo, self.timezone)
            if not newInfo:
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
        i = 0
        while i < len(eventList):
            eventList[i] = Event(*eventList[i], self.timezone)
            i += 1

        eventList.sort(key=lambda x: x.date, reverse=True)

        for event in eventList:
            # Check if last event
            lastEvent = (event == eventList[-1])
            # Get info
            # event = Event(*event, self.timezone)
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

            if event.friendlyNotification():
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
                    print(event.nextDay())
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

    def getMyChannelId(self, channelType):
        # Check if I have a channel and return
        self.c.execute("SELECT channelId FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash, channelType))
        res = self.c.fetchone()
        if res is not None:
            return res[0]
        else:
            return 0

    def getLog(self):
        self.c.execute("SELECT log FROM log WHERE server_hash=?;", (self.guildHash, ))
        log = self.c.fetchone()

        if log is not None:
            return json.loads(log[0])
        else:
            self.c.execute("INSERT INTO log (server_hash, log) VALUES (?, ?)", (self.guildHash, "[]"))
            self.conn.commit()
            return []

    def insertIntoLog(self, message):
        oldLog = self.getLog()
        time = datetime.datetime.now().strftime("%D %T")

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


if __name__ == "__main__":
    conn = sqlite3.connect("../db/events.db")
    c = conn.cursor()

    c.execute("ALTER TABLE events ADD recurring bool;")
    c.execute("CREATE TABLE guildTimezones (server_hash int, timezone str);")
    c.execute("SELECT * FROM events;")
    res = c.fetchall()
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for r in res:
        if r[2].lower() == "tbd":
            c.execute("DELETE FROM events WHERE server_hash=? AND id=?", (r[0], r[1]))
            continue
        if r[2].split()[0].lower() in weekdays:
            recurring = True
        else:
            recurring = False
        try:
            date = datetime.datetime.strptime(r[2], "%d/%m/%Y %M:%H")
            date = date.strftime("%d %B %Y %H:%M")
        except ValueError:
            date = r[2]
        d = parseDate(r[2], pytz.timezone("utc"))
        c.execute("UPDATE events SET date=?, recurring=? WHERE server_hash=? AND id=?", (d, recurring, r[0], r[1]))
    conn.commit()
