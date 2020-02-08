import math
import random
import sqlite3

insults = open("salt/insults.txt", "r+")
insults = insults.read().strip().split("\n")

def insult(name,t):
    bad = insults
    i = random.randint(0,len(bad)-1)
    return bad[i].format(name)

class sprigganMead():
    def __init__(self):
        self.conn = sqlite3.connect("salt.db")
        self.c = self.conn.cursor()

    def getCookies(self, user):
        i = user.id
        self.c.execute("SELECT cookies FROM cookies WHERE uid=?",(i,))
        return self.c.fetchone()

    def eatCookie(self, user):
        i = user.id
        current = getCookies(user)
        if current:
            current = current[0] + 1
            c.execute("UPDATE cookies SET cookies=? WHERE uid=?",(current,i))
        else:
            c.execute("INSERT INTO cookies VALUES (1,?)",(i,))
            current = 1
        self.conn.commit()
        return current
