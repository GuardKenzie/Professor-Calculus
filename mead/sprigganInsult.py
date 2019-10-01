# Author: Tristan Ferrua
# 2019-10-01 12:48
# Filename: sprigganInsult.py

import math
import random
from pathlib import Path

here = Path(__file__).parent

insults = open("mead/insults.txt", "r+")
insults = insults.read().split("\n")[:-1]

def insult(name):
    i = random.randint(0,len(insults)-1)
    return insults[i].format(name)
