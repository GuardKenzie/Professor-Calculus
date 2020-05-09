import bokasafn.events as events
import sqlite3
import datetime
import dateutil.parser
import discord


class Reminders:
    def __init__(self, database=None):
        self.conn = sqlite3.connect(database)
        self.c = self.conn.cursor()

    def createReminder(self, user_id, string):
        string = string.split(" to ")

        time = string[0]
        reminder = string[1]
        parsedTime = events.parseDate(time)

        now = datetime.datetime.now().isoformat()
        self.c.execute("INSERT INTO reminders VALUES (?, ?, ?, ?, ?)", (user_id, parsedTime, reminder, now, time))
        self.conn.commit()

    def checkIfRemind(self):
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        inAMinute = now + datetime.timedelta(minutes=1)

        self.c.execute("SELECT * FROM reminders WHERE reminderDate BETWEEN ? AND ?;", (str(now), str(inAMinute)))
        res = self.c.fetchall()

        self.c.execute("DELETE FROM reminders WHERE reminderDate BETWEEN ? AND ?;", (str(now), str(inAMinute)))

        out = []

        for r in res:
            setString = dateutil.parser.isoparse(r[3]).strftime("%d %B %Y %H:%M")
            embed = discord.Embed(title="Reminder!", description=r[2], colour=discord.Colour.blue())
            embed.add_field(name="When did I set this?", value="Set at `{}` for `{}`".format(setString, r[4]), inline=0)
            out.append({"id": r[0], "embed": embed})

        self.conn.commit()
        return out


if __name__ == "__main__":
    conn = sqlite3.connect(input("Location: "))
    c = conn.cursor()
    c.execute("CREATE TABLE reminders (user_id int, reminderDate str, reminder str, set_at str, original_time str)")
    conn.commit()
