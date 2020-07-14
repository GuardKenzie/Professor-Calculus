import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

c.execute("ALTER TABLE events ADD ownerId int;")
c.execute("UPDATE events SET ownerId=0;")

conn.commit()
