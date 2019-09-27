# Author: Tristan Ferrua
# 2019-09-27 17:41
# Filename: dateformat.py

import math

def dcheck(x):
    if "TBD" in x:
        return True
    _30 = [4,6,9,10]

    ok = True
    x = x.split(" ")

    if len(x) != 2:
        return False

    d = x[0]
    t = x[1]

    t = t.split(":")
    h = int(t[0])
    m = int(t[1])

    d = d.split("/")

    D = int(d[0])
    M = int(d[1])
    Y = int(d[2])

    if h not in range(0,24):
        return False
    if m not in range(0,61):
        return False
    if D not in range(1,32):
        return False
    if D not in range(1,31) and M in _30:
        return False
    if D not in range(1,29) and M == 2 and Y%4 != 0:
        return False
    if D not in range(1,30) and M == 2 and Y%4 == 0:
        return False
    if M not in range(1,13):
        return False
    return True

def add0(x):
    if len(x)<2:
        return "0" + x
    else:
        return x

def pad(x):
    if x == "TBD":
        return x
    x = x.split(" ")
    a = x[0]
    b = x[1]

    a = a.split("/")
    b = b.split(":")

    a = list(map(add0,a))
    b = list(map(add0,b))

    out = "/".join(a) + " " + ":".join(b)

    return out

def gmt(x):
    if x == "TBD":
        return x
    else:
        return x + " GMT"

