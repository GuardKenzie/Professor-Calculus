import random


class foodEmojis:
    def __init__(self, emojis: str):
        with open(emojis, "r") as f:
            self.emojis = f.read().splitlines()
        random.shuffle(self.emojis)

        self.cancel = "\u274C"
        self.checkmark = "\u2705"

    def getEmojis(self, n: int) -> list:
        return self.emojis[0:n]

    def getIndex(self, emoji: str) -> int:
        if emoji != self.cancel:
            try:
                return self.emojis.index(emoji)
            except ValueError:
                return -1
        else:
            return -2
