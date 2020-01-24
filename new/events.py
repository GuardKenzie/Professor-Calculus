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

        monthsWith30Days = [4,6,9,10]

    # Seperate date and time
        date = date.split(" ")
        if len(date) != 2:
            return False

        day = date[0].split("/")
        if len(day) != 3:
            return False

        time = date[1].split(":")
        if len(time) != 2:
            return False

        h = int(time[0])
        m = int(time[1])

        D = int(day[0])
        M = int(day[1])
        Y = int(day[2])

        if h not in range(0,24):
            return False
        if m not in range(0,61):
            return False
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
        out = "{}/{}/{} {}:{}".format(str(D).zfill(2), str(M).zfill(2), str(Y), str(h).zfill(2), str(m).zfill(2))
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

        if toUpdate == "date" and not self.dateFormat(newInfo):
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
        timeHour = (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M")
        timeNow = datetime.now().strftime("%d/%m/%Y %H:%M")

        eventsList = self.getEvents()

        # Check if notification for now or in an hour
        for event in eventsList:
            event = parseEvent(event)

            # If now then remove
            if event["date"] == timeNow:
                self.removeEvent(event["id"])
                return (event, discord.Color.red(), timeNow, self.channel, True)
            elif event["date"] == timeHour:
                return (event, discord.Color.orange(), timeHour, self.channel, False)
        else:
            return False


