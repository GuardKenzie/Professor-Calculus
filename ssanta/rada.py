# Author: Tristan Ferrua
# 2019-10-16 11:44
# Filename: rada.py 

import math

import random

def rada(x):
    out = {}
    random.shuffle(x)
    i = 0
    while i < len(x)-1:
        out[x[i]] = x[i+1]
        i += 1
    out[x[-1]] = x[0]

    return out

if __name__ == "__main__":
    print(rada(input().split()))
