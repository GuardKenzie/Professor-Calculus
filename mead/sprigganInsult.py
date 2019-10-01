# Author: Tristan Ferrua
# 2019-10-01 12:48
# Filename: sprigganInsult.py

import math
import random
from pathlib import Path

here = Path(__file__).parent

insults = open("mead/insults.txt", "r+")
insults = insults.read().strip().split("\n")

bday = open("mead/bday.txt", "r+")
bday = bday.read().strip().split("\n")

jol = open("mead/jol.txt", "r+")
jol = jol.read().strip().split("\n")

def insult(name,t):
    if t == "j":
        insults = jol
    elif t=="b":
        insults = bday
    i = random.randint(0,len(insults)-1)
    return insults[i].format(name)
