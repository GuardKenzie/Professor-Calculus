import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

c.execute("CREATE TABLE cookies (cookies int, uid int)")
c.execute("CREATE TABLE birthdays (uid int, birthday str, server_hash str)")
conn.commit()
conn.close()
