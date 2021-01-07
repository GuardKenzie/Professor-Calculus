import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

c.execute("ALTER TABLE events RENAME TO tmp;")
c.execute("CREATE TABLE events (server_hash str, id int, date str, name str, description str, people str, roles string, eventLimit int, recurring str, ownerId int);")

c.execute("INSERT INTO events(server_hash, id, date, name, description, people, roles, eventLimit, recurring, ownerId) \
SELECT server_hash, id, date, name, description, people, roles, eventLimit, recurring, ownerId from tmp;")
c.execute("DROP TABLE tmp;")

c.execute("UPDATE events SET recurring='week' WHERE recurring='1';")
c.execute("UPDATE events SET recurring='' WHERE recurring='0';")

conn.commit()
