# Author: Tristan Ferrua
# 2020-09-10 13:00
# Filename: notice.py 

import math
import sqlite3

class Notice:
    def __init__(self, guild, database=None):
        if database is not None:
            self.conn = sqlite3.connect(database)
            self.c = self.conn.cursor()

        self.guildHash = hash(guild)

    def isNotice(self, msgid):
        self.c.execute("SELECT * FROM notice WHERE messageid=? AND guildhash=?;", (msgid, self.guildHash))
        res = self.c.fetchone()
        if res:
            return True
        else:
            return False

    def create(self, msgid):
        self.c.execute("INSERT INTO notice VALUES (?, ?);", (msgid, self.guildHash))
        self.conn.commit()
