import math
import random
import sqlite3

insults = open("salt/insults.txt", "r+")
insults = insults.read().strip().split("\n")


class saltClass():
    def __init__(self):
        self.conn = sqlite3.connect("salt.db")
        self.c = self.conn.cursor()

    def insult(self, name):
        bad = insults
        i = random.randint(0,len(bad)-1)
        return bad[i].format(name)

    def getCookieBoard(self, guild):
        out = {}
        for i in guild.members:
            current = self.getCookies(i)
            if current:
                out[i.display_name] = current[0]
        out = sorted(out.items(),key=lambda x: -x[1])
        return out

    def getCookies(self, user):
        i = user.id
        self.c.execute("SELECT count FROM salt WHERE userId=?",(i,))
        return self.c.fetchone()

    def eatCookie(self, user):
        i = user.id
        current = self.getCookies(user)
        if current:
            current = current[0] + 1
            self.c.execute("UPDATE salt SET count=? WHERE userId=?",(current,i))
        else:
            self.c.execute("INSERT INTO salt VALUES (1,?)",(i,))
            current = 1
        self.conn.commit()
        return current
