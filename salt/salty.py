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
