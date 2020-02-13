# Author: Tristan Ferrua
# 2020-01-06 11:06
# Filename: events.py 

import sqlite3
import discord
import random
import string
import math
import json
from datetime import datetime
from datetime import timedelta

def randomId():
    # Generate random int from 1 to 1000000000
    return random.randint(1,1000000000)

def parseEvent(event):
        out = {}
        out["hash"] = event[0]
        out["id"] = event[1]
        out["date"] = event[2]
        out["name"] = event[3]
        out["description"] = event[4]
        out["people"] = json.loads(event[5])

        return out

class Events():
    # Events database handler
    # Format for table 'events': 
    # server_hash str, id int, date str, name str, description str, people str
    def __init__(self, guildHash, channel):
        self.guildHash = guildHash
        self.channel = channel
        self.myMessage = ""

        self.conn = sqlite3.connect("events.db")
        self.c = self.conn.cursor()

        self.page = 1

    def dateFormat(self, date):
        # checks if date is in format D/M/Y h:m
        # returns padded date if ok or False if not
        if date.lower() == "tbd":
            return "TBD"

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        monthsWith30Days = [4,6,9,10]

    # Seperate date and time
        date = date.split(" ")
        if len(date) != 2:
            return False


        time = date[1].split(":")
        if len(time) != 2:
            return False

        h = int(time[0])
        m = int(time[1])

        if h not in range(0,24):
            return False
        if m not in range(0,61):
            return False

        if date[0].lower() not in weekdays:
            day = date[0].split("/")
            if len(day) != 3:
                return False

            D = int(day[0])
            M = int(day[1])
            Y = int(day[2])

            if D not in range(1,32):
                return False
            if D not in range(1,31) and M in monthsWith30Days:
                return False
            if D not in range(1,29) and M == 2 and Y%4 != 0:
                return False
            if D not in range(1,30) and M == 2 and Y%4 == 0:
                return False
            if M not in range(1,13):
                return False
            dayString = "{}/{}/{}".format(str(D).zfill(2), str(M).zfill(2), str(Y))
        else:
            dayString = date[0].capitalize()

        out = "{} {}:{}".format(dayString, str(h).zfill(2), str(m).zfill(2))
        if datetime.strptime(out, "%d/%m/%Y %H:%M") < datetime.now():
            return False
        else:
            return out

    def getChannel(self):
        # Get the events channel for the server
        return self.channel

    def getEvents(self):
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

            allEvents = self.getEvents()

            # Check if eventNumber is out of bounds
            if eventNumber <= len(allEvents) and eventNumber > 0:
                return allEvents[eventNumber - 1][1]
            else:
                return False

        except ValueError:
            return False

    def createEvent(self, eventDate, eventName):
        # Creates a new event and stores in database
        eventDate = self.dateFormat(eventDate)
        eventId = randomId()
        if eventDate:
            e = self.c.execute("INSERT INTO events VALUES (?, ?, ?, ?, '', '[]')", (self.guildHash, eventId, eventDate, eventName))
            self.conn.commit()
            return e
        else:
            return False

    def removeEvent(self, eventId):
        # Removes event with ID: eventId
        e = self.c.execute("DELETE FROM events WHERE id=? AND server_hash=?", (eventId,self.guildHash))
        self.conn.commit()
        return e


    def attendEvent(self, eventId, userId, attend):
        # Adds userId to list of attendants for event with id eventId

        # Get actual Id
        eventId = self.getEventId(eventId)
        if not eventId:
            return False

        # Get event
        self.c.execute("SELECT * FROM events WHERE server_hash=? AND id=?", (self.guildHash, eventId))
        event = self.c.fetchone()

        # Check if event was fetched
        if event == None:
            return False

        # Grab list of attendants and load from json
        attendantList = json.loads(event[5])

        # Check if attending and user not already in list
        if attend and userId not in attendantList:
            attendantList.append(userId)
        # Check if leaving and user in list
        elif not attend and userId in attendantList:
            attendantList.remove(userId)
        else:
            return False

        # Update database and commit
        e = self.c.execute("UPDATE events SET people=? WHERE server_hash=? AND id=?", (json.dumps(attendantList), self.guildHash, eventId))
        self.conn.commit()
        return e

    def updateEvent(self, eventId, toUpdate, newInfo):
        # updates field toUpdate to newInfo in database

        # Get actual Id
        eventId = self.getEventId(eventId)
        if not eventId:
            return False

        # Check for date and set correct padding
        if toUpdate == "date":
            newInfo = self.dateFormat(newInfo)
            if not newInfo:
                return False

        # Update entry and check for success
        e = self.c.execute("UPDATE events SET {}=?  WHERE server_hash=? AND id=?".format(toUpdate), (newInfo, self.guildHash, eventId))
        if e:
            self.conn.commit()
            return e
        else:
            return False

    def generateEventsMessage(self, guildMembers):
        eventList = self.getEvents()

        page = self.page

        numberOfPages = math.ceil(len(eventList)/5)

        # Fix page 0
        if numberOfPages == 0:
            numberOfPages = 1

        # Check if at the last page
        if page > numberOfPages:
            page = numberOfPages

        # Define bounds for events list if not at last page
        if page != numberOfPages:
            begin = (page-1)*5
            end = begin + 5
        # if at last page then get all remaining events
        else:
            begin = (page-1)*5
            end = len(eventList)

        # Create embed
        message = discord.Embed(title="Scheduled events: (Page {}/{})".format(page,numberOfPages), color=discord.Color.purple())

        # Narrow list of events to begin:end
        eventList = eventList[begin:end]

        # Create line for each event on page
        fakeId = 1 + (page-1)*5
        for event in eventList:
            # Check if last event
            lastEvent = (event == eventList[-1])
            # Get info
            event = parseEvent(event)
            attendants = []

            # Get display names for attendants and put them in a list
            for member in event["people"]:
                attendants.append(guildMembers[member])

            # Check if noone is attending or no description
            if len(attendants) == 0:
                attendants = ["Nobody :("]
            if event["description"] == "":
                event["description"] = "No description yet."

            # Create the header
            fieldName = "{}. {} ({})".format(str(fakeId), event["name"], event["date"])
            message.add_field(name=fieldName, value=event["description"], inline = True)

            # Add party
            message.add_field(name="Party", value="\n".join(attendants))

            # Add a margin if it isn't the last event in list
            if not lastEvent:
                message.add_field(name="\u200b", value="\u200b", inline=False)
            fakeId += 1

        self.page = page
        return message

    def checkIfNotification(self):
        # Generate time string for 1 hour in future and now
        dateHour = []
        dateHour.append((datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M"))
        dateHour.append((datetime.now() + timedelta(hours=1)).strftime("%A %H:%M"))

        dateNow = []
        dateNow.append(datetime.now().strftime("%d/%m/%Y %H:%M"))
        dateNow.append(datetime.now().strftime("%A %H:%M"))

        timeNow = datetime.now().strftime("%H:%M")

        weekday = datetime.now().strftime("%A")

        eventsList = self.getEvents()

        # Check if notification for now or in an hour
        for event in eventsList:
            event = parseEvent(event)
            recurringEvent = False

            # Get actual day of event
            eventDay = event["date"].split(" ")[0]

            if eventDay == weekday:
                recurringEvent = True

                if timeNow == "10:00":
                    return {"event":    event, \
                            "date":     weekday,
                            "friendly": True, \
                            "channelId":  self.getMyChannelId("friendly"),
                            "guild":    self.channel.guild
                            }

            # If now then remove
            if event["date"] in dateNow:
                if not recurringEvent:
                    self.removeEvent(event["id"])
                return {"event":    event, \
                        "color":    discord.Color.red(), \
                        "date":     dateNow, \
                        "channel":  self.channel, \
                        "now":      True, \
                        "friendly": False }
                #(event, discord.Color.red(), dateNow, self.channel, True)

            elif event["date"] in dateHour:
                return {"event":    event, \
                        "color":    discord.Color.orange(), \
                        "date":     dateHour, \
                        "channel":  self.channel, \
                        "now":      False, \
                        "friendly": False }
                # (event, discord.Color.orange(), dateHour, self.channel, False)
        else:
            return False

    def setMyChannelId(self, channelId, channelType):
        # Get my channel id from the database
        self.c.execute("SELECT * FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash, channelType))

        # Check if I have a channel id
        if len(self.c.fetchall()) > 0:
            self.c.execute("UPDATE myChannels SET channelId=? WHERE guildHash=? AND channelType=?;", (channelId, self.guildHash, channelType))
        else:
            self.c.execute("INSERT INTO myChannels (guildHash, channelId, channelType) VALUES (?, ?, ?);", (self.guildHash, channelId, channelType))

        # Save
        self.conn.commit();

    def getMyChannelId(self, channelType):
        # Check if I have a channel and return
        self.c.execute("SELECT channelId FROM myChannels WHERE guildHash=? AND channelType=?;", (self.guildHash,  channelType))
        res = self.c.fetchone()
        if len(res) > 0:
            return res[0]
        else:
            return 0


