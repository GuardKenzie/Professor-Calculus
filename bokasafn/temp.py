import sqlite3

conn = sqlite3.connect("../db/spoilers.db")
c = conn.cursor()
c.execute("CREATE TABLE spoilers ( userid int, messageid int, channelid int, guildhash int)")
conn.commit()