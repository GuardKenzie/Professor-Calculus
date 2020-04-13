import sqlite3
import json


class SoundBoard():
    def __init__(self, guildHash):
        self.conn = sqlite3.connect("sounds.db")
        self.cursor = self.conn.cursor()
        self.guildHash = guildHash

        self.cursor.execute("SELECT soundDict FROM soundboard WHERE guildHash=?", (guildHash,))
        res = self.cursor.fetchone()

        if res is not None:
            self.soundDict = json.loads(res[0])
        else:
            self.cursor.execute("INSERT INTO soundboard VALUES ('{}', ?)", (guildHash,))
            self.soundDict = {}
            self.conn.commit()

    def getSounds(self):
        return self.soundDict

    def updateDict(self):
        self.cursor.execute("UPDATE soundboard SET soundDict=? WHERE guildHash=?", (json.dumps(self.soundDict), self.guildHash))
        self.conn.commit()

    def createSound(self, name, link):
        if name in self.soundDict.keys():
            return False

        self.soundDict[name] = link
        self.updateDict()
        return True

    def removeSound(self, name):
        if name not in self.soundDict.keys():
            return False

        del self.soundDict[name]
        self.updateDict()

        return True
