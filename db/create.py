import sqlite3
import os.path


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


def skapa(fname, tables):
    if os.path.isfile(fname):
        status = "Updating"
    else:
        status = "Creating"

    print(f'{status} {color.BOLD}{fname}{color.END}')
    conn = sqlite3.connect(fname)
    c = conn.cursor()

    count = 0

    for table in tables:
        try:
            c.execute(table)
            print(f'==> {color.YELLOW}{table}{color.END}')
            conn.commit()
            count += 1
        except sqlite3.OperationalError:
            pass
    conn.close()

    if count == 0:
        status = f'{color.YELLOW}Nothing to do{color.END}'
    else:
        status = f'{color.GREEN}Done{color.END}'
    print(f'{status}\n')


# Hooks.db
hooks = ["CREATE TABLE hooks (eventId int, toProcess str, action str, params str);"]

# Reminders
reminders = ["CREATE TABLE reminders (user_id int, reminderDate str, reminder str, set_at str, original_time str);"]

# sounds.db
soundboard = ["CREATE TABLE soundboard (soundDict string, guildHash int);"]

# Events
events = ["CREATE TABLE events (server_hash str, id int, date str, name str, description str, people str, roles string, eventLimit int, recurring bool);",
          "CREATE TABLE myChannels (guildHash int, channelId int, channelType string);",
          "CREATE TABLE log (server_hash str, log str);",
          "CREATE TABLE myMessages (messageId int, server_hash int);",
          "CREATE TABLE myLogMessages (messageId int, server_hash int);",
          "CREATE TABLE guildTimezones (server_hash int, timezone str);"
          ]

# Permissions
perms = ["CREATE TABLE permissions (permissionsDict str, guildHash int);"]

# Salt
salt = ["CREATE TABLE salt (count int, userId int);"]

# Spoilers
spoilers = ["CREATE TABLE spoilers ( userid int, messageid int, channelid int, guildhash int);"]


skapa("hooks.db", hooks)
skapa("events.db", events)
skapa("spoilers.db", spoilers)
skapa("permissions.db", perms)
skapa("reminders.db", reminders)
skapa("sounds.db", soundboard)
skapa("salt.db", salt)
