import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

c.execute("CREATE TABLE events (server_hash str, id int, date str, name str, description str, people str)")
c.execute("CREATE TABLE cookies (cookies int, uid int)")
conn.commit()
conn.close()
