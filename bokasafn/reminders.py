from . import events
from . import dags
import sqlite3
import datetime
import dateutil.parser
import discord
import math

accent_colour = discord.Colour(int("688F56", 16))


class Reminders:
    def __init__(self, database=None):
        self.conn = sqlite3.connect(database)
        self.c = self.conn.cursor()

    def createReminder(self, user_id, string):
        # split the reminder
        string = string.split(" to ")

        # Find time and text
        time = string[0]
        reminder = " to ".join(string[1:])
        parsedTime = dags.parse(time)

        # Get the current time
        now = datetime.datetime.now().isoformat()

        # Update table
        self.c.execute("INSERT INTO reminders VALUES (?, ?, ?, ?, ?)", (user_id, parsedTime, reminder, now, time))
        self.conn.commit()

    def getReminders(self, user_id):
        self.c.execute("SELECT * FROM reminders WHERE user_id=?", (user_id, ))
        res = self.c.fetchall()
        if res:
            return sorted(res, key=lambda x: dateutil.parser.isoparse(x[1]))
        else:
            return None

    def genList(self, user_id, page):
        res = self.getReminders(user_id)

        if res is None:
            return res
        else:
            i = 1 * page

            pages = math.ceil(len(res) / 10)
            if page > pages or page < 1:
                return -1

            if page * 10 < len(res):
                res = res[(page - 1) * 10:page * 10]
            else:
                res = res[(page - 1) * 10:]
            out = discord.Embed(title="Reminders (page {}/{})".format(page, pages), colour=accent_colour)
            for r in res:
                out.add_field(name="{}. {}".format(i, r[2]), value=dateutil.parser.isoparse(r[1]).strftime("%d %B %Y %H:%M UTC"), inline=False)
                i += 1
        return out

    def removeReminder(self, author_id, reminder_id):
        r = self.getReminders(author_id)
        if r is not None:
            if reminder_id <= len(r):
                r = r[reminder_id - 1]
            else:
                return -1
        else:
            return -1
        self.c.execute("DELETE FROM reminders WHERE set_at=? AND user_id=?", (r[3], author_id))
        return 1

    def checkIfRemind(self):
        # Get current time and time in 1 minute
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        inAMinute = now + datetime.timedelta(minutes=1)

        # Fetch all reminders in the next minute
        self.c.execute("SELECT * FROM reminders WHERE reminderDate BETWEEN ? AND ?;", (str(now), str(inAMinute)))
        res = self.c.fetchall()

        # Delete all reminders fetched
        self.c.execute("DELETE FROM reminders WHERE reminderDate BETWEEN ? AND ?;", (str(now), str(inAMinute)))

        out = []

        # Create embed for all reminders fetched
        for r in res:
            setString = dateutil.parser.isoparse(r[3]).strftime("%d %B %Y %H:%M")
            embed = discord.Embed(title="Reminder!", description=r[2], colour=accent_colour)
            embed.add_field(name="When did I set this?", value="Set at `{}` for `{}`".format(setString, r[4]), inline=0)
            out.append({"id": r[0], "embed": embed})

        self.conn.commit()

        return out


if __name__ == "__main__":
    # Create database
    conn = sqlite3.connect(input("Location: "))
    c = conn.cursor()
    c.execute("CREATE TABLE reminders (user_id int, reminderDate str, reminder str, set_at str, original_time str)")
    conn.commit()
